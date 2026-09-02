import tempfile
import zipfile
from datetime import time
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, connection, transaction
from django.test import RequestFactory, TransactionTestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from calendar_app.models import Appointment
from config.backups import (
    BackupValidationError,
    create_backup,
    restore_backup,
    verify_backup,
)
from config.environment import database_from_url, env_bool
from config.error_views import server_error
from config.validators import validate_property_image
from contacts.models import Contact
from properties.models import Property


class StabilityAndSecurityTests(TransactionTestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.media_root = Path(self.temporary_directory.name) / "media"
        self.backup_root = Path(self.temporary_directory.name) / "backups"
        self.media_root.mkdir()
        self.settings_override = override_settings(
            MEDIA_ROOT=self.media_root,
            BACKUP_ROOT=self.backup_root,
        )
        self.settings_override.enable()
        self.user = get_user_model().objects.create_user(
            username="security-agent",
            password="test-password",
            role="agent",
        )

    def tearDown(self):
        self.settings_override.disable()
        self.temporary_directory.cleanup()

    def _image_bytes(self):
        from PIL import Image

        output = BytesIO()
        Image.new("RGB", (40, 30), "#4338ca").save(output, format="PNG")
        return output.getvalue()

    def test_healthchecks_and_request_identifier(self):
        live_response = self.client.get(reverse("health_live"))
        ready_response = self.client.get(reverse("health_ready"))

        self.assertEqual(live_response.status_code, 200)
        self.assertEqual(ready_response.status_code, 200)
        self.assertRegex(live_response["X-Request-ID"], r"^[a-f0-9]{32}$")

        supplied_response = self.client.get(
            reverse("health_live"),
            HTTP_X_REQUEST_ID="support-case-1234",
        )
        self.assertEqual(supplied_response["X-Request-ID"], "support-case-1234")

    def test_personal_dashboard_query_budget(self):
        self.client.force_login(self.user)

        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(queries), 75)

    def test_server_error_is_independent_and_shows_reference(self):
        request = RequestFactory().get("/broken/")
        request.request_id = "error-reference-123"

        response = server_error(request)

        self.assertEqual(response.status_code, 500)
        self.assertIn(b"error-reference-123", response.content)

    def test_property_image_validation_and_private_delivery(self):
        valid_upload = SimpleUploadedFile(
            "house.png",
            self._image_bytes(),
            content_type="image/png",
        )
        validate_property_image(valid_upload)
        with self.assertRaises(ValidationError):
            validate_property_image(
                SimpleUploadedFile(
                    "fake.png",
                    b"not-an-image",
                    content_type="image/png",
                )
            )

        property_obj = Property.objects.create(
            street="Calle Segura",
            number="1",
            city="Arcos de la Frontera",
            property_type="house",
            created_by=self.user,
            assigned_agent=self.user,
        )
        property_obj.image.save("house.png", ContentFile(self._image_bytes()))
        image_url = reverse("property_image", args=[property_obj.pk])

        anonymous_response = self.client.get(image_url)
        self.assertEqual(anonymous_response.status_code, 302)

        self.client.force_login(self.user)
        response = self.client.get(image_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "private, max-age=3600")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        response.close()

    def test_backup_is_created_verified_and_detects_tampering(self):
        (self.media_root / "sample.txt").write_text("contenido", encoding="utf-8")
        backup = create_backup(self.backup_root / "test-backup.zip")
        manifest = verify_backup(backup)

        self.assertIn("database.json", manifest["files"])
        self.assertIn("media/sample.txt", manifest["files"])

        tampered = self.backup_root / "tampered.zip"
        with zipfile.ZipFile(backup, "r") as source, zipfile.ZipFile(tampered, "w") as target:
            for info in source.infolist():
                content = source.read(info.filename)
                if info.filename == "database.json":
                    content += b" "
                target.writestr(info, content)
        with self.assertRaises(BackupValidationError):
            verify_backup(tampered)

    def test_restore_requires_explicit_confirmation(self):
        backup = create_backup(self.backup_root / "test-backup.zip")

        with self.assertRaises(CommandError):
            call_command("restore_crm", str(backup))

    def test_database_constraints_reject_invalid_appointment_interval(self):
        contact = Contact.objects.create(
            name="Cliente seguro",
            last_name="CRM",
            phone="600100999",
            identification_number="12345678Z",
            marital_status="single",
            is_buyer=True,
            assigned_agent=self.user,
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            Appointment.objects.create(
                contact=contact,
                agent=self.user,
                appointment_type="valuation",
                date="2026-09-02",
                time=time(12, 0),
                end_time=time(11, 0),
            )

    def test_environment_parsers_are_strict(self):
        with patch.dict("os.environ", {"CRM_TEST_BOOLEAN": "sometimes"}):
            with self.assertRaises(Exception):
                env_bool("CRM_TEST_BOOLEAN", default=False)
        database = database_from_url(
            "postgresql://user:secret@db:5432/crm?sslmode=require",
            Path(self.temporary_directory.name),
        )
        self.assertEqual(database["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(database["OPTIONS"]["sslmode"], "require")


class BackupRestoreTests(TransactionTestCase):
    def test_verified_backup_restores_database_and_media(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            media_root = root / "media"
            backup_root = root / "backups"
            media_root.mkdir()
            with override_settings(MEDIA_ROOT=media_root, BACKUP_ROOT=backup_root):
                get_user_model().objects.create_user(
                    username="preserved-user",
                    password="test-password",
                )
                (media_root / "preserved.txt").write_text(
                    "original",
                    encoding="utf-8",
                )
                backup = create_backup(backup_root / "restore-test.zip")

                get_user_model().objects.create_user(
                    username="discarded-user",
                    password="test-password",
                )
                (media_root / "preserved.txt").write_text(
                    "modified",
                    encoding="utf-8",
                )
                restore_backup(backup, create_safety_backup=False)

                self.assertTrue(
                    get_user_model().objects.filter(username="preserved-user").exists()
                )
                self.assertFalse(
                    get_user_model().objects.filter(username="discarded-user").exists()
                )
                self.assertEqual(
                    (media_root / "preserved.txt").read_text(encoding="utf-8"),
                    "original",
                )

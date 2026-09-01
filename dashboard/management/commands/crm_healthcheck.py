import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from config.backups import BackupValidationError, verify_backup


class Command(BaseCommand):
    help = "Comprueba base de datos, escritura multimedia y antigüedad de las copias."

    def add_arguments(self, parser):
        parser.add_argument(
            "--max-backup-age-hours",
            type=int,
            default=26,
            help="Antigüedad máxima aceptada para la última copia.",
        )

    def handle(self, *args, **options):
        errors = []
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                if cursor.fetchone()[0] != 1:
                    errors.append("La base de datos no respondió correctamente.")
        except Exception as exc:
            errors.append(f"No se puede acceder a la base de datos: {exc}")

        media_root = Path(settings.MEDIA_ROOT)
        try:
            media_root.mkdir(parents=True, exist_ok=True)
            descriptor, probe = tempfile.mkstemp(prefix=".health-", dir=media_root)
            os.close(descriptor)
            Path(probe).unlink()
        except OSError as exc:
            errors.append(f"El almacenamiento multimedia no permite escritura: {exc}")

        backup_root = Path(settings.BACKUP_ROOT)
        backups = sorted(
            backup_root.glob("crm-backup-*.zip") if backup_root.exists() else [],
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if not backups:
            errors.append("No existe ninguna copia automática.")
        else:
            latest = backups[0]
            created_at = datetime.fromtimestamp(latest.stat().st_mtime, timezone.utc)
            maximum_age = timedelta(hours=options["max_backup_age_hours"])
            if datetime.now(timezone.utc) - created_at > maximum_age:
                errors.append(f"La última copia es demasiado antigua: {latest.name}")
            try:
                verify_backup(latest)
            except BackupValidationError as exc:
                errors.append(f"La última copia no es válida: {exc}")

        if errors:
            raise CommandError("\n".join(errors))
        self.stdout.write(self.style.SUCCESS("CRM operativo y última copia válida."))

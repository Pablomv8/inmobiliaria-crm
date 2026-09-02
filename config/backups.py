import hashlib
import json
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone as datetime_timezone
from io import StringIO
from pathlib import Path, PurePosixPath

from django.conf import settings
from django.core.management import call_command
from django.db import transaction
from django.db.migrations.recorder import MigrationRecorder


BACKUP_FORMAT_VERSION = 1
DATABASE_MEMBER = "database.json"
MANIFEST_MEMBER = "manifest.json"
EXCLUDED_MODELS = (
    "contenttypes.contenttype",
    "auth.permission",
    "sessions.session",
)


class BackupValidationError(ValueError):
    pass


def _sha256_bytes(content):
    return hashlib.sha256(content).hexdigest()


def _safe_member_name(name):
    path = PurePosixPath(name)
    return bool(name and not path.is_absolute() and ".." not in path.parts)


def create_backup(destination=None):
    backup_root = Path(getattr(settings, "BACKUP_ROOT", settings.BASE_DIR / "backups"))
    backup_root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(datetime_timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    target = Path(destination) if destination else backup_root / f"crm-backup-{timestamp}.zip"
    target.parent.mkdir(parents=True, exist_ok=True)

    output = StringIO()
    args = [
        "dumpdata",
        "--indent",
        "2",
        "--natural-foreign",
        "--natural-primary",
    ]
    for model in EXCLUDED_MODELS:
        args.extend(["--exclude", model])
    from django.db import connection

    already_in_transaction = connection.in_atomic_block
    with transaction.atomic():
        if (
            connection.vendor == "postgresql"
            and not already_in_transaction
        ):
            with connection.cursor() as cursor:
                cursor.execute(
                    "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"
                )
        call_command(*args, stdout=output)
    database_content = output.getvalue().encode("utf-8")

    applied_migrations = sorted(
        f"{app}.{name}"
        for app, name in MigrationRecorder.Migration.objects.values_list("app", "name")
    )
    manifest = {
        "format_version": BACKUP_FORMAT_VERSION,
        "created_at": datetime.now(datetime_timezone.utc).isoformat(),
        "django_settings": settings.SETTINGS_MODULE,
        "database_engine": settings.DATABASES["default"]["ENGINE"],
        "applied_migrations": applied_migrations,
        "files": {},
    }

    temporary_target = target.with_suffix(target.suffix + ".tmp")
    with zipfile.ZipFile(temporary_target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(DATABASE_MEMBER, database_content)
        manifest["files"][DATABASE_MEMBER] = {
            "sha256": _sha256_bytes(database_content),
            "size": len(database_content),
        }
        media_root = Path(settings.MEDIA_ROOT)
        if media_root.exists():
            for file_path in sorted(path for path in media_root.rglob("*") if path.is_file()):
                relative = file_path.relative_to(media_root).as_posix()
                member = f"media/{relative}"
                content = file_path.read_bytes()
                archive.writestr(member, content)
                manifest["files"][member] = {
                    "sha256": _sha256_bytes(content),
                    "size": len(content),
                }
        archive.writestr(
            MANIFEST_MEMBER,
            json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"),
        )
    temporary_target.replace(target)
    return target


def verify_backup(backup_path):
    path = Path(backup_path)
    max_archive_size = getattr(settings, "BACKUP_MAX_ARCHIVE_BYTES", 5 * 1024**3)
    max_uncompressed_size = getattr(
        settings,
        "BACKUP_MAX_UNCOMPRESSED_BYTES",
        10 * 1024**3,
    )
    if not path.is_file():
        raise BackupValidationError("El archivo de copia no existe.")
    if path.stat().st_size > max_archive_size:
        raise BackupValidationError("La copia supera el tamaño máximo permitido.")

    try:
        with zipfile.ZipFile(path, "r") as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            if len(names) != len(set(names)):
                raise BackupValidationError("La copia contiene rutas duplicadas.")
            if any(not _safe_member_name(name) for name in names):
                raise BackupValidationError("La copia contiene una ruta no segura.")
            if sum(info.file_size for info in infos) > max_uncompressed_size:
                raise BackupValidationError("La copia descomprimida supera el límite permitido.")
            if MANIFEST_MEMBER not in names or DATABASE_MEMBER not in names:
                raise BackupValidationError("La copia no contiene manifiesto o base de datos.")

            manifest = json.loads(archive.read(MANIFEST_MEMBER).decode("utf-8"))
            if manifest.get("format_version") != BACKUP_FORMAT_VERSION:
                raise BackupValidationError("La versión del formato no es compatible.")
            declared = manifest.get("files", {})
            if set(declared) != set(names) - {MANIFEST_MEMBER}:
                raise BackupValidationError("El manifiesto no coincide con el contenido.")
            for member, metadata in declared.items():
                content = archive.read(member)
                if len(content) != metadata.get("size"):
                    raise BackupValidationError(f"Tamaño incorrecto en {member}.")
                if _sha256_bytes(content) != metadata.get("sha256"):
                    raise BackupValidationError(f"Checksum incorrecto en {member}.")
            database_data = json.loads(archive.read(DATABASE_MEMBER).decode("utf-8"))
            if not isinstance(database_data, list):
                raise BackupValidationError("El volcado de la base de datos no es válido.")
            return manifest
    except (zipfile.BadZipFile, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BackupValidationError("La copia está dañada o no tiene un formato válido.") from exc


def restore_backup(backup_path, create_safety_backup=True):
    path = Path(backup_path)
    manifest = verify_backup(path)
    safety_backup = create_backup() if create_safety_backup else None

    with tempfile.TemporaryDirectory(prefix="crm-restore-") as temporary_directory:
        fixture_path = Path(temporary_directory) / DATABASE_MEMBER
        with zipfile.ZipFile(path, "r") as archive:
            fixture_path.write_bytes(archive.read(DATABASE_MEMBER))

        call_command("flush", interactive=False)
        with transaction.atomic():
            call_command("loaddata", str(fixture_path))

        media_root = Path(settings.MEDIA_ROOT)
        restored_media = Path(temporary_directory) / "restored-media"
        restored_media.mkdir()
        with zipfile.ZipFile(path, "r") as archive:
            for member in manifest["files"]:
                if not member.startswith("media/"):
                    continue
                relative = PurePosixPath(member).relative_to("media")
                destination = restored_media.joinpath(*relative.parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(archive.read(member))
        if media_root.exists():
            shutil.rmtree(media_root)
        shutil.copytree(restored_media, media_root)
    return safety_backup

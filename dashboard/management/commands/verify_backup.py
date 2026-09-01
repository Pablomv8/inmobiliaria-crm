from django.core.management.base import BaseCommand, CommandError

from config.backups import BackupValidationError, verify_backup


class Command(BaseCommand):
    help = "Comprueba estructura, JSON y checksums de una copia del CRM."

    def add_arguments(self, parser):
        parser.add_argument("backup")

    def handle(self, *args, **options):
        try:
            manifest = verify_backup(options["backup"])
        except BackupValidationError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(
            self.style.SUCCESS(
                f"Copia válida ({manifest['created_at']}, "
                f"{len(manifest['files'])} archivos)."
            )
        )

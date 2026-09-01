from django.core.management.base import BaseCommand, CommandError

from config.backups import BackupValidationError, restore_backup


class Command(BaseCommand):
    help = "Restaura una copia verificada del CRM. Requiere confirmación explícita."

    def add_arguments(self, parser):
        parser.add_argument("backup")
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Confirma el reemplazo de la base de datos y del directorio multimedia.",
        )
        parser.add_argument(
            "--no-safety-backup",
            action="store_true",
            help="No crear una copia de seguridad del estado previo.",
        )

    def handle(self, *args, **options):
        if not options["confirm"]:
            raise CommandError("Añade --confirm para autorizar la restauración.")
        try:
            safety_backup = restore_backup(
                options["backup"],
                create_safety_backup=not options["no_safety_backup"],
            )
        except BackupValidationError as exc:
            raise CommandError(str(exc)) from exc
        message = "Copia restaurada correctamente."
        if safety_backup:
            message += f" Copia previa: {safety_backup}"
        self.stdout.write(self.style.SUCCESS(message))

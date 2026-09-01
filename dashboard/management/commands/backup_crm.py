from pathlib import Path

from django.core.management.base import BaseCommand

from config.backups import create_backup, verify_backup


class Command(BaseCommand):
    help = "Crea y verifica una copia completa de los datos y archivos del CRM."

    def add_arguments(self, parser):
        parser.add_argument("--output", help="Ruta opcional del archivo ZIP de salida.")
        parser.add_argument(
            "--keep",
            type=int,
            default=30,
            help="Número de copias automáticas que se conservan (por defecto: 30).",
        )

    def handle(self, *args, **options):
        target = create_backup(options["output"])
        verify_backup(target)
        self.stdout.write(self.style.SUCCESS(f"Copia creada y verificada: {target}"))

        if not options["output"] and options["keep"] >= 1:
            backups = sorted(
                Path(target).parent.glob("crm-backup-*.zip"),
                key=lambda path: path.stat().st_mtime,
                reverse=True,
            )
            for obsolete in backups[options["keep"]:]:
                obsolete.unlink()

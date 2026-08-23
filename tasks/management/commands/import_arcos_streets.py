import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.core.management.base import BaseCommand, CommandError

from tasks.street_import import parse_overpass_streets, save_streets


DEFAULT_ENDPOINT = "https://overpass-api.de/api/interpreter"
OVERPASS_QUERY = """
[out:json][timeout:90];
area["boundary"="administrative"]["name"="Arcos de la Frontera"]["admin_level"="8"]->.searchArea;
way(area.searchArea)["highway"]["name"]["highway"!~"motorway|motorway_link|trunk|trunk_link"];
out tags geom;
""".strip()


class Command(BaseCommand):
    help = "Importa y actualiza las calles de Arcos de la Frontera desde OpenStreetMap."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=Path,
            help="Lee una respuesta JSON de Overpass desde un archivo local.",
        )
        parser.add_argument(
            "--endpoint",
            default=DEFAULT_ENDPOINT,
            help="Endpoint compatible con Overpass API.",
        )
        parser.add_argument(
            "--prune",
            action="store_true",
            help="Elimina del catálogo las calles que ya no aparezcan en la fuente.",
        )

    def handle(self, *args, **options):
        try:
            if options["file"]:
                with options["file"].open(encoding="utf-8") as source:
                    payload = json.load(source)
            else:
                body = urlencode({"data": OVERPASS_QUERY}).encode("utf-8")
                request = Request(
                    options["endpoint"],
                    data=body,
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "User-Agent": "InmobiliariaCRM/1.0 (street catalog import)",
                    },
                )
                with urlopen(request, timeout=120) as response:
                    payload = json.load(response)
        except (OSError, ValueError) as exc:
            raise CommandError(f"No se pudieron obtener las calles: {exc}") from exc

        rows = parse_overpass_streets(payload)
        if not rows:
            raise CommandError("La fuente no devolvió ninguna calle utilizable.")

        created, updated, removed = save_streets(
            rows,
            prune=options["prune"],
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Calles importadas: {created} nuevas, {updated} actualizadas"
                f" y {removed} eliminadas."
            )
        )

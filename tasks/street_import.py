from collections import defaultdict

from django.db import transaction

from .models import Street


MUNICIPALITY = "Arcos de la Frontera"


def normalize_street_name(name):
    return " ".join(name.casefold().split())


def parse_overpass_streets(payload):
    grouped = defaultdict(lambda: {"name": "", "external_ids": [], "lines": []})

    for element in payload.get("elements", []):
        name = str(element.get("tags", {}).get("name", "")).strip()
        geometry = element.get("geometry") or []
        coordinates = [
            [point["lon"], point["lat"]]
            for point in geometry
            if "lon" in point and "lat" in point
        ]
        if not name or len(coordinates) < 2:
            continue

        key = normalize_street_name(name)
        grouped[key]["name"] = grouped[key]["name"] or name
        grouped[key]["external_ids"].append(element.get("id"))
        grouped[key]["lines"].append(coordinates)

    return [
        {
            "name": item["name"],
            "normalized_name": key,
            "external_ids": [
                external_id
                for external_id in item["external_ids"]
                if external_id is not None
            ],
            "geometry": {
                "type": "MultiLineString",
                "coordinates": item["lines"],
            },
        }
        for key, item in sorted(grouped.items())
    ]


@transaction.atomic
def save_streets(street_rows, municipality=MUNICIPALITY, prune=False):
    imported_names = set()
    created = 0
    updated = 0

    for row in street_rows:
        normalized_name = row["normalized_name"]
        imported_names.add(normalized_name)
        _, was_created = Street.objects.update_or_create(
            municipality=municipality,
            normalized_name=normalized_name,
            defaults={
                "name": row["name"],
                "geometry": row["geometry"],
                "external_ids": row["external_ids"],
                "source": "OpenStreetMap",
            },
        )
        if was_created:
            created += 1
        else:
            updated += 1

    removed = 0
    if prune:
        stale = Street.objects.filter(municipality=municipality).exclude(
            normalized_name__in=imported_names,
        )
        removed = stale.count()
        stale.delete()

    return created, updated, removed

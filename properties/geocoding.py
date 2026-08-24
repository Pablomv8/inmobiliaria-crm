import hashlib
import json
import unicodedata
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.cache import cache


CARTOCIUDAD_URL = getattr(
    settings,
    "CARTOCIUDAD_GEOCODER_URL",
    "https://www.cartociudad.es/geocoder/api/geocoder",
)
NOMINATIM_URL = getattr(
    settings,
    "NOMINATIM_GEOCODER_URL",
    "https://nominatim.openstreetmap.org/search",
)
GEOCODING_USER_AGENT = getattr(
    settings,
    "PROPERTY_GEOCODING_USER_AGENT",
    "InmobiliariaCRM/1.0 (property address geocoding)",
)
REQUEST_TIMEOUT = getattr(settings, "PROPERTY_GEOCODING_TIMEOUT", 4)


@dataclass(frozen=True)
class GeocodingResult:
    latitude: Decimal
    longitude: Decimal
    source: str
    label: str = ""


def normalize_text(value):
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    without_accents = "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )
    return " ".join(without_accents.casefold().split())


def is_arcos_de_la_frontera(city):
    return normalize_text(city) in {"arcos", "arcos de la frontera"}


def build_address(street, number, postal_code, city, province):
    street_line = " ".join(
        part.strip()
        for part in (str(street or ""), str(number or ""))
        if part and part.strip()
    )
    return ", ".join(
        part.strip()
        for part in (
            street_line,
            str(postal_code or ""),
            str(city or ""),
            str(province or ""),
            "España",
        )
        if part and part.strip()
    )


def _request_json(url, params):
    request_url = f"{url}?{urlencode({key: value for key, value in params.items() if value not in (None, '')})}"
    request = Request(
        request_url,
        headers={
            "Accept": "application/json",
            "User-Agent": GEOCODING_USER_AGENT,
        },
    )
    with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
        return json.load(response)


def _decimal_coordinates(latitude, longitude):
    try:
        latitude = Decimal(str(latitude))
        longitude = Decimal(str(longitude))
    except (InvalidOperation, TypeError, ValueError):
        return None
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return None
    return latitude, longitude


def _extract_coordinates(payload):
    if isinstance(payload, list):
        for item in payload:
            coordinates = _extract_coordinates(item)
            if coordinates:
                return coordinates
        return None

    if not isinstance(payload, dict):
        return None

    coordinates = _decimal_coordinates(
        payload.get("lat") or payload.get("latitude"),
        payload.get("lng") or payload.get("lon") or payload.get("longitude"),
    )
    if coordinates:
        return coordinates

    geometry = payload.get("geometry")
    if isinstance(geometry, dict):
        values = geometry.get("coordinates")
        if geometry.get("type") == "Point" and isinstance(values, list) and len(values) >= 2:
            coordinates = _decimal_coordinates(values[1], values[0])
            if coordinates:
                return coordinates

    for key in ("features", "results", "candidates", "items"):
        coordinates = _extract_coordinates(payload.get(key))
        if coordinates:
            return coordinates
    return None


def _cartociudad_candidates(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("candidates", "results", "items"):
            if isinstance(payload.get(key), list):
                return payload[key]
        if payload.get("id") or payload.get("lat"):
            return [payload]
    return []


def _geocode_with_cartociudad(street, number, postal_code, city, province):
    candidates = _request_json(
        f"{CARTOCIUDAD_URL}/candidates",
        {
            "q": " ".join(part for part in (street, number) if part).strip(),
            "municipio_filter": city,
            "provincia_filter": province or "Cádiz",
            "cod_postal_filter": postal_code or "",
            "limit": 5,
        },
    )
    candidate_rows = _cartociudad_candidates(candidates)
    for candidate in candidate_rows:
        coordinates = _extract_coordinates(candidate)
        if coordinates:
            return GeocodingResult(
                *coordinates,
                source="CartoCiudad",
                label=candidate.get("address", ""),
            )

    for candidate in candidate_rows:
        if not candidate.get("id") or not candidate.get("type"):
            continue
        details = _request_json(
            f"{CARTOCIUDAD_URL}/find",
            {
                "id": candidate["id"],
                "type": candidate["type"],
                "portal": number or candidate.get("portalNumber", ""),
                "outputformat": "geoJson",
            },
        )
        coordinates = _extract_coordinates(details)
        if coordinates:
            return GeocodingResult(
                *coordinates,
                source="CartoCiudad",
                label=candidate.get("address", ""),
            )
    return None


def _geocode_with_nominatim(street, number, postal_code, city, province):
    results = _request_json(
        NOMINATIM_URL,
        {
            "format": "jsonv2",
            "limit": 1,
            "countrycodes": "es",
            "q": build_address(street, number, postal_code, city, province),
        },
    )
    if not isinstance(results, list) or not results:
        return None
    coordinates = _extract_coordinates(results[0])
    if not coordinates:
        return None
    return GeocodingResult(
        *coordinates,
        source="OpenStreetMap Nominatim",
        label=results[0].get("display_name", ""),
    )


def geocode_address(street, number, postal_code="", city="", province=""):
    if not street or not number or not is_arcos_de_la_frontera(city):
        return None

    address = build_address(street, number, postal_code, city, province)
    cache_key = "property-geocoding:" + hashlib.sha256(
        normalize_text(address).encode("utf-8")
    ).hexdigest()
    cached = cache.get(cache_key)
    if cached == "not-found":
        return None
    if cached:
        return GeocodingResult(
            latitude=Decimal(cached["latitude"]),
            longitude=Decimal(cached["longitude"]),
            source=cached["source"],
            label=cached.get("label", ""),
        )

    for provider in (_geocode_with_cartociudad, _geocode_with_nominatim):
        try:
            result = provider(street, number, postal_code, city, province)
        except (OSError, ValueError, json.JSONDecodeError):
            result = None
        if result:
            cache.set(
                cache_key,
                {
                    "latitude": str(result.latitude),
                    "longitude": str(result.longitude),
                    "source": result.source,
                    "label": result.label,
                },
                60 * 60 * 24 * 30,
            )
            return result

    cache.set(cache_key, "not-found", 60 * 5)
    return None

import re

from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError


DNI_LETTERS = "TRWAGMYFPDXBNJZSQVHLCKE"
DOCUMENT_SEPARATORS = re.compile(r"[\s-]+")
PHONE_SEPARATORS = re.compile(r"[\s().-]+")
MAX_PROPERTY_IMAGE_BYTES = 8 * 1024 * 1024
MAX_PROPERTY_IMAGE_PIXELS = 40_000_000
ALLOWED_PROPERTY_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}


def normalize_identity_document(value):
    return DOCUMENT_SEPARATORS.sub("", (value or "").upper())


def validate_identity_document(value):
    document = normalize_identity_document(value)
    if not document:
        return

    dni_match = re.fullmatch(r"(\d{8})([A-Z])", document)
    if dni_match:
        expected_letter = DNI_LETTERS[int(dni_match.group(1)) % 23]
        if dni_match.group(2) != expected_letter:
            raise ValidationError(
                "La letra del DNI no corresponde con el número indicado.",
                code="invalid_dni",
            )
        return

    nie_match = re.fullmatch(r"([XYZ])(\d{7})([A-Z])", document)
    if nie_match:
        nie_number = f"{'XYZ'.index(nie_match.group(1))}{nie_match.group(2)}"
        expected_letter = DNI_LETTERS[int(nie_number) % 23]
        if nie_match.group(3) != expected_letter:
            raise ValidationError(
                "La letra del NIE no corresponde con el número indicado.",
                code="invalid_nie",
            )
        return

    if re.fullmatch(r"(?=[A-Z0-9]*[A-Z])(?=[A-Z0-9]*\d)[A-Z0-9]{6,20}", document):
        return

    raise ValidationError(
        "Introduce un DNI o NIE válido, o un pasaporte alfanumérico de 6 a 20 caracteres.",
        code="invalid_identity_document",
    )


def compact_phone_number(value):
    phone = PHONE_SEPARATORS.sub("", (value or "").strip())
    if phone.startswith("00"):
        phone = f"+{phone[2:]}"
    return phone


def validate_phone_number(value):
    phone = compact_phone_number(value)
    if not phone:
        return

    if phone.startswith("+"):
        digits = phone[1:]
        if not re.fullmatch(r"[1-9]\d{7,14}", digits):
            raise ValidationError(
                "Introduce un teléfono internacional válido, por ejemplo +34612345678.",
                code="invalid_phone",
            )
        if phone.startswith("+34") and not re.fullmatch(r"[6789]\d{8}", phone[3:]):
            raise ValidationError(
                "Los teléfonos españoles deben tener 9 cifras y comenzar por 6, 7, 8 o 9.",
                code="invalid_spanish_phone",
            )
        return

    if not re.fullmatch(r"[6789]\d{8}", phone):
        raise ValidationError(
            "Introduce un teléfono español de 9 cifras que comience por 6, 7, 8 o 9.",
            code="invalid_spanish_phone",
        )


def normalize_phone_number(value):
    phone = compact_phone_number(value)
    if phone and not phone.startswith("+"):
        return f"+34{phone}"
    return phone


def validate_spanish_postal_code(value):
    postal_code = (value or "").strip()
    if not postal_code:
        return
    if not re.fullmatch(r"(?:0[1-9]|[1-4]\d|5[0-2])\d{3}", postal_code):
        raise ValidationError(
            "Introduce un código postal español válido de 5 cifras.",
            code="invalid_postal_code",
        )


def validate_property_image(upload):
    if upload.size > MAX_PROPERTY_IMAGE_BYTES:
        raise ValidationError(
            "La imagen no puede superar los 8 MB.",
            code="image_too_large",
        )
    initial_position = upload.tell()
    try:
        image = Image.open(upload)
        image.verify()
        upload.seek(initial_position)
        image = Image.open(upload)
        if image.format not in ALLOWED_PROPERTY_IMAGE_FORMATS:
            raise ValidationError(
                "Utiliza una imagen JPEG, PNG o WEBP.",
                code="invalid_image_format",
            )
        if image.width * image.height > MAX_PROPERTY_IMAGE_PIXELS:
            raise ValidationError(
                "La resolución de la imagen es demasiado grande.",
                code="image_dimensions_too_large",
            )
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValidationError(
            "El archivo no contiene una imagen válida.",
            code="invalid_image",
        ) from exc
    finally:
        upload.seek(initial_position)

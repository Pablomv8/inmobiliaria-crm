from django import forms


class CRMDateInput(forms.DateInput):
    """Campo de fecha HTML con un valor ISO válido en cualquier idioma."""

    input_type = "date"

    def __init__(self, attrs=None, format=None):
        super().__init__(attrs=attrs, format=format or "%Y-%m-%d")


class CRMTimeInput(forms.TimeInput):
    """Campo de hora en formato de 24 horas, sin segundos innecesarios."""

    input_type = "time"

    def __init__(self, attrs=None, format=None):
        super().__init__(attrs=attrs, format=format or "%H:%M")


class CRMDateTimeInput(forms.DateTimeInput):
    """Campo de fecha y hora local compatible con los navegadores."""

    input_type = "datetime-local"

    def __init__(self, attrs=None, format=None):
        super().__init__(attrs=attrs, format=format or "%Y-%m-%dT%H:%M")

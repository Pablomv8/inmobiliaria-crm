from django import forms
from .models import News, NewsComment

INPUT_CLASS = """
w-full
rounded-xl
border
border-gray-300
bg-white
px-4
py-3
text-gray-900
shadow-sm
placeholder:text-gray-400
focus:border-indigo-500
focus:ring-4
focus:ring-indigo-100
focus:outline-none
transition-all
duration-200
"""

TEXTAREA_CLASS = INPUT_CLASS + " resize-none"


class NewsForm(forms.ModelForm):

    def __init__(self, *args, property_obj=None, **kwargs):
        super().__init__(*args, **kwargs)

        if property_obj is not None:
            self.fields.pop("related_property")

    class Meta:
        model = News
        fields = [
            "related_property",
            "motivation",
            "client_price",
            "estimated_price",
        ]

        labels = {
            "related_property": "Inmueble",
            "motivation": "Motivación",
            "client_price": "Precio cliente",
            "estimated_price": "Precio estimado",
        }

        widgets = {
            "related_property": forms.Select(attrs={
                "class": INPUT_CLASS,
            }),
            "motivation": forms.Select(attrs={
                "class": INPUT_CLASS,
            }),
            "client_price": forms.NumberInput(attrs={
                "class": INPUT_CLASS,
                "placeholder": "Ej: 250000"
            }),
            "estimated_price": forms.NumberInput(attrs={
                "class": INPUT_CLASS,
                "placeholder": "Ej: 240000"
            }),
        }

class NewsCommentForm(forms.ModelForm):

    class Meta:
        model = NewsComment
        fields = ["text"]

        widgets = {
            "text": forms.Textarea(attrs={
                "class": INPUT_CLASS,
                "rows": 3,
                "maxlength": 500,
                "placeholder": "Escribe un comentario..."
            })
        }

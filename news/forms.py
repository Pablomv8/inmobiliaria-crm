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

    MOTIVATION_CHOICES = [
        ("sale", "Venta"),
        ("rent", "Alquiler"),
    ]

    motivation = forms.ChoiceField(
        choices=MOTIVATION_CHOICES,
        widget=forms.Select(attrs={
            "class": INPUT_CLASS
        })
    )

    class Meta:
        model = News
        fields = [
            "motivation",
            "client_price",
            "estimated_price",
        ]

        labels = {
            "motivation": "Motivación",
            "client_price": "Precio cliente",
            "estimated_price": "Precio estimado",
        }

        widgets = {
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
                "placeholder": "Escribe un comentario..."
            })
        }
from django import forms
from .models import News, NewsComment
from properties.models import Property
from users.permissions import assignable_agents, can_manage_assignments

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

    def __init__(self, *args, property_obj=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["related_property"].queryset = Property.objects.filter(
            is_archived=False,
        )

        if property_obj is not None:
            self.fields.pop("related_property")

        if can_manage_assignments(user):
            self.fields["agent"].queryset = assignable_agents(
                self.instance.agent if self.instance.pk else None
            )
            self.fields["agent"].empty_label = "Selecciona un responsable"
            self.fields["agent"].required = True
            self.fields["agent"].error_messages["required"] = (
                "Selecciona la persona responsable de la noticia."
            )
            if not self.is_bound and not self.instance.pk:
                self.fields["agent"].initial = user
        else:
            self.fields.pop("agent")

    class Meta:
        model = News
        fields = [
            "related_property",
            "agent",
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
            "agent": forms.Select(attrs={"class": INPUT_CLASS}),
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

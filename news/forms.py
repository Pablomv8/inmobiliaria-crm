from django import forms

from .models import News, NewsComment

INPUT_CLASS = """
w-full
rounded-xl
border
border-gray-300
bg-gray-50
px-4
py-3
text-gray-800
placeholder-gray-400
focus:bg-white
focus:border-gray-900
focus:ring-2
focus:ring-gray-200
focus:outline-none
transition
"""


class NewsForm(forms.ModelForm):

    class Meta:

        model = News

        fields = [
            "motivation",
            "client_price",
            "estimated_price",
        ]

      

class NewsCommentForm(forms.ModelForm):

    class Meta:
        model = NewsComment
        fields = ["text"]

        widgets = {
            "text": forms.Textarea(attrs={
                "class": "w-full rounded-xl border border-gray-200 p-4 text-sm focus:ring-2 focus:ring-gray-300 focus:border-gray-300 resize-none",
                "rows": 3,
                "placeholder": "Escribe un comentario..."
            })
        }
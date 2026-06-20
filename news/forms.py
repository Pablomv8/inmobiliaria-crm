from django import forms

from .models import News, NewsComment



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

        fields = [
            "text"
        ]
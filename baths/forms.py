from datetime import time

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils import timezone

from .models import Inquiry, Message, Publication

IMAGES = [
    ("images/sauna.webp", "Светлая сауна"),
    ("images/banya.webp", "Деревянная баня"),
    ("images/interior.webp", "Интерьер парной"),
    ("images/tea.webp", "Чай"),
]


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(label="Имя", max_length=80)
    email = forms.EmailField(label="Почта")

    class Meta:
        model = User
        fields = ["first_name", "username", "email", "password1", "password2"]

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Эта почта уже используется.")
        return email


class InquiryForm(forms.ModelForm):
    consent = forms.BooleanField(
        label="Согласен на сохранение обращения и контактов для ответа"
    )
    visit_at = forms.DateTimeField(
        label="Желаемые дата и время",
        required=False,
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
        ),
    )

    class Meta:
        model = Inquiry
        fields = ["name", "email", "subject", "bath", "visit_at", "text"]
        labels = {"bath": "Помещение (для заявки)"}
        widgets = {"text": forms.Textarea(attrs={"rows": 5})}

    def clean(self):
        data = super().clean()
        visit_at = data.get("visit_at")
        bath = data.get("bath")
        if visit_at and visit_at <= timezone.now():
            self.add_error("visit_at", "Выберите будущее время.")
        if bath and not visit_at:
            self.add_error("visit_at", "Укажите желаемое время посещения.")
        if visit_at and not bath:
            self.add_error("bath", "Выберите помещение.")
        if visit_at:
            visit_time = timezone.localtime(visit_at).time()
            if visit_time < time(9) or visit_time > time(20):
                self.add_error(
                    "visit_at", "Начало двухчасового посещения — с 09:00 до 20:00."
                )
        return data


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ["text"]
        widgets = {"text": forms.Textarea(attrs={"rows": 3})}


class PublicationForm(forms.ModelForm):
    image = forms.ChoiceField(label="Изображение", choices=IMAGES)

    class Meta:
        model = Publication
        fields = [
            "title",
            "slug",
            "summary",
            "body",
            "category",
            "image",
            "image_alt",
            "published_at",
            "is_published",
        ]
        widgets = {
            "body": forms.Textarea(attrs={"rows": 8}),
            "published_at": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }
        help_texts = {
            "slug": "Короткое название латиницей, например new-sauna. Вместо пробелов — дефис."
        }

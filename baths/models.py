from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


class Bath(models.Model):
    name = models.CharField("Название", max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField("Описание")
    capacity = models.PositiveSmallIntegerField("Вместимость")
    price = models.PositiveIntegerField("Цена за час")
    features = models.CharField("Удобства", max_length=250)
    image = models.CharField("Изображение", max_length=100)
    image_alt = models.CharField("Описание изображения", max_length=200)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("baths") + "#" + self.slug


class Service(models.Model):
    name = models.CharField("Название", max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField("Описание")
    price = models.PositiveIntegerField("Цена")
    unit = models.CharField("Единица", max_length=50)
    image = models.CharField("Изображение", max_length=100)
    image_alt = models.CharField("Описание изображения", max_length=200)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("services") + "#" + self.slug


class Publication(models.Model):
    CATEGORIES = [
        ("visit", "Перед посещением"),
        ("baths", "О банях и отдыхе"),
        ("news", "Новости комплекса"),
    ]
    title = models.CharField("Заголовок", max_length=160)
    slug = models.SlugField("Адрес материала", unique=True, max_length=100)
    summary = models.CharField("Краткое описание", max_length=300)
    body = models.TextField("Текст")
    category = models.CharField("Категория", choices=CATEGORIES, max_length=20)
    image = models.CharField("Изображение", max_length=100)
    image_alt = models.CharField("Описание изображения", max_length=200)
    published_at = models.DateField("Дата публикации", default=timezone.localdate)
    is_published = models.BooleanField("Опубликовано", default=True)

    class Meta:
        ordering = ["-published_at", "-id"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        page = "news" if self.category == "news" else "journal"
        return reverse(page) + "#" + self.slug


class Inquiry(models.Model):
    STATUSES = [("new", "Новая"), ("active", "В работе"), ("closed", "Закрыта")]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    name = models.CharField("Имя", max_length=80)
    email = models.EmailField("Почта")
    subject = models.CharField("Тема", max_length=120)
    text = models.TextField("Сообщение", max_length=3000)
    bath = models.ForeignKey(Bath, on_delete=models.SET_NULL, null=True, blank=True)
    visit_at = models.DateTimeField("Желаемое время", null=True, blank=True)
    status = models.CharField("Статус", choices=STATUSES, default="new", max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class Message(models.Model):
    inquiry = models.ForeignKey(
        Inquiry, on_delete=models.CASCADE, related_name="replies"
    )
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    text = models.TextField("Сообщение", max_length=3000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

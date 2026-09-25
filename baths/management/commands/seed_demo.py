import json
from pathlib import Path

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from baths.models import Bath, Publication, Service


class Command(BaseCommand):
    help = "Добавляет учебные помещения, услуги и публикации"

    def add_arguments(self, parser):
        parser.add_argument(
            "--with-users", action="store_true", help="Создать тестовые учётные записи"
        )

    @transaction.atomic
    def handle(self, *args, **options):
        path = Path(__file__).resolve().parents[2] / "data.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        for item in data["baths"]:
            Bath.objects.get_or_create(slug=item["slug"], defaults=item)
        for item in data["services"]:
            Service.objects.get_or_create(slug=item["slug"], defaults=item)
        for item in data["publications"]:
            item["published_at"] = timezone.localdate()
            Publication.objects.get_or_create(slug=item["slug"], defaults=item)
        if options["with_users"]:
            accounts = [
                ("visitor", "Посетитель", "Visitor2026!", False),
                ("administrator", "Администратор", "Admin2026!Bath", True),
            ]
            for username, name, password, is_staff in accounts:
                user, created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        "first_name": name,
                        "email": username + "@example.com",
                        "is_staff": is_staff,
                    },
                )
                if created:
                    user.set_password(password)
                    user.save()
                    self.stdout.write("Создан пользователь: " + username)
        self.stdout.write(
            self.style.SUCCESS(
                "Начальные данные добавлены. Существующие записи сохранены."
            )
        )

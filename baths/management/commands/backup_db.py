import sqlite3
from datetime import datetime

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Сохраняет резервную копию SQLite в папку backups"

    def handle(self, *args, **options):
        folder = settings.BASE_DIR / "backups"
        folder.mkdir(exist_ok=True)
        path = folder / (
            "site-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".sqlite3"
        )
        connection.ensure_connection()
        destination = sqlite3.connect(path)
        try:
            connection.connection.backup(destination)
        finally:
            destination.close()
        self.stdout.write(str(path))

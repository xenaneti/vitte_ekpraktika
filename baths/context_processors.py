from django.conf import settings


def site(request):
    return {
        "site_name": "Тихий пар",
        "site_url": settings.SITE_URL,
        "canonical_url": settings.SITE_URL + request.path,
        "navigation": [
            ("baths", "Бани и сауны"),
            ("services", "Услуги и цены"),
            ("about", "О комплексе"),
            ("journal", "Журнал"),
            ("news", "Новости"),
            ("contacts", "Контакты"),
        ],
    }

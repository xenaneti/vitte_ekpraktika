import json
import os
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from django.contrib.auth.models import User
from playwright.sync_api import sync_playwright

from baths.models import Inquiry, Message

OUTPUT = ROOT / "docs" / "checks"
SCREENSHOTS = ROOT / "docs" / "screenshots"
BASE = "http://127.0.0.1:8000"
username = "browser_" + uuid.uuid4().hex[:8]
password = "BrowserCheck2026!"

try:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome", headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()
        page.goto(BASE + "/account/?mode=register")
        page.locator("#id_register-first_name").fill("Проверка формы")
        page.locator("#id_register-username").fill(username)
        page.locator("#id_register-email").fill(username + "@example.com")
        page.locator("#id_register-password1").fill(password)
        page.locator("#id_register-password2").fill(password)
        page.get_by_role("button", name="Зарегистрироваться").click()
        assert page.get_by_role("heading", name="Мои обращения").count() == 1
        page.goto(BASE + "/contacts/?bath=small-sauna")
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT12:00")
        page.locator("#id_visit_at").fill(tomorrow)
        page.locator("#id_text").fill("Проверка заявки: придём вдвоём, нужны два комплекта полотенец.")
        page.locator("#id_consent").check()
        page.get_by_role("button", name="Отправить обращение").click()
        inquiry_id = int(parse_qs(urlparse(page.url).query)["thread"][0])
        admin_context = browser.new_context(viewport={"width": 1280, "height": 900})
        admin_page = admin_context.new_page()
        admin_page.goto(BASE + "/account/")
        admin_page.locator("#id_username").fill("administrator")
        admin_page.locator("#id_password").fill("Admin2026!Bath")
        admin_page.get_by_role("button", name="Войти", exact=True).click()
        admin_page.goto(BASE + f"/staff/?thread={inquiry_id}")
        admin_page.locator("#conversation #id_text").fill("Подготовим два комплекта. Заявку получили.")
        admin_page.get_by_role("button", name="Отправить сообщение", exact=True).click()
        page.reload()
        assert page.get_by_text("Подготовим два комплекта. Заявку получили.", exact=True).is_visible()
        page.screenshot(path=str(SCREENSHOTS / "conversation.png"), full_page=True)
        admin_page.screenshot(path=str(SCREENSHOTS / "staff.png"), full_page=False)
        admin_page.locator("#status").select_option("closed")
        admin_page.get_by_role("button", name="Сохранить статус").click()
        page.reload()
        assert page.get_by_text("Обращение закрыто.", exact=True).is_visible()
        assert page.get_by_role("button", name="Отправить сообщение").count() == 0
        for route, name in [("/contacts/", "contact-form.png"), ("/journal/#what-to-bring", "journal.png"), ("/unknown-address/", "404.png")]:
            page.goto(BASE + route, wait_until="networkidle")
            page.screenshot(path=str(SCREENSHOTS / name), full_page=False)
        page.goto(BASE)
        page.locator("#access-toggle").click()
        page.locator("#access-theme").select_option("light")
        page.locator("#access-size").select_option("larger")
        for width in [390, 1440]:
            page.set_viewport_size({"width": width, "height": 1000})
            for route in ["/", "/baths/", "/services/", "/journal/", "/account/"]:
                page.goto(BASE + route)
                assert not page.evaluate("document.documentElement.scrollWidth > innerWidth + 1"), (width, route)
        browser.close()
    assert Inquiry.objects.get(pk=inquiry_id).user.username == username
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "workflow.json").write_text(json.dumps({"checked_at": datetime.now().astimezone().isoformat(), "browser": "Chrome", "registration": "passed", "inquiry": "passed", "admin_reply": "passed", "closing": "passed", "large_text": "passed", "cleanup": "test user and inquiry removed"}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Регистрация, заявка, ответ и закрытие обращения проверены в браузере.")
finally:
    test_users = User.objects.filter(username=username)
    Message.objects.filter(inquiry__user__in=test_users).delete()
    Inquiry.objects.filter(user__in=test_users).delete()
    test_users.delete()

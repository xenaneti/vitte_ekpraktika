import json
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "docs" / "checks"
SCREENSHOTS = ROOT / "docs" / "screenshots"
OUTPUT.mkdir(parents=True, exist_ok=True)
SCREENSHOTS.mkdir(parents=True, exist_ok=True)
BASE = "http://127.0.0.1:8000"
PAGES = [
    "/",
    "/about/",
    "/baths/",
    "/services/",
    "/journal/",
    "/news/",
    "/contacts/",
    "/account/",
    "/search/",
    "/sitemap/",
]
results = []

with sync_playwright() as playwright:
    for channel in ["chrome", "msedge"]:
        browser = playwright.chromium.launch(channel=channel, headless=True)
        page = browser.new_page(
            viewport={"width": 1440, "height": 1000}, device_scale_factor=1
        )
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        for width in [1440, 768, 390, 360]:
            page.set_viewport_size({"width": width, "height": 1000})
            for path in PAGES:
                response = page.goto(BASE + path, wait_until="networkidle")
                assert response.status == 200, (channel, width, path, response.status)
                assert page.locator("h1").count() == 1, path
                overflow = page.evaluate(
                    "document.documentElement.scrollWidth > window.innerWidth + 1"
                )
                assert not overflow, ("horizontal overflow", channel, width, path)
                assert page.locator("img:not([alt])").count() == 0, path
                broken = page.locator("img").evaluate_all(
                    "images => images.filter(img => img.complete && !img.naturalWidth).length"
                )
                assert broken == 0, ("broken images", path)
                results.append(
                    {
                        "browser": channel,
                        "width": width,
                        "page": path,
                        "status": "passed",
                    }
                )
            if channel == "chrome" and width in [1440, 390]:
                page.goto(BASE, wait_until="networkidle")
                name = "home-desktop.png" if width == 1440 else "home-mobile.png"
                page.screenshot(path=str(SCREENSHOTS / name), full_page=True)
        page.set_viewport_size({"width": 390, "height": 844})
        page.goto(BASE)
        page.get_by_role("button", name="Меню", exact=True).click()
        assert page.locator("#main-nav").is_visible()
        page.locator("#main-nav").get_by_role("link", name="Бани и сауны").click()
        assert page.url.endswith("/baths/")
        page.goto(BASE + "/search/")
        page.get_by_role("searchbox").fill("САУНА")
        page.get_by_role("button", name="Найти", exact=True).click()
        assert (
            page.locator(".search-results")
            .get_by_role("link", name="Камерная сауна", exact=True)
            .count()
            == 1
        )
        page.goto(BASE + "/journal/#what-to-bring")
        assert page.locator("#what-to-bring").get_attribute("open") is not None
        page.locator("#access-toggle").click()
        page.locator("#access-theme").select_option("dark")
        page.locator("#access-size").select_option("larger")
        page.locator("#access-spacing").check()
        page.locator("#access-images").check()
        page.goto(BASE + "/contacts/")
        assert page.locator("html").get_attribute("data-theme") == "dark"
        assert page.locator("html").get_attribute("data-size") == "larger"
        assert not page.evaluate(
            "document.documentElement.scrollWidth > innerWidth + 1"
        ), "a11y overflow"
        if channel == "chrome":
            page.screenshot(
                path=str(SCREENSHOTS / "accessible-mobile.png"), full_page=True
            )
        page.locator("#access-toggle").click()
        page.locator("#access-reset").click()
        assert page.locator("html").get_attribute("data-theme") == "normal"
        page.goto(BASE + "/account/")
        page.get_by_label("Имя пользователя").fill("visitor")
        page.get_by_label("Пароль").fill("Visitor2026!")
        page.get_by_role("button", name="Войти", exact=True).click()
        assert page.get_by_role("heading", name="Мои обращения").count() == 1
        page.get_by_role("button", name="Выйти", exact=True).click()
        assert page.url == BASE + "/"
        response = page.goto(BASE + "/unknown-address/")
        assert response.status == 404
        assert page.get_by_role("heading", name="Такой страницы нет").count() == 1
        assert errors == [], errors
        results.append(
            {
                "browser": channel,
                "scenario": "menu, search, articles, accessibility, login, logout, 404",
                "status": "passed",
                "javascript_errors": errors,
            }
        )
        browser.close()

(OUTPUT / "browser.json").write_text(
    json.dumps(
        {"checked_at": datetime.now().astimezone().isoformat(), "results": results},
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)
print(f"Проверок в браузере: {len(results)}. Все пройдены.")

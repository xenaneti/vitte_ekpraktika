import argparse
import json
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser()
parser.add_argument("--output", required=True)
args = parser.parse_args()
pages = ["/", "/about/", "/baths/", "/services/", "/journal/", "/news/", "/contacts/"]
results = []

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(channel="chrome", headless=True)
    for path in pages:
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = context.new_page()
        response = page.goto("http://127.0.0.1:8000" + path, wait_until="networkidle")
        page.evaluate("document.querySelectorAll('img').forEach(img => img.loading = 'eager')")
        page.evaluate("Promise.all(Array.from(document.images).map(img => img.decode().catch(() => {})))")
        info = page.evaluate("""() => {
          const navigation = performance.getEntriesByType('navigation')[0];
          const resources = performance.getEntriesByType('resource');
          return {
            title: document.title,
            description: document.querySelector('meta[name="description"]')?.content || '',
            h1: document.querySelectorAll('h1').length,
            images: document.images.length,
            missing_alt: document.querySelectorAll('img:not([alt]), img[alt=""]').length,
            encoded_bytes: resources.reduce((sum, item) => sum + item.encodedBodySize, navigation.encodedBodySize),
            image_bytes: resources.filter(item => item.initiatorType === 'img').reduce((sum, item) => sum + item.encodedBodySize, 0),
            load_ms: Math.round(navigation.loadEventEnd - navigation.startTime),
            requests: resources.length + 1
          };
        }""")
        info["path"] = path
        info["status"] = response.status
        results.append(info)
        context.close()
    browser.close()

output = Path(args.output)
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps({"checked_at": datetime.now().astimezone().isoformat(), "environment": "localhost, Chrome, 1440x1000, fresh context for each page", "pages": results}, ensure_ascii=False, indent=2), encoding="utf-8")
print(str(output))
print("Главная, байт:", results[0]["encoded_bytes"])

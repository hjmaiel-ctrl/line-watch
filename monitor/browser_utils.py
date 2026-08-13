"""Utility Playwright condivise per gli scraper di quote (Sportybet, Bet365)."""
from contextlib import contextmanager

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


@contextmanager
def new_page(headless: bool = True):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page(user_agent=USER_AGENT, viewport={"width": 1440, "height": 900})
        try:
            yield page
        finally:
            browser.close()


def numeric_odds_on_page(page, min_val=1.01, max_val=1000.0):
    texts = page.locator("text=/^[0-9]+\\.[0-9]{2}$/").all_inner_texts()
    out = []
    for t in texts:
        try:
            v = float(t)
            if min_val < v < max_val:
                out.append(v)
        except ValueError:
            continue
    return out

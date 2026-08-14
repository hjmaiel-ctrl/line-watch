"""Utility Playwright condivise per gli scraper di quote (Sportybet, Bet365)."""
from contextlib import contextmanager

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# Header extra per assomigliare di piu' a un browser Chrome reale: alcuni siti
# di betting (es. bet9ja, protetto da Akamai) restituiscono "Access Denied" ai
# runner GitHub Actions gia' a livello di WAF/CDN, prima ancora di caricare la
# pagina - probabilmente per reputazione dell'IP/ASN del datacenter, non solo
# per lo user-agent. Questi tentativi (header piu' realistici, flag anti-
# automazione disattivato, navigazione "riscaldata" dalla home invece che
# diretta alla pagina live) possono aiutare ma NON garantiscono di superare un
# blocco a livello di IP: se il blocco e' sulla reputazione dell'IP stesso,
# nessuna di queste modifiche lo risolve.
EXTRA_HEADERS = {
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "Upgrade-Insecure-Requests": "1",
}


@contextmanager
def new_page(headless: bool = True):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = browser.new_page(
            user_agent=USER_AGENT,
            viewport={"width": 1440, "height": 900},
            extra_http_headers=EXTRA_HEADERS,
        )
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

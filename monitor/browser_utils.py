"""Utility Playwright condivise per gli scraper di quote (Sportybet, Bet365)."""
from contextlib import contextmanager

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# Header extra per assomigliare di piu' a un browser Chrome reale: alcuni siti
# di betting (es. bet9ja, protetto da Akamai) restituivano "Access Denied" ai
# runner GitHub Actions gia' a livello di WAF/CDN, prima ancora di caricare la
# pagina - probabilmente per reputazione dell'IP/ASN del datacenter, non solo
# per lo user-agent. Questi header piu' realistici + il flag anti-automazione
# disattivato + la navigazione "riscaldata" dalla home (vedi bet9ja.py) hanno
# risolto il blocco su bet9ja (verificato il 14/08/2026, run #7: da "Access
# Denied" a 5 partite live trovate). Non e' garantito che funzioni per sempre
# o per altri siti con blocchi piu' aggressivi (es. Bet365).
EXTRA_HEADERS = {
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "Upgrade-Insecure-Requests": "1",
}

# Un solo processo Playwright + un solo browser condiviso per l'intera
# esecuzione di run.py. IMPORTANTE: l'API sync di Playwright non supporta
# istanze annidate di sync_playwright() nello stesso processo - se run.py
# tiene aperta una pagina bet9ja (dentro un "with new_page()") e nel
# frattempo sportybet.py/bet365.py chiamano di nuovo new_page(), avviare un
# SECONDO "with sync_playwright()" mentre il primo e' ancora attivo genera
# l'errore "Playwright Sync API inside the asyncio loop" (verificato nel run
# #7: bet9ja funzionava, ma sportybet/bet365 no, proprio per questo motivo).
# La soluzione e' avviare il driver Playwright e il browser UNA SOLA VOLTA
# (lazy, alla prima richiesta) e riusarli per ogni pagina, chiudendo solo la
# singola pagina (non l'intero browser) alla fine di ogni "with new_page()".
_playwright_cm = None
_playwright = None
_browser = None


def _ensure_browser(headless: bool = True):
    global _playwright_cm, _playwright, _browser
    if _browser is None:
        from playwright.sync_api import sync_playwright

        _playwright_cm = sync_playwright()
        _playwright = _playwright_cm.start()
        _browser = _playwright.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
    return _browser


def close_browser():
    """Chiude il browser e il driver Playwright condivisi. Va chiamato una
    volta a fine esecuzione (es. in run.py), non dopo ogni singola pagina."""
    global _playwright_cm, _playwright, _browser
    if _browser is not None:
        try:
            _browser.close()
        except Exception:
            pass
        _browser = None
    if _playwright_cm is not None:
        try:
            _playwright_cm.stop()
        except Exception:
            pass
        _playwright_cm = None
        _playwright = None


@contextmanager
def new_page(headless: bool = True):
    browser = _ensure_browser(headless=headless)
    page = browser.new_page(
        user_agent=USER_AGENT,
        viewport={"width": 1440, "height": 900},
        extra_http_headers=EXTRA_HEADERS,
    )
    try:
        yield page
    finally:
        try:
            page.close()
        except Exception:
            pass


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

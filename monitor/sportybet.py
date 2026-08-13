"""
Quote Sportybet (1X2, Corner O/U, Cartellini O/U) — best-effort.

Verificato navigando il sito il 13/08/2026: la pagina Single View di
https://www.sportybet.com/ng/sport/live/ mostra un evento con tab dei mercati
tra cui "Corners" e "Bookings" (cartellini). Non e' stato pero' possibile
collaudare l'estrazione dei valori riga per riga da un ambiente con accesso di
rete reale (vedi limiti descritti nel README): questa funzione usa la stessa
strategia generica di lettura testo usata nel progetto precedente (ricerca
squadra + lettura quote numeriche vicine), quindi va vista come un primo
tentativo, non come integrazione definitiva.
"""
from typing import Dict, Optional

from monitor.browser_utils import new_page, numeric_odds_on_page
from monitor.config import SPORTYBET_LIVE_URL

TAB_LABELS = {"1X2": None, "CORNERS_OU": "Corners", "CARDS_OU": "Bookings"}


def fetch_odds(home: str, away: str, markets: list) -> Dict[str, Optional[dict]]:
    result = {m: None for m in markets}
    try:
        with new_page() as page:
            page.goto(SPORTYBET_LIVE_URL, wait_until="domcontentloaded", timeout=25000)
            page.wait_for_timeout(2500)

            locator = page.get_by_text(home, exact=False)
            if locator.count() == 0:
                locator = page.get_by_text(away, exact=False)
            if locator.count() == 0:
                return result  # partita non trovata live su Sportybet in questo momento

            locator.first.click(timeout=5000)
            page.wait_for_timeout(2000)

            if "1X2" in markets:
                odds = numeric_odds_on_page(page)
                if len(odds) >= 3:
                    result["1X2"] = odds[:3]

            for market, tab_label in TAB_LABELS.items():
                if market not in markets or tab_label is None:
                    continue
                tab = page.get_by_text(tab_label, exact=True)
                if tab.count() == 0:
                    continue
                tab.first.click(timeout=5000)
                page.wait_for_timeout(1500)
                odds = numeric_odds_on_page(page)
                if len(odds) >= 2:
                    # non abbiamo un modo verificato per leggere la soglia (es. "9.5")
                    # in modo affidabile: la lasciamo a None, e' il primo aggiustamento
                    # da fare una volta collaudato con accesso reale al sito.
                    result[market] = {"line": None, "odds": odds[:2]}
    except Exception as exc:
        print(f"[sportybet] errore durante lo scraping di {home} - {away}: {exc}")
    return result

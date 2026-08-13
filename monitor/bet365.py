"""
Quote Bet365 (1X2, Corner O/U, Cartellini O/U) — MAI VERIFICATO, a rischio.

A differenza di ogni altro sito toccato in questo progetto e nel precedente,
il mio strumento di navigazione ha rifiutato di aprire bet365.com per
"restrizioni di sicurezza": non ho quindi potuto vedere la pagina nemmeno una
volta, ne' uno screenshot ne' il markup. Questo modulo e' scritto "alla cieca",
riusando la stessa strategia generica degli altri scraper (ricerca squadra +
lettura quote numeriche vicine), sapendo che:

1. Non ho nessuna conferma che questa strategia funzioni sulla struttura reale
   di bet365.com — potrebbe non trovare nulla, o trovare i numeri sbagliati.
2. Bet365 e' notoriamente il bookmaker con le protezioni anti-automazione piu'
   aggressive del settore: fingerprint del browser molto sofisticato, blocco
   attivo di IP di datacenter (compresi quelli di GitHub Actions). E' realistico
   aspettarsi che questa funzione fallisca quasi sempre in pratica.

Per questo il resto del sistema (diff.py, dashboard) e' scritto per funzionare
comunque bene anche se Bet365 non restituisce mai nulla: in quel caso il
confronto si riduce a "controlla se la linea di Sportybet e' cambiata rispetto
all'ultima volta", che resta comunque utile.

Se vuoi tenere Bet365 nel sistema, il modo piu' realistico per farlo funzionare
e' eseguire questo controllo da una rete "normale" (es. il tuo PC/ufficio,
non un runner cloud di GitHub Actions) — vedi README.md.
"""
from typing import Dict, Optional

from monitor.browser_utils import new_page, numeric_odds_on_page
from monitor.config import BET365_LIVE_URL


def fetch_odds(home: str, away: str, markets: list) -> Dict[str, Optional[dict]]:
    result = {m: None for m in markets}
    try:
        with new_page() as page:
            page.goto(BET365_LIVE_URL, wait_until="domcontentloaded", timeout=25000)
            page.wait_for_timeout(3000)

            locator = page.get_by_text(home, exact=False)
            if locator.count() == 0:
                locator = page.get_by_text(away, exact=False)
            if locator.count() == 0:
                return result

            locator.first.click(timeout=5000)
            page.wait_for_timeout(2000)

            if "1X2" in markets:
                odds = numeric_odds_on_page(page)
                if len(odds) >= 3:
                    result["1X2"] = odds[:3]
            # Corner/Cartellini: nessuna idea verificata di come navigare ai
            # rispettivi mercati su bet365, quindi non tentiamo nulla di
            # specifico oltre a quanto sopra finche' non si vede la pagina reale.
    except Exception as exc:
        print(f"[bet365] errore (atteso, mai verificato) per {home} - {away}: {exc}")
    return result

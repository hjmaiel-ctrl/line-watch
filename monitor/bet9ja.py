"""
Bet9ja: scoperta partite live + lettura statistiche live (tiri, corner,
cartellini...) + lettura delle QUOTE PROPRIE di bet9ja sui mercati Corner
Over/Under e Cartellini Over/Under.

A differenza degli scraper di Sportybet/Bet365 (best-effort, mai verificati
davvero), questo modulo e' basato su cose controllate a mano navigando
il sito il 13/08/2026:

1. Nella pagina live (https://sports.bet9ja.com/), ogni riga partita e' un
   elemento con id del tipo:
       home_live_sport-<sportid>_soccer_event-<EVENTID>_to-live-event
   e contiene due div .sports-table__home / .sports-table__away con i nomi
   delle squadre. L'EVENTID e' lo stesso usato nell'URL della pagina partita:
       https://sports.bet9ja.com/liveEvent/<EVENTID>

2. La pagina di una singola partita live incorpora il widget "Live Match
   Tracker" di Sportradar (lo stesso fornitore di dati usato da molti
   bookmaker, non solo Bet9ja), che internamente chiama un endpoint del tipo:
       https://lmt.fn.sportradar.com/.../gismo/match_detailsextended/<matchid_sportradar>?T=...
   Il "T=..." e' un token firmato con scadenza, generato dalla pagina stessa:
   non si puo' richiamare direttamente senza aprire la pagina, ma si puo'
   intercettare la risposta che il browser scarica comunque in automatico
   mentre la pagina e' aperta. E' la stessa cosa che vede chiunque apra quella
   pagina: non e' un accesso "nascosto", solo automatizzato.

   Il campo "values" della risposta contiene voci come "Yellow cards",
   "Red cards", "Corner kicks", "Shots on target", "Shots off target", ognuna
   con {home: n, away: n} — sono CONTEGGI statistici, non quote su cui si
   punta (vedi fetch_match_stats).

3. La stessa pagina della partita ha, sopra la tabella delle quote, una barra
   di tab per categoria di mercato: "Popular Markets", "Minutes",
   "Corner Markets", "Booking", "Player", "Combo +", "All". Cliccando
   "Corner Markets" appare una sezione col titolo "Corners - Over/Under"
   (una riga per ogni soglia, es. 9.5 e 10.5, con quota Over/Under);
   cliccando "Booking" appare "Cards - Over/Under" con la stessa struttura
   per i cartellini. QUESTE sono le quote proprie di bet9ja su cui si
   punterebbe (vedi fetch_market_odds) — un dato diverso e distinto dai
   conteggi Sportradar del punto 2, e non prelevato da nessun feed di terzi.

   Struttura DOM verificata (Anderlecht-PAOK, 13/08/2026): il titolo della
   sezione e' un div.accordion-text dentro un div.accordion-toggle; il
   "fratello" successivo (div.accordion-content) contiene le righe in
   div.market-row, ognuna con 3+ div.market-item: il primo e' la soglia
   (testo semplice), gli altri sono le uscite (Over/Under), ciascuna con
   un div.arrow-container il cui testo diretto (non nei figli) e' la quota.

   NOTA IMPORTANTE: la pagina live si ridisegna da sola periodicamente (nuovo
   punteggio/minuto) e questo puo' far tornare il pannello mercati alla vista
   di default "Popular Markets", anche se la tab cliccata resta evidenziata
   graficamente come attiva. fetch_market_odds quindi ritenta piu' volte
   (click + breve attesa + verifica) invece di fidarsi di un singolo click.
"""
import re
import time
from typing import List, Dict, Optional

from monitor.config import BET9JA_LIVE_URL

ROW_SELECTOR = '[id*="_to-live-event"]'
STATS_URL_PATTERN = re.compile(r"lmt\.fn\.sportradar\.com/.*/gismo/match_detailsextended/")

# nomi (case-insensitive, sottostringa) delle statistiche che ci interessano;
# il nome esatto restituito da Sportradar viene mantenuto com'e' nel risultato,
# questa e' solo la lista di cosa raccogliere.
WANTED_STATS = [
    "corner kicks", "yellow cards", "red cards", "yellow/red cards",
    "shots on target", "shots off target", "shots blocked", "fouls",
    "offsides", "free kicks", "goal kicks", "throw-ins", "saves", "penalties",
]


def discover_live_matches(page) -> List[Dict]:
    """Ritorna [{home, away, event_id, url}] per tutte le partite live di calcio
    trovate nella pagina principale."""
    page.goto(BET9JA_LIVE_URL, wait_until="domcontentloaded", timeout=25000)
    try:
        page.wait_for_selector(ROW_SELECTOR, timeout=15000)
    except Exception:
        pass  # nessuna riga apparsa in tempo: continuiamo comunque, il log sotto spiega perche'
    page.wait_for_timeout(1000)
    rows = page.query_selector_all(ROW_SELECTOR)
    # Diagnostica: se da un runner GitHub Actions troviamo 0 partite, questi log
    # servono a capire se la pagina e' stata bloccata/redirezionata (es. per IP
    # da datacenter, come succede spesso con i siti di betting) oppure se e'
    # semplicemente il momento giusto in cui non ci sono partite di calcio live.
    try:
        print(f"[bet9ja] URL effettivo dopo goto: {page.url}")
        print(f"[bet9ja] Titolo pagina: {page.title()!r}")
        body_text = page.inner_text("body")
        print(f"[bet9ja] Lunghezza testo body: {len(body_text)} caratteri")
        print(f"[bet9ja] Righe trovate con il selettore partite: {len(rows)}")
        if len(rows) == 0:
            print(f"[bet9ja] Primi 300 caratteri del body: {body_text[:300]!r}")
    except Exception as exc:
        print(f"[bet9ja] errore nella diagnostica: {exc}")
    matches = []
    for row in rows:
        row_id = row.get_attribute("id") or ""
        m = re.search(r"event-(\d+)", row_id)
        if not m:
            continue
        event_id = m.group(1)
        home_el = row.query_selector(".sports-table__home")
        away_el = row.query_selector(".sports-table__away")
        if not home_el or not away_el:
            continue
        home = home_el.inner_text().strip()
        away = away_el.inner_text().strip()
        if home and away:
            matches.append({
                "home": home,
                "away": away,
                "event_id": event_id,
                "url": f"https://sports.bet9ja.com/liveEvent/{event_id}",
            })
    # rimuovi eventuali duplicati (stessa partita puo' comparire in piu' liste/tab)
    seen = set()
    unique = []
    for m in matches:
        if m["event_id"] not in seen:
            seen.add(m["event_id"])
            unique.append(m)
    return unique


def fetch_match_stats(page, match: Dict, timeout_ms: int = 15000) -> Optional[Dict]:
    """Apre la pagina della partita e intercetta la risposta Sportradar
    match_detailsextended. Ritorna None se non arriva entro il timeout
    (partita senza tracker live, mercato non ancora iniziato, ecc)."""
    captured = {}

    def on_response(response):
        if STATS_URL_PATTERN.search(response.url):
            try:
                captured["json"] = response.json()
            except Exception:
                pass

    page.on("response", on_response)
    try:
        page.goto(match["url"], wait_until="domcontentloaded", timeout=25000)
        deadline = time.time() + timeout_ms / 1000
        while "json" not in captured and time.time() < deadline:
            page.wait_for_timeout(500)
    finally:
        page.remove_listener("response", on_response)

    raw = captured.get("json")
    if not raw:
        return None
    try:
        values = raw["doc"][0]["data"]["values"]
    except (KeyError, IndexError, TypeError):
        return None

    stats = {}
    for entry in values.values():
        name = (entry.get("name") or "").strip()
        if any(w in name.lower() for w in WANTED_STATS):
            stats[name] = entry.get("value")
    return stats or None


# --- Quote proprie di bet9ja (Corner O/U, Cartellini O/U) -------------------

# Testo esatto delle tab di categoria mercato e del titolo sezione che
# ciascuna fa apparire (verificato navigando il sito, vedi docstring modulo).
_MARKET_TABS = {
    "CORNERS_OU": {"tab": "Corner Markets", "header": "Corners - Over/Under"},
    "CARDS_OU": {"tab": "Booking", "header": "Cards - Over/Under"},
}

# Eseguito nel contesto della pagina: trova la sezione con questo titolo
# esatto e ne estrae le righe (soglia + quota Over + quota Under). Ritorna
# [] se la sezione non e' (ancora) visibile in questo momento.
_PARSE_OU_SECTION_JS = """
(headerText) => {
    function findLeafByText(txt) {
        const all = Array.from(document.querySelectorAll('body *'));
        return all.find(el => el.children.length === 0 && el.textContent.trim() === txt);
    }
    function ownText(el) {
        let t = '';
        for ((const n of el.childNodes) {
            if (n.nodeType === Node.TEXT_NODE) t += n.textContent;
        }
        return t.trim();
    }
    const header = findLeafByText(headerText);
    if (!header) return [];
    const accordionItem = header.parentElement.parentElement;
    const body = Array.from(accordionItem.children).find(c => c !== header.parentElement);
    if (!body) return [];
    const rows = Array.from(body.querySelectorAll('.market-row'));
    return rows.map(row => {
        const items = Array.from(row.querySelectorAll(':scope > .market-item'));
        if (items.length < 3) return null;
        const line = ownText(items[0].querySelector('div')) || items[0].textContent.trim();
        const overEl = items[1].querySelector('.arrow-container');
        const underEl = items[2].querySelector('.arrow-container');
        return {
            line: line,
            over: overEl ? ownText(overEl) : null,
            under: underEl ? ownText(underEl) : null,
        };
    }).filter(Boolean);
}
"""


def _to_float(value) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _click_tab(page, tab_text: str) -> bool:
    """Clicca la tab di categoria mercato con questo testo esatto (es.
    "Corner Markets", "Booking"). Ritorna False se la tab non e' presente
    o il click fallisce (partita senza quel mercato in questo momento)."""
    try:
        tab = page.get_by_text(tab_text, exact=True)
        if tab.count() == 0:
            return False
        tab.first.click(timeout=5000)
        return True
    except Exception:
        return False


def _parse_ou_section(page, header_text: str) -> List[Dict]:
    try:
        raw_rows = page.evaluate(_PARSE_OU_SECTION_JS, header_text)
    except Exception:
        return []
    parsed = []
    for r in raw_rows or []:
        over = _to_float(r.get("over"))
        under = _to_float(r.get("under"))
        if over is None and under is None:
            continue
        line = _to_float(r.get("line"))
        if line is None:
            line = r.get("line")
        parsed.append({"line": line, "over": over, "under": under})
    return parsed


def _read_ou_section_with_retry(page, tab_text: str, header_text: str,
                                 attempts: int = 4, wait_ms: int = 600) -> List[Dict]:
    """Clicca la tab e legge la sezione, riprovando piu' volte: la pagina live
    di bet9ja si puo' ridisegnare da sola (nuovo punteggio/minuto) e resettare
    la vista a "Popular Markets" subito dopo un click riuscito."""
    for _ in range(attempts):
        _click_tab(page, tab_text)
        page.wait_for_timeout(wait_ms)
        rows = _parse_ou_section(page, header_text)
        if rows:
            return rows
    return []


def fetch_market_odds(page, match: Dict) -> Dict[str, Optional[dict]]:
    """Legge le QUOTE PROPRIE di bet9ja (non i conteggi Sportradar) per i
    mercati Corner Over/Under e Cartellini Over/Under, dalla pagina della
    partita live gia' aperta (stesso `page` usato da fetch_match_stats — non
    ricarica la pagina).

    Ritorna un dizionario con chiavi "CORNERS_OU" e "CARDS_OU" (le uniche
    richieste); ogni valore e', se trovato:
        {"line": 9.5, "odds": [over, under], "_all_lines": [...]}
    oppure None se il mercato non era disponibile/visibile in questo giro.

    Per ciascun mercato bet9ja mostra spesso piu' soglie contemporaneamente
    (es. Corner 9.5 E 10.5): si tiene come "line"/"odds" principali solo la
    PRIMA elencata da bet9ja (quella piu' vicina al gioco in corso), e si
    conservano tutte in "_all_lines" per riferimento/dashboard. Il confronto
    con Sportybet/Bet365 in diff.py usa solo la soglia principale.
    """
    result: Dict[str, Optional[dict]] = {}
    for market, cfg in _MARKET_TABS.items():
        rows = _read_ou_section_with_retry(page, cfg["tab"], cfg["header"])
        if not rows:
            result[market] = None
            continue
        first = rows[0]
        result[market] = {
            "line": first["line"],
            "odds": [first["over"], first["under"]],
            "_all_lines": rows,
        }
    return result

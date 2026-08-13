"""
Logica di confronto: decide quando generare un avviso.

Due tipi di avviso, esattamente come richiesto:
1. "quota differente" - Bet365 e Sportybet hanno quote troppo diverse tra loro
   sullo stesso mercato/partita in questo momento.
2. "linea cambiata" - la soglia di un mercato (es. Over/Under corner) o la quota
   stessa di un bookmaker e' cambiata rispetto all'ultimo controllo.
"""
import itertools
from typing import Optional

from monitor.config import MARKETS, ODDS_DIFF_THRESHOLD_PCT, ODDS_MOVE_THRESHOLD_PCT


def _pct_diff(a: float, b: float) -> float:
    if a == 0 or b == 0:
        return 0.0
    return abs(a - b) / min(a, b) * 100.0


def compare_bookmakers(match_label: str, market: str, odds_a: dict, book_a: str, odds_b: dict, book_b: str):
    """Confronta le quote di due bookmaker per lo stesso mercato/partita in questo momento."""
    alerts = []
    if odds_a is None or odds_b is None:
        return alerts
    line_a = odds_a.get("line") if isinstance(odds_a, dict) else None
    line_b = odds_b.get("line") if isinstance(odds_b, dict) else None
    values_a = odds_a.get("odds") if isinstance(odds_a, dict) else odds_a
    values_b = odds_b.get("odds") if isinstance(odds_b, dict) else odds_b

    if line_a is not None and line_b is not None and line_a != line_b:
        alerts.append({
            "type": "linea_diversa_tra_bookmaker",
            "match": match_label,
            "market": market,
            "detail": f"{book_a} ha la linea a {line_a}, {book_b} a {line_b}",
        })

    if values_a and values_b and len(values_a) == len(values_b):
        for i, (va, vb) in enumerate(zip(values_a, values_b)):
            if va and vb:
                diff = _pct_diff(va, vb)
                if diff >= ODDS_DIFF_THRESHOLD_PCT:
                    alerts.append({
                        "type": "quota_differente",
                        "match": match_label,
                        "market": market,
                        "detail": f"{book_a}={va} vs {book_b}={vb} (esito #{i+1}, differenza {diff:.1f}%)",
                    })
    return alerts


def compare_with_previous(match_label: str, market: str, bookmaker: str, current: dict, previous: Optional[dict]):
    """Confronta la quota/linea attuale di UN bookmaker con quella salvata al giro precedente."""
    alerts = []
    if previous is None or current is None:
        return alerts
    line_now = current.get("line") if isinstance(current, dict) else None
    line_before = previous.get("line") if isinstance(previous, dict) else None
    values_now = current.get("odds") if isinstance(current, dict) else current
    values_before = previous.get("odds") if isinstance(previous, dict) else previous

    if line_now is not None and line_before is not None and line_now != line_before:
        alerts.append({
            "type": "linea_cambiata",
            "match": match_label,
            "market": market,
            "detail": f"{bookmaker}: linea passata da {line_before} a {line_now}",
        })

    if values_now and values_before and len(values_now) == len(values_before):
        for i, (vn, vb) in enumerate(zip(values_now, values_before)):
            if vn and vb:
                diff = _pct_diff(vn, vb)
                if diff >= ODDS_MOVE_THRESHOLD_PCT:
                    alerts.append({
                        "type": "quota_cambiata",
                        "match": match_label,
                        "market": market,
                        "detail": f"{bookmaker}: esito #{i+1} passato da {vb} a {vn} ({diff:.1f}%)",
                    })
    return alerts


def build_alerts_for_match(match_label: str, odds_by_bookmaker: dict, previous_odds_by_bookmaker: dict):
    """odds_by_bookmaker: {'bet9ja': {market: odds_or_dict}, 'bet365': {...}, 'sportybet': {...}}

    Confronta OGNI coppia di fonti tra loro (non solo le prime due), cosi'
    bet9ja/bet365/sportybet vengono tutti controllati a vicenda. Una fonte con
    dato None per un mercato (es. bet9ja su 1X2, che non legge) viene
    semplicemente ignorata in quel confronto — vedi compare_bookmakers."""
    alerts = []
    books = list(odds_by_bookmaker.keys())
    for market in MARKETS:
        # confronto di ogni coppia di bookmaker tra loro, in questo momento
        for book_a, book_b in itertools.combinations(books, 2):
            odds_a = odds_by_bookmaker.get(book_a, {}).get(market)
            odds_b = odds_by_bookmaker.get(book_b, {}).get(market)
            alerts += compare_bookmakers(match_label, market, odds_a, book_a, odds_b, book_b)
        # confronto di ciascun bookmaker con il proprio dato del giro precedente
        for book in books:
            current = odds_by_bookmaker.get(book, {}).get(market)
            previous = (previous_odds_by_bookmaker or {}).get(book, {}).get(market)
            alerts += compare_with_previous(match_label, market, book, current, previous)
    return alerts

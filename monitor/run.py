"""
Punto di ingresso principale: un'esecuzione completa del controllo.

Eseguito dal workflow GitHub Actions ogni N minuti (vedi
.github/workflows/monitor.yml). Ogni esecuzione:

1. Scopre le partite live su Bet9ja e ne legge le statistiche (tiri, corner,
   cartellini) dal feed Sportradar incorporato nella pagina.
2. Per le stesse partite, prova a leggere le quote su Sportybet e Bet365.
3. Confronta le quote attuali tra i due bookmaker, e con quelle salvate al
   giro precedente, generando avvisi quando c'e' una differenza rilevante o
   un cambio di linea.
4. Manda gli avvisi su Slack, aggiorna il log e i dati per la dashboard.
"""
import sys
import time
import traceback

from monitor import bet9ja, sportybet, bet365, slack
from monitor.config import MARKETS, STATE_PATH, DASHBOARD_DATA_PATH
from monitor.diff import build_alerts_for_match
from monitor.matching import best_match
from monitor.state import load_state, save_state, append_alerts_log, write_dashboard_data
from monitor.browser_utils import new_page


def match_key(home: str, away: str) -> str:
    return f"{home.strip()}|{away.strip()}"


def run_once(max_matches: int = 12):
    state = load_state()
    previous_matches = state.get("matches", {})
    new_matches_state = {}
    all_alerts = []
    dashboard_rows = []

    with new_page() as bet9ja_page:
        try:
            live_matches = bet9ja.discover_live_matches(bet9ja_page)
        except Exception:
            print("[run] errore scoprendo le partite live su Bet9ja:")
            traceback.print_exc()
            live_matches = []

        print(f"[run] {len(live_matches)} partite live trovate su Bet9ja.")
        live_matches = live_matches[:max_matches]  # limite di sicurezza per non far durare troppo un singolo giro

        for match in live_matches:
            label = f"{match['home']} - {match['away']}"
            print(f"[run] partita: {label}")

            try:
                stats = bet9ja.fetch_match_stats(bet9ja_page, match)
            except Exception:
                print(f"[run] errore leggendo le statistiche di {label}:")
                traceback.print_exc()
                stats = None

            odds_by_bookmaker = {}

            # Quote proprie di bet9ja (Corner O/U, Cartellini O/U) — lette
            # dalla stessa pagina partita gia' aperta per le statistiche,
            # nessuna richiesta di rete aggiuntiva.
            try:
                bet9ja_odds = bet9ja.fetch_market_odds(bet9ja_page, match)
            except Exception:
                print(f"[run] errore leggendo le quote di bet9ja per {label}:")
                traceback.print_exc()
                bet9ja_odds = {}
            odds_by_bookmaker["bet9ja"] = {m: bet9ja_odds.get(m) for m in MARKETS}

            for module, name in ((sportybet, "sportybet"), (bet365, "bet365")):
                try:
                    odds_by_bookmaker[name] = module.fetch_odds(match["home"], match["away"], MARKETS)
                except Exception:
                    print(f"[run] errore leggendo le quote {name} per {label}:")
                    traceback.print_exc()
                    odds_by_bookmaker[name] = {m: None for m in MARKETS}

            key = match_key(match["home"], match["away"])
            previous_entry = previous_matches.get(key, {})
            previous_odds = previous_entry.get("odds", {})

            alerts = build_alerts_for_match(label, odds_by_bookmaker, previous_odds)
            all_alerts.extend(alerts)

            new_matches_state[key] = {
                "home": match["home"],
                "away": match["away"],
                "event_id": match["event_id"],
                "odds": odds_by_bookmaker,
                "last_checked": time.time(),
            }
            dashboard_rows.append({
                "match": label,
                "bet9ja_stats": stats,
                "odds": odds_by_bookmaker,
                "alerts": [a for a in alerts if a["match"] == label],
            })

    save_state({"matches": new_matches_state})
    append_alerts_log(all_alerts)
    write_dashboard_data({
        "generated_at": time.time(),
        "matches": dashboard_rows,
        "alert_count_this_run": len(all_alerts),
    }, DASHBOARD_DATA_PATH)

    if all_alerts:
        print(f"[run] {len(all_alerts)} avvisi generati, invio su Slack.")
        slack.send_alerts(all_alerts)
    else:
        print("[run] nessun avviso in questo giro.")

    return {"matches_checked": len(new_matches_state), "alerts": len(all_alerts)}


if __name__ == "__main__":
    summary = run_once()
    print(f"[run] fatto: {summary}")

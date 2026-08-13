"""
Persistenza dello stato tra un'esecuzione e la successiva.

Ogni esecuzione di GitHub Actions parte da una macchina nuova e vuota: per
"ricordare" le quote dell'ultimo controllo (necessario per capire se una linea
e' cambiata) lo stato viene letto/scritto come file JSON dentro al repository,
e il workflow lo ri-committa a ogni esecuzione (vedi .github/workflows/monitor.yml).
"""
import json
import os
from pathlib import Path

from monitor.config import STATE_PATH, ALERTS_LOG_PATH


def _abspath(rel_path: str) -> Path:
    root = Path(__file__).resolve().parent.parent
    return root / rel_path


def load_state() -> dict:
    path = _abspath(STATE_PATH)
    if not path.exists():
        return {"matches": {}}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {"matches": {}}


def save_state(state: dict):
    path = _abspath(STATE_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def append_alerts_log(alerts: list):
    if not alerts:
        return
    path = _abspath(ALERTS_LOG_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = []
    if path.exists():
        try:
            existing = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            existing = []
    existing = (existing + alerts)[-500:]  # tieni solo gli ultimi 500 per non far crescere il file all'infinito
    path.write_text(json.dumps(existing, indent=2, ensure_ascii=False))


def write_dashboard_data(payload: dict, dashboard_path: str):
    path = _abspath(dashboard_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))

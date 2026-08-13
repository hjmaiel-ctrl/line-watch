"""
Invio avvisi su Slack tramite Incoming Webhook.

Serve creare un Incoming Webhook nel proprio workspace Slack (vedi README.md)
e salvarlo come secret `SLACK_WEBHOOK_URL` nel repository GitHub. Non e' incluso
nessun token nel codice: viene letto solo dalla variabile d'ambiente.
"""
import os
import requests

WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "").strip()


def send_alerts(alerts: list):
      if not alerts:
                return
            if not WEBHOOK_URL:
                      print(f"[slack] SLACK_WEBHOOK_URL non impostato: {len(alerts)} avvisi non inviati (solo salvati nel log/dashboard).")
                      return
                  lines = ["*Line Watch — avvisi*"]
    for a in alerts:
              emoji = {
                            "quota_differente": "⚖️",
                            "linea_cambiata": "📈",
                            "quota_cambiata": "🔁",
                            "linea_diversa_tra_bookmaker": "🧭",
              }.get(a["type"], "•")
              lines.append(f"{emoji} *{a['match']}* — {a['market']}: {a['detail']}")
          text = "\n".join(lines)
    try:
              resp = requests.post(WEBHOOK_URL, json={"text": text}, timeout=10)
              if resp.status_code >= 300:
                            print(f"[slack] invio fallito: HTTP {resp.status_code} {resp.text[:200]}")
    except Exception as exc:
        print(f"[slack] errore invio: {exc}")

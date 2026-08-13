"""
Configurazione di Line Watch.

Cosa fa il sistema, in breve:
- legge le partite live su Bet9ja e le statistiche live (tiri, corner, cartellini...)
  tramite il feed Sportradar che Bet9ja stesso usa per il proprio widget (verificato
  navigando il sito, non e' un'API nascosta o protetta: e' lo stesso dato che vede
  chiunque apra la pagina della partita su Bet9ja).
- legge anche le QUOTE PROPRIE di bet9ja (non i conteggi Sportradar sopra) sui
  mercati Corner Over/Under e Cartellini Over/Under, direttamente dalle tab
  "Corner Markets"/"Booking" della pagina partita.
- per le stesse partite, prova a leggere le quote su Bet365 e Sportybet.
- confronta le quote di bet9ja, Bet365 e Sportybet tra loro (ogni coppia): se
  sono troppo diverse, o se una linea (es. la soglia di un Over/Under) e'
  cambiata rispetto al controllo precedente, manda un avviso su Slack e lo
  mostra sulla dashboard.

IMPORTANTE su Bet365: a differenza di tutti gli altri siti toccati in questo e nel
progetto precedente, il mio stesso strumento di navigazione ha bloccato l'accesso a
bet365.com per "restrizioni di sicurezza" - non ho quindi potuto vedere la pagina
nemmeno una volta, a differenza di Sportybet/Bet9ja di cui ho verificato la
struttura. Lo scraper per Bet365 (monitor/bet365.py) e' scritto "alla cieca", con la
stessa logica generica usata altrove: e' ragionevole aspettarsi che non funzioni
quasi mai, sia perche' non e' stato possibile verificarne la struttura, sia perche'
Bet365 e' notoriamente il bookmaker con le protezioni anti-automazione piu' aggressive
del settore (fingerprint del browser, blocco di IP di datacenter come quelli di
GitHub Actions). Vedi README.md.
"""

# Mercati da confrontare tra Bet365 e Sportybet per ogni partita.
# Scelti in base alle statistiche che si leggono da Bet9ja (corner/cartellini),
# piu' 1X2 come riferimento generale.
MARKETS = ["1X2", "CORNERS_OU", "CARDS_OU"]

# Soglia sopra la quale una differenza di quota tra Bet365 e Sportybet
# genera un avviso (in percentuale sulla quota piu' bassa delle due).
ODDS_DIFF_THRESHOLD_PCT = 5.0

# Soglia sopra la quale un cambiamento di quota (stesso mercato, stessa soglia)
# rispetto al controllo precedente genera un avviso "quota cambiata"
# (indipendente dal cambio di soglia/linea, che genera comunque sempre avviso).
ODDS_MOVE_THRESHOLD_PCT = 8.0

# Ogni quanto viene eseguito il controllo: impostato nel workflow GitHub Actions
# (.github/workflows/monitor.yml), non qui. Di default ogni 10 minuti: GitHub
# Actions non garantisce precisione al minuto sui cron gratuiti, quindi
# "continuo" va inteso come "controllo periodico ogni ~10 minuti", non realtime.

STATE_PATH = "data/state.json"
DASHBOARD_DATA_PATH = "docs/data.json"
ALERTS_LOG_PATH = "data/alerts_log.json"

BET9JA_LIVE_URL = "https://sports.bet9ja.com/liveEvent"
SPORTYBET_LIVE_URL = "https://www.sportybet.com/ng/sport/live/"
BET365_LIVE_URL = "https://www.bet365.com/#/AC/B1/C1/D1002/E0/F2/"  # da verificare, mai visto davvero

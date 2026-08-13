# Line Watch

Controllo periodico (gratuito, su GitHub) delle partite live: legge le
statistiche live di Bet9ja (tiri, corner, cartellini...) E le quote proprie
di Bet9ja sui mercati Corner/Cartellini Over-Under, poi confronta queste
ultime con le quote di Bet365 e Sportybet sulle stesse partite, avvisando su
Slack e su una dashboard quando due quote sono troppo diverse tra loro o
quando una linea è cambiata rispetto al controllo precedente.

## Cosa è verificato e cosa no (leggi prima di fidarti dei risultati)

Ho costruito questo sistema controllando davvero i siti coinvolti (13/08/2026),
e la qualità/affidabilità delle fonti è molto diversa:

| Fonte | Stato | Perché |
|---|---|---|
| **Bet9ja — statistiche live** (`monitor/bet9ja.py`, `fetch_match_stats`) | ✅ Verificato | Ho trovato gli elementi reali della pagina (selettore `[id*="_to-live-event"]` per l'elenco partite live, feed JSON di Sportradar `match_detailsextended` incorporato nella pagina della singola partita) e ho testato l'estrazione con dati reali presi dal sito. È lo stesso dato che vede chiunque apra la pagina della partita su Bet9ja, solo letto in automatico. Sono CONTEGGI (es. "5 corner finora"), non quote. |
| **Bet9ja — quote proprie Corner/Cartellini O/U** (`monitor/bet9ja.py`, `fetch_market_odds`) | ✅ Verificato | Ho cliccato le tab "Corner Markets" e "Booking" sulla pagina di una partita live reale (Anderlecht-PAOK) e trovato la struttura esatta delle sezioni "Corners - Over/Under" e "Cards - Over/Under" (classi `market-row`/`market-item`/`arrow-container`), testando l'estrazione con dati reali. **Attenzione**: la pagina si ridisegna da sola ogni tanto e a volte questo fa perdere la tab selezionata (torna a "Popular Markets") anche se visivamente resta evidenziata come attiva — per questo la funzione ritenta il click più volte prima di rinunciare. |
| **Sportybet — quote** (`monitor/sportybet.py`) | 🟡 Best-effort | Ho visto la pagina (le tab dei mercati "Corners"/"Bookings" esistono davvero), ma non ho potuto collaudare l'estrazione dei valori con un accesso di rete reale da questo ambiente. Va rifinita al primo uso vero. |
| **Bet365 — quote** (`monitor/bet365.py`) | 🔴 Mai verificato, a rischio | Il mio stesso strumento di navigazione ha bloccato bet365.com per "restrizioni di sicurezza": non ho **mai visto la pagina**, nemmeno uno screenshot. Il codice è scritto alla cieca, riusando la stessa logica generica di Sportybet. Bet365 è anche notoriamente il bookmaker con le protezioni anti-automazione più aggressive del settore (fingerprint del browser, blocco di IP di datacenter): è realistico che questa parte non funzioni quasi mai da un runner GitHub Actions. Il resto del sistema è scritto per restare utile anche se Bet365 non risponde mai (in quel caso vedi comunque il confronto bet9ja vs Sportybet, che resta un segnale valido). |

Se dopo il primo utilizzo reale Sportybet o Bet365 non funzionano, i file da
aggiustare sono `monitor/sportybet.py` e `monitor/bet365.py` — l'interfaccia
(una funzione `fetch_odds(home, away, markets)`) resta la stessa, cambia solo
come si legge la pagina.

## Come funziona un giro di controllo

1. `monitor/bet9ja.py` apre `sports.bet9ja.com`, trova tutte le partite di
   calcio live, e per ognuna apre la pagina della partita per: (a) intercettare
   il feed Sportradar con tiri/corner/cartellini/ecc (conteggi), e (b) leggere
   le quote proprie di bet9ja sui mercati Corner Over/Under e Cartellini
   Over/Under (`fetch_market_odds`), sulla stessa pagina già aperta.
2. Per la stessa partita, `monitor/sportybet.py` e `monitor/bet365.py`
   provano a leggere le quote su 1X2, Corner Over/Under e Cartellini
   Over/Under.
3. `monitor/diff.py` confronta le quote di bet9ja, Bet365 e Sportybet tra loro
   *in questo momento* (ogni coppia), e le confronta anche con quelle salvate
   al giro precedente (`data/state.json`) per capire se una linea è cambiata.
4. Ogni differenza sopra soglia genera un avviso, mandato su Slack
   (`monitor/slack.py`) e salvato in `docs/data.json` (letto dalla dashboard)
   e in `data/alerts_log.json` (storico).

Nota: per i mercati Corner/Cartellini, bet9ja spesso mostra più soglie insieme
(es. Corner 9.5 E 10.5): il sistema usa come riferimento principale solo la
prima elencata da bet9ja (quella più vicina al gioco in corso); tutte le
soglie viste sono comunque salvate (campo `_all_lines`) per riferimento.

Le soglie (quanto deve essere diversa una quota per generare un avviso, quali
mercati controllare) sono in `monitor/config.py`.

## Perché GitHub Actions + GitHub Pages (invece di Hugging Face)

Hai chiesto un'alternativa gratuita che possa controllare "in continuo": Hugging
Face Spaces gratuiti si "addormentano" dopo un periodo di inattività, il che è
un problema per un controllo che deve girare da solo. GitHub Actions no: puoi
programmare un'esecuzione ogni N minuti (qui impostato a 10) senza bisogno di
nessun server sempre acceso, ed è gratuito entro limiti piuttosto generosi
(2.000 minuti/mese sui repository privati, illimitati su quelli pubblici).
GitHub Pages ospita gratuitamente la dashboard statica.

Il compromesso: non è realtime, è "controllo ogni 10 minuti" (GitHub non
garantisce nemmeno quella precisione al minuto nei momenti di traffico alto).
Se ti serve davvero continuo (ogni 30-60 secondi), l'alternativa gratuita più
vicina è una macchina virtuale "Always Free" di Oracle Cloud, ma richiede più
lavoro di configurazione — dimmelo se vuoi che prepari anche quella versione.

## Come metterlo in piedi

1. **Crea un repository GitHub** (gratuito, anche privato) e caricaci dentro
   tutto il contenuto di questa cartella.
2. **Crea un Incoming Webhook su Slack**: nel tuo workspace Slack, vai su
   [api.slack.com/apps](https://api.slack.com/apps) → "Create New App" → "From
   scratch" → dai un nome (es. "Line Watch") e scegli il workspace → nella
   sezione "Incoming Webhooks" attivali e clicca "Add New Webhook to
   Workspace", scegliendo il canale dove vuoi ricevere gli avvisi. Copia l'URL
   del webhook che ti viene mostrato (inizia con `https://hooks.slack.com/...`).
3. **Salva il webhook come secret**: nel repository GitHub, vai su Settings →
   Secrets and variables → Actions → "New repository secret". Nome:
   `SLACK_WEBHOOK_URL`, valore: l'URL copiato al punto 2.
4. **Attiva GitHub Pages**: Settings → Pages → sotto "Build and deployment",
   Source: "Deploy from a branch", Branch: `main` (o quella che usi), cartella
   `/docs`. Dopo qualche minuto la dashboard sarà visibile a un URL del tipo
   `https://<tuo-utente>.github.io/<nome-repo>/`.
5. **Il workflow parte da solo**: è già programmato ogni 10 minuti
   (`.github/workflows/monitor.yml`). Puoi anche farlo partire a mano dalla tab
   "Actions" del repository → "Line Watch monitor" → "Run workflow", utile per
   il primo test senza aspettare il prossimo giro programmato.

## Eseguirlo in locale (per collaudare Sportybet/Bet365 con accesso di rete vero)

```bash
pip install -r requirements.txt
python -m playwright install chromium
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."   # opzionale
python -m monitor.run
```

Un giro scrive/aggiorna `data/state.json`, `data/alerts_log.json` e
`docs/data.json` — apri quest'ultimo file (o `docs/index.html` con un piccolo
server statico, es. `python -m http.server` dentro `docs/`) per vedere il
risultato.

## Struttura del progetto

```
monitor/
  config.py          mercati, soglie, URL
  matching.py        abbinamento partite tra bookmaker diversi
  bet9ja.py          scoperta partite + statistiche live (VERIFICATO)
  sportybet.py       quote Sportybet (best-effort)
  bet365.py          quote Bet365 (mai verificato, a rischio)
  diff.py            logica degli avvisi
  slack.py           invio su Slack
  state.py           salvataggio/lettura dati tra un giro e il successivo
  run.py             punto di ingresso, orchestrazione di un giro completo
.github/workflows/monitor.yml    cron GitHub Actions
docs/
  index.html         dashboard (GitHub Pages)
  data.json           dati dell'ultimo giro (aggiornato automaticamente)
data/
  state.json          stato persistente tra un giro e il successivo
  alerts_log.json      storico avvisi (ultimi 500)
```

## Limiti da tenere a mente

- **Numero di partite per giro**: limitato a 12 (`max_matches` in
  `monitor/run.py`) per stare dentro al timeout di un job GitHub Actions
  (8 minuti). Se ci sono più partite live di calcio disponibili, quelle in più
  vengono ignorate in quel giro — aumentalo se serve, ma tieni d'occhio la
  durata del job.
- **Abbinamento partite**: fatto per somiglianza dei nomi delle squadre
  (`monitor/matching.py`), non per ID condiviso tra bookmaker — con nomi molto
  diversi tra un sito e l'altro può non abbinare correttamente.
- **La soglia (`line`) di Corner/Cartellini O/U su Sportybet e Bet365** non è
  ancora letta in modo verificato (vedi i commenti in `sportybet.py`/
  `bet365.py`): per queste due fonti resta `None` finché non si rifinisce con
  un vero accesso al sito. Per bet9ja invece la soglia è verificata e letta
  correttamente (vedi tabella sopra).

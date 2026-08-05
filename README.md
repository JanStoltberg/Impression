# Impression — Morning Briefing

Kuratiert automatisch die wichtigsten Meldungen aus deinen Fachmedien
(HORIZONT, W&V, ADZINE, Digiday, AdExchanger, Adweek, Ad Age ...) und
veröffentlicht sie als kleine Website auf GitHub Pages.

```
Feeds (RSS) → ingest.py → curate.py → data/briefings/*.json → Astro-Build → GitHub Pages
```

## Struktur

```
scripts/
  sources.yaml    Liste der RSS-Quellen (Region, Themenkategorie)
  ingest.py       Laedt alle Feeds, schreibt Rohdaten nach data/raw/
  curate.py       Dedupe, Ranking, Auswahl -> data/briefings/<datum>.json
data/
  briefings/      Ein JSON-File pro Tag - das ist das Archiv, wird versioniert
  raw/            Zwischenstand, nicht versioniert (.gitignore)
site/             Astro-Projekt, liest aus ../data/briefings
.github/workflows/
  daily-briefing.yml   Cron-Job: ingest+curate+commit, dann Build+Deploy
```
## Lokal entwickeln

```bash
# Pipeline
pip install -r requirements.txt --break-system-packages
python scripts/ingest.py
python scripts/curate.py

# Website
cd site
npm install
npm run dev      # lokaler Dev-Server
npm run build    # Produktions-Build nach site/dist/
```

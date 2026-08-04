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

## Einmaliges Setup

1. **Repo pushen.** Dieses Verzeichnis in ein neues GitHub-Repo pushen.

2. **GitHub Pages aktivieren.** Im Repo unter *Settings → Pages* als
   Source **"GitHub Actions"** waehlen (nicht "Deploy from a branch").

3. ~~`site/astro.config.mjs` anpassen~~ — bereits fertig konfiguriert fuer
   `github.com/JanStoltberg/Impression`. Die Seite ist danach erreichbar
   unter **https://JanStoltberg.github.io/Impression/**. Falls das Repo
   spaeter umbenannt wird, hier `site`/`base` entsprechend nachziehen.

4. **Quellen pruefen.** In `scripts/sources.yaml` sind zwei Feeds mit
   `# TODO` markiert (ADZINE, Ad Age) - deren RSS-URL war beim Erstellen
   nicht zweifelsfrei verifizierbar. Kurz im Browser oeffnen und ggf.
   korrigieren. Eigene Quellen lassen sich nach demselben Schema ergaenzen.

5. **Optional: Claude API fuer besseres Ranking.** Ohne weiteres Zutun
   laeuft ein regelbasiertes Ranking (Keywords + Aktualitaet). Fuer
   LLM-gestuetztes Ranking mit Editorial-Einordnung pro Artikel:
   *Settings → Secrets and variables → Actions* → neues Secret
   `ANTHROPIC_API_KEY` anlegen.

6. **Cron-Zeit anpassen (optional).** In
   `.github/workflows/daily-briefing.yml` steht `cron: '0 5 * * *'`
   (5 Uhr UTC). Andere Uhrzeit nach Bedarf eintragen.

Danach laeuft der Workflow taeglich automatisch. Zum Testen: im Reiter
*Actions* den Workflow "Daily Briefing" manuell per "Run workflow" starten.

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

## Naechste sinnvolle Schritte

- **Kategorie-Seiten erweitern:** `site/src/pages/kategorie/[topic].astro`
  zeigt aktuell nur das juengste Briefing pro Kategorie. Fuer eine
  Kategorie-Historie ueber mehrere Tage muesste hier zusaetzlich durchs
  Archiv iteriert werden.
- **Bessere Dedupe-Erkennung:** `curate.py` nutzt eine einfache
  Text-Aehnlichkeits-Heuristik. Fuer praezisere Erkennung liesse sich ein
  Embedding-Vergleich oder ein zusaetzlicher Claude-Batch-Check ergaenzen.
- **Eigene Domain:** ueber eine `CNAME`-Datei in `site/public/` moeglich,
  siehe GitHub-Pages-Doku zu Custom Domains.

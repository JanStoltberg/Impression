#!/usr/bin/env python3
"""
Ingest-Skript: laedt alle RSS-Feeds aus sources.yaml und schreibt die
rohen Artikel-Items als JSON nach data/raw/<datum>.json.

Ein einzelner kaputter Feed darf den gesamten Lauf nicht stoppen -
Fehler werden geloggt, der Rest laeuft weiter.

Aufruf:
    python scripts/ingest.py
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import yaml

ROOT = Path(__file__).resolve().parent.parent
SOURCES_FILE = ROOT / "scripts" / "sources.yaml"
RAW_DIR = ROOT / "data" / "raw"


def load_sources() -> list[dict]:
    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config["sources"]


def parse_entry(entry, source: dict) -> dict:
    published = None
    if getattr(entry, "published_parsed", None):
        published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).isoformat()
    elif getattr(entry, "updated_parsed", None):
        published = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc).isoformat()

    summary = getattr(entry, "summary", "") or ""

    return {
        "title": getattr(entry, "title", "").strip(),
        "url": getattr(entry, "link", "").strip(),
        "source": source["name"],
        "region": source["region"],
        "topic": source.get("topic", "marketing"),
        "published": published,
        "summary": summary.strip(),
    }


def fetch_source(source: dict) -> list[dict]:
    items = []
    try:
        feed = feedparser.parse(source["rss"])
        if feed.bozo and not feed.entries:
            print(
                f"  Warnung: {source['name']} liefert kein lesbares Feed-XML "
                f"({feed.bozo_exception})",
                file=sys.stderr,
            )
            return items
        for entry in feed.entries:
            item = parse_entry(entry, source)
            if item["title"] and item["url"]:
                items.append(item)
    except Exception as exc:
        # Bewusst breit gefangen: ein einzelner defekter Feed soll den
        # kompletten taeglichen Lauf nicht abbrechen.
        print(f"  Fehler bei {source['name']}: {exc}", file=sys.stderr)
    return items


def main() -> None:
    sources = load_sources()
    all_items: list[dict] = []

    for source in sources:
        print(f"Lade {source['name']} ...")
        items = fetch_source(source)
        print(f"  {len(items)} Artikel gefunden")
        all_items.extend(items)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RAW_DIR / f"{today}.json"

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "date": today,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "items": all_items,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"\n{len(all_items)} Artikel gesamt -> {out_path}")


if __name__ == "__main__":
    main()

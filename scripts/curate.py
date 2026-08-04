#!/usr/bin/env python3
"""
Kuratier-Skript: liest die rohen Artikel des Tages, dedupliziert sie,
rankt sie und schreibt das fertige Briefing nach data/briefings/<datum>.json.

Ohne ANTHROPIC_API_KEY laeuft ein regelbasiertes Ranking (Keyword-Score +
Aktualitaet). Mit gesetztem ANTHROPIC_API_KEY nutzt das Skript zusaetzlich
Claude, um pro Artikel einen kurzen Einordnungssatz zu schreiben und die
Relevanz feiner zu gewichten - faellt bei jedem Fehler sauber auf das
regelbasierte Ranking zurueck.

Aufruf:
    python scripts/curate.py [--date YYYY-MM-DD] [--top-per-topic 6]
"""
import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
BRIEFINGS_DIR = ROOT / "data" / "briefings"

# Begriffe, die fuer ein Produktmanagement-Publikum im Werbeumfeld besonders
# relevant sind. Wird fuers regelbasierte Ranking genutzt - gerne an eigene
# Prioritaeten anpassen (z.B. eigene Produktkategorie, Wettbewerber-Namen).
RELEVANCE_KEYWORDS = [
    "programmatic", "adtech", "dsp", "ssp", "header bidding", "cookie",
    "privacy sandbox", "identity", "retail media", "ctv", "measurement",
    "attribution", "kuenstliche intelligenz", " ki ", "openai", "google ads",
    "meta", "amazon ads", "the trade desk", "prebid", "iab", "consent",
    "produkt", "plattform", "api", "targeting",
]


def normalize_title(title: str) -> str:
    t = title.lower()
    t = re.sub(r"[^a-z0-9äöüß ]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def item_id(item: dict) -> str:
    return hashlib.sha1(item["url"].encode("utf-8")).hexdigest()[:12]


def dedupe(items: list[dict]) -> list[dict]:
    """Entfernt Artikel, deren Titel sich stark aehneln (gleiche Meldung,
    von mehreren Outlets aufgegriffen).

    Einfache Heuristik aus Zeichen- und Wort-Aehnlichkeit - faengt die
    meisten Faelle, aber nicht jede freie Umschreibung zwischen Outlets.
    Fuer praezisere Erkennung liesse sich hier z.B. ein Embedding-Vergleich
    oder ein zusaetzlicher Claude-Batch-Check ergaenzen.
    """
    kept: list[dict] = []
    kept_norm: list[str] = []
    for item in items:
        norm = normalize_title(item["title"])
        norm_words = set(norm.split())
        is_dupe = False
        for existing in kept_norm:
            char_sim = SequenceMatcher(None, norm, existing).ratio()
            existing_words = set(existing.split())
            word_overlap = (
                len(norm_words & existing_words) / len(norm_words | existing_words)
                if (norm_words or existing_words)
                else 0.0
            )
            if char_sim > 0.72 or word_overlap > 0.55:
                is_dupe = True
                break
        if not is_dupe:
            kept.append(item)
            kept_norm.append(norm)
    return kept


def keyword_score(item: dict) -> float:
    text = f"{item['title']} {item.get('summary', '')}".lower()
    return float(sum(1 for kw in RELEVANCE_KEYWORDS if kw in text))


def recency_score(item: dict, now: datetime) -> float:
    if not item.get("published"):
        return 0.0
    try:
        published = datetime.fromisoformat(item["published"])
    except ValueError:
        return 0.0
    hours_old = (now - published).total_seconds() / 3600
    return max(0.0, 24 - hours_old) / 24  # 0..1, frischer = hoeher


def rank_rule_based(items: list[dict]) -> list[dict]:
    now = datetime.now(timezone.utc)
    for item in items:
        item["score"] = round(keyword_score(item) * 2 + recency_score(item, now) * 3, 2)
    return sorted(items, key=lambda i: i["score"], reverse=True)


def rank_with_claude(items: list[dict]) -> list[dict]:
    """Optionales Feintuning per Claude API: Editorial-Score + Ein-Satz-
    Einordnung fuer die vielversprechendsten Kandidaten."""
    try:
        import anthropic
    except ImportError:
        print("anthropic-Paket nicht installiert, ueberspringe LLM-Ranking.")
        return rank_rule_based(items)

    ranked = rank_rule_based(items)
    candidates = ranked[:40]  # Kosten begrenzen: nur die Top-Kandidaten bewerten

    payload = [
        {"id": item_id(it), "title": it["title"], "summary": it.get("summary", "")[:300]}
        for it in candidates
    ]

    prompt = (
        "Du bewertest Fachartikel fuer das taegliche Briefing eines "
        "Produktmanagers in der digitalen Werbebranche (Fokus Adtech / "
        "Programmatic). Gib fuer jeden Artikel eine relevance (0-10) und "
        "einen editorial_summary (max. 20 Woerter, Deutsch, eigene "
        "Formulierung, keine Wortuebernahme aus dem Original) zurueck. "
        "Antworte NUR mit einem JSON-Array im Format "
        '[{"id": "...", "relevance": 0, "editorial_summary": "..."}], '
        f"kein Fliesstext:\n\n{json.dumps(payload, ensure_ascii=False)}"
    )

    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in response.content if block.type == "text")
        text = text.strip()
        if text.startswith("```"):
            text = text.strip("`")
            text = text[4:] if text.startswith("json") else text
        scored = {row["id"]: row for row in json.loads(text)}
    except Exception as exc:
        print(f"Claude-Ranking fehlgeschlagen ({exc}), nutze regelbasiertes Ranking.")
        return ranked

    for item in candidates:
        row = scored.get(item_id(item))
        if row:
            item["score"] = float(row.get("relevance", item["score"]))
            item["editorial_summary"] = row.get("editorial_summary", "")

    candidates.sort(key=lambda i: i["score"], reverse=True)
    return candidates + ranked[40:]


def select_top_per_bucket(items: list[dict], top_per_topic: int) -> list[dict]:
    buckets: dict[tuple[str, str], list[dict]] = {}
    for item in items:
        key = (item["region"], item["topic"])
        buckets.setdefault(key, []).append(item)

    selected: list[dict] = []
    for bucket_items in buckets.values():
        selected.extend(bucket_items[:top_per_topic])
    return selected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    parser.add_argument("--top-per-topic", type=int, default=6)
    args = parser.parse_args()

    raw_path = RAW_DIR / f"{args.date}.json"
    if not raw_path.exists():
        raise SystemExit(f"Keine Rohdaten gefunden: {raw_path}. Zuerst ingest.py laufen lassen.")

    with open(raw_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    items = dedupe(raw["items"])
    print(f"{len(raw['items'])} Artikel -> {len(items)} nach Dedupe")

    if os.environ.get("ANTHROPIC_API_KEY"):
        items = rank_with_claude(items)
    else:
        items = rank_rule_based(items)

    top_items = select_top_per_bucket(items, args.top_per_topic)
    for item in top_items:
        item["id"] = item_id(item)

    briefing = {
        "date": args.date,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "items": top_items,
    }

    BRIEFINGS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = BRIEFINGS_DIR / f"{args.date}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(briefing, f, ensure_ascii=False, indent=2)

    print(f"Briefing mit {len(top_items)} Artikeln -> {out_path}")


if __name__ == "__main__":
    main()

import fs from 'node:fs';
import path from 'node:path';

// Astro-Build laeuft mit cwd = site/, daher relativ zum Repo-Root aufloesen.
const DATA_DIR = path.resolve(process.cwd(), '../data/briefings');

export function listBriefingDates() {
  if (!fs.existsSync(DATA_DIR)) return [];
  return fs
    .readdirSync(DATA_DIR)
    .filter((f) => f.endsWith('.json'))
    .map((f) => f.replace('.json', ''))
    .sort()
    .reverse();
}

export function loadBriefing(date) {
  const filePath = path.join(DATA_DIR, `${date}.json`);
  if (!fs.existsSync(filePath)) return null;
  return JSON.parse(fs.readFileSync(filePath, 'utf-8'));
}

export function loadLatestBriefing() {
  const [latest] = listBriefingDates();
  return latest ? loadBriefing(latest) : null;
}

export const REGION_LABELS = {
  dach: 'DACH',
  international: 'International',
};

export const TOPIC_LABELS = {
  adtech: 'Adtech & Programmatic',
  marketing: 'Marketing & Markt',
  markt: 'Markt & M&A',
  kreativ: 'Kreation & Kampagnen',
};

export function groupByRegionAndTopic(items) {
  const groups = {};
  for (const item of items) {
    groups[item.region] ??= {};
    groups[item.region][item.topic] ??= [];
    groups[item.region][item.topic].push(item);
  }
  return groups;
}

const SUMMARY_MAX_LENGTH = 180;

function stripHtml(raw) {
  return raw
    .replace(/<[^>]*>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&quot;/g, '"')
    .replace(/&#0?39;/g, "'")
    .replace(/\s+/g, ' ')
    .trim();
}

function truncate(text, maxLength) {
  if (text.length <= maxLength) return text;
  const cut = text.slice(0, maxLength);
  const lastSpace = cut.lastIndexOf(' ');
  return `${cut.slice(0, lastSpace > 0 ? lastSpace : maxLength)}…`;
}

// Editorial-Zusammenfassung (Claude) hat Vorrang; ohne API-Key faellt das
// auf eine bereinigte, gekuerzte Fassung der rohen Feed-Beschreibung zurueck,
// damit unter jeder Schlagzeile immer eine kurze Einordnung steht.
export function getSummary(item) {
  if (item.editorial_summary) return item.editorial_summary;
  if (!item.summary) return '';
  return truncate(stripHtml(item.summary), SUMMARY_MAX_LENGTH);
}

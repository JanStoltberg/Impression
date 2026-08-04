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

import { chromium } from 'playwright';
import { mkdirSync } from 'node:fs';

const sites = [
  ['election', 'https://yomiuri-election-2026.web.app/'],
  ['gformgen', 'https://gfca-aizu.web.app/'],
  ['human', 'https://human-topology.vercel.app/'],
  ['vr', 'https://unityroom.com/games/stick_catch'],
  ['mindscape', 'https://mindscapeai.streamlit.app/'],
  ['english', 'https://english-as-code-indol.vercel.app/'],
];

mkdirSync('assets/previews', { recursive: true });
const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
let failures = 0;
try {
  for (const [key, url] of sites) {
    const page = await browser.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1, colorScheme: 'light' });
    try {
      const response = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 40000 });
      if (response && response.status() >= 400) throw new Error('HTTP ' + response.status());
      await page.waitForTimeout(key === 'mindscape' ? 18000 : key === 'vr' ? 12000 : 6500);
      await page.screenshot({ path: 'assets/previews/' + key + '.jpg', type: 'jpeg', quality: 78, animations: 'disabled' });
      console.log('Captured ' + key + ' from ' + url + ' (' + await page.title() + ')');
    } catch (error) {
      failures++;
      console.warn('Failed ' + key + ': ' + error.message);
    } finally {
      await page.close();
    }
  }
} finally {
  await browser.close();
}
console.log('Screenshots complete: ' + (sites.length - failures) + '/' + sites.length);
if (failures === sites.length) process.exitCode = 1;

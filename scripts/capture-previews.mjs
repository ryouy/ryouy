import { chromium } from 'playwright';
import { spawn, spawnSync } from 'node:child_process';
import { mkdirSync } from 'node:fs';

const sites = [
  ['election', 'https://yomiuri-election-2026.web.app/'],
  ['gformgen', 'https://gfca-aizu.web.app/'],
  ['human', 'https://human-topology.vercel.app/'],
  ['vr', 'https://unityroom.com/games/stick_catch'],
  ['mindscape', 'https://mindscapeai.streamlit.app/'],
];

mkdirSync('assets/previews', { recursive: true });
const clone = spawnSync('git', ['clone', '--depth', '1', 'https://github.com/ryouy/English_as_Code.git', '/tmp/eac-site'], { stdio: 'inherit' });
let localServer = null;
if (clone.status === 0) {
  localServer = spawn('python3', ['-m', 'http.server', '4399', '--directory', '/tmp/eac-site/ui'], { stdio: 'ignore' });
  sites.push(['english', 'http://127.0.0.1:4399/']);
}

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
  if (localServer) localServer.kill();
}
console.log('Screenshots complete: ' + (sites.length - failures) + '/' + sites.length);
if (failures === sites.length) process.exitCode = 1;

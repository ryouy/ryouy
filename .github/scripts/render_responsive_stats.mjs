// Generates one vertically stacked, static image of Languages + WakaTime.
// Two separate images (this one and the live Spotify widget) can wrap naturally
// on narrow README viewports without custom CSS, which GitHub strips.
import fs from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";

const USER = "ryouy";
const WAKATIME_URL =
  "https://wakatime.com/share/@fbc09dd1-8cde-45b2-87e4-c0b5efee3fa7/46152627-c048-465f-93af-b5c0e8b1c4ef.svg";
const OUTPUT = "assets/stats-column.png";
const token = process.env.GITHUB_TOKEN;
const colors = {
  "Jupyter Notebook": "#da5b0b", HTML: "#e34c26",
  TypeScript: "#3178c6", JavaScript: "#f1e05a", Python: "#3572a5",
  "Objective-C": "#438eff", "C#": "#178600", CSS: "#663399",
  Java: "#b07219", "C++": "#f34b7d", C: "#555555",
  Go: "#00add8", Rust: "#dea584", Shell: "#89e051",
  PHP: "#4f5d95", Vue: "#41b883", Svelte: "#ff3e00",
};
const escapeHtml = (s) => String(s).replace(/[&<>"']/g, c =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

async function githubJson(endpoint) {
  const response = await fetch("https://api.github.com" + endpoint, {
    headers: {
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "ryouy-profile-responsive-stats",
      ...(token ? { Authorization: "Bearer " + token } : {}),
    },
    signal: AbortSignal.timeout(30000),
  });
  if (!response.ok) throw Error("GitHub API returned " + response.status + " for " + endpoint);
  return response.json();
}

async function getTopLanguages() {
  const repos = [];
  for (let page = 1; page <= 10; page++) {
    const batch = await githubJson(
      "/users/" + USER + "/repos?type=owner&per_page=100&page=" + page
    );
    if (!Array.isArray(batch)) throw Error("Unexpected GitHub repos response");
    repos.push(...batch);
    if (batch.length < 100) break;
    if (page === 10) throw Error("Too many repositories; adjust pagination");
  }
  const eligible = repos.filter(r => r.full_name && !r.fork && !r.archived && !r.disabled);
  const bytes = new Map();
  // Bounded parallelism, to avoid hammering the GitHub API.
  for (let start = 0; start < eligible.length; start += 5) {
    const chunk = eligible.slice(start, start + 5);
    const data = await Promise.all(chunk.map(async r =>
      githubJson("/repos/" + r.full_name + "/languages")
    ));
    for (const langMap of data) {
      for (const [name, count] of Object.entries(langMap)) {
        if (Number.isFinite(count) && count > 0) {
          bytes.set(name, (bytes.get(name) || 0) + count);
        }
      }
    }
  }
  const total = [...bytes.values()].reduce((a, b) => a + b, 0);
  if (!total) throw Error("No language bytes returned from GitHub");
  return [...bytes].sort((a,b) => b[1] - a[1]).slice(0, 7)
    .map(([name, count]) => ({
      name, ratio: count / total, color: colors[name] || "#7aa2f7"
    }));
}

function languageCard(languages) {
  const segments = languages.map(l =>
    '<span style="background:' + l.color + ';flex:' + Math.max(l.ratio, 0.001) + '"></span>'
  ).join("");
  const entries = languages.map(l =>
    '<div class="language"><span class="dot" style="background:' + l.color + '"></span>' +
    '<span class="name">' + escapeHtml(l.name) + '</span>' +
    '<span class="percent">' + (100 * l.ratio).toFixed(1) + '%</span></div>'
  ).join("");
  return '<section class="language-card">' +
    '<div class="heading">Most Used Languages</div>' +
    '<div class="bar">' + segments + '</div>' +
    '<div class="language-grid">' + entries + '</div>' +
    '</section>';
}

async function main() {
  const languages = await getTopLanguages();
  const html = '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">' +
    '<style>' +
    '*{box-sizing:border-box}html,body{margin:0;padding:0;background:transparent}' +
    'body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif}' +
    '#column{width:440px;display:flex;flex-direction:column;gap:12px}' +
    '.language-card{background:#1a1b27;border-radius:12px;padding:24px 21px 21px;color:#c0caf5}' +
    '.heading{font-size:20px;font-weight:700;color:#70a5fd;margin-bottom:22px}' +
    '.bar{height:13px;display:flex;overflow:hidden;border-radius:7px;background:#30364c;margin-bottom:24px}' +
    '.bar span{display:block;height:100%}' +
    '.language-grid{display:grid;grid-template-columns:1fr 1fr;column-gap:20px;row-gap:15px}' +
    '.language{display:flex;align-items:center;gap:7px;font-size:12px;min-width:0}' +
    '.dot{width:10px;height:10px;border-radius:50%;flex-shrink:0}' +
    '.name{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}' +
    '.percent{margin-left:auto;color:#9aa5c6;font-size:11px}' +
    '#wakatime{display:block;width:440px;height:auto;object-fit:contain}' +
    '</style></head><body><div id="column">' + languageCard(languages) +
    '<img id="wakatime" alt="WakaTime stats" src="' + WAKATIME_URL + '">' +
    '</div></body></html>';
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({
      viewport: { width: 500, height: 850 },
      deviceScaleFactor: 2,
      reducedMotion: "reduce",
    });
    await page.setContent(html, { waitUntil: "domcontentloaded" });
    await page.waitForFunction(() => {
      const img = document.getElementById("wakatime");
      return img && img.complete && img.naturalWidth > 0 && img.naturalHeight > 0;
    }, { timeout: 50000 });
    await page.waitForTimeout(1700); // Let SVG-internal loading transitions settle.
    await fs.mkdir(path.dirname(OUTPUT), { recursive: true });
    await page.locator("#column").screenshot({
      path: OUTPUT, omitBackground: true, animations: "disabled",
      timeout: 60000,
    });
    console.log("Generated", OUTPUT, "with", languages.map(l => l.name).join(", "));
  } finally {
    await browser.close();
  }
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1; // Never overwrite the last working image on failure.
});

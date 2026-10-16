// Generate a stable, static language card. GitHub README SVG animations
// can flicker, so the card is intentionally exported as a PNG.
import fs from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";

const USER = "ryouy";
const OUTPUT = "assets/languages-card.png";
const token = process.env.GITHUB_TOKEN;
const colors = {
  "Jupyter Notebook": "#da5b0b", HTML: "#e34c26",
  TypeScript: "#3178c6", JavaScript: "#f1e05a", Python: "#3572a5",
  "Objective-C": "#438eff", "C#": "#178600", CSS: "#663399",
  Java: "#b07219", "C++": "#f34b7d", C: "#555555",
  Go: "#00add8", Rust: "#dea584", Shell: "#89e051",
  PHP: "#4f5d95", Vue: "#41b883", Svelte: "#ff3e00"
};
const esc = s => String(s).replace(/[&<>"']/g, c =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

async function githubJson(endpoint) {
  const response = await fetch("https://api.github.com" + endpoint, {
    headers: {
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "ryouy-static-language-card",
      ...(token ? { Authorization: "Bearer " + token } : {})
    },
    signal: AbortSignal.timeout(30000)
  });
  if (!response.ok) throw Error("GitHub API " + response.status + " for " + endpoint);
  return response.json();
}

async function getLanguages() {
  const repos = [];
  for (let page = 1; page <= 10; page++) {
    const part = await githubJson("/users/" + USER +
      "/repos?type=owner&per_page=100&page=" + page);
    if (!Array.isArray(part)) throw Error("Invalid GitHub repository response");
    repos.push(...part);
    if (part.length < 100) break;
    if (page === 10) throw Error("Too many repositories to count safely");
  }
  const relevant = repos.filter(r => r.full_name && !r.fork && !r.archived && !r.disabled);
  const counts = new Map();
  for (let i = 0; i < relevant.length; i += 5) {
    const chunk = await Promise.all(relevant.slice(i, i + 5)
      .map(r => githubJson("/repos/" + r.full_name + "/languages")));
    for (const map of chunk) {
      if (typeof map !== "object" || map === null || Array.isArray(map))
        throw Error("Invalid GitHub language data");
      for (const [name, value] of Object.entries(map)) {
        if (Number.isFinite(value) && value > 0)
          counts.set(name, (counts.get(name) || 0) + value);
      }
    }
  }
  const total = [...counts.values()].reduce((a,b) => a+b, 0);
  if (!total) throw Error("No public language statistics returned");
  return [...counts].sort((a,b) => b[1]-a[1]).slice(0,7)
    .map(([name,bytes]) => ({name,ratio:bytes/total,color:colors[name] || "#7aa2f7"}));
}

async function main() {
  const languages = await getLanguages();
  const segments = languages.map(l =>
    '<span style="background:' + l.color + ';flex:' + Math.max(l.ratio,.001) + '"></span>'
  ).join("");
  const items = languages.map(l =>
    '<div class="language"><span class="dot" style="background:' + l.color + '"></span>' +
    '<span class="name">' + esc(l.name) + '</span>' +
    '<span class="percent">' + (l.ratio * 100).toFixed(1) + '%</span></div>'
  ).join("");
  const html = '<!DOCTYPE html><html><head><meta charset="utf-8"><style>' +
    '*{box-sizing:border-box}html,body{margin:0;background:transparent}' +
    'body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif}' +
    '#card{width:440px;background:#1a1b27;border-radius:12px;padding:24px 21px 21px;color:#c0caf5}' +
    '.heading{font-size:20px;font-weight:700;color:#70a5fd;margin-bottom:22px}' +
    '.bar{height:13px;display:flex;overflow:hidden;border-radius:7px;background:#30364c;margin-bottom:24px}' +
    '.bar span{display:block;height:100%}' +
    '.language-grid{display:grid;grid-template-columns:1fr 1fr;column-gap:20px;row-gap:15px}' +
    '.language{display:flex;align-items:center;gap:7px;font-size:12px;min-width:0}' +
    '.dot{width:10px;height:10px;border-radius:50%;flex-shrink:0}' +
    '.name{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}' +
    '.percent{margin-left:auto;color:#9aa5c6;font-size:11px}' +
    '</style></head><body><section id="card">' +
    '<div class="heading">Most Used Languages</div><div class="bar">' + segments +
    '</div><div class="language-grid">' + items + '</div></section></body></html>';
  const browser = await chromium.launch({headless:true});
  try {
    const page = await browser.newPage({
      viewport:{width:480,height:300},deviceScaleFactor:2,reducedMotion:"reduce"
    });
    await page.setContent(html,{waitUntil:"domcontentloaded"});
    await fs.mkdir(path.dirname(OUTPUT),{recursive:true});
    await page.locator("#card").screenshot({
      path:OUTPUT,omitBackground:true,animations:"disabled",timeout:60000
    });
    console.log("Generated",OUTPUT,"with",languages.map(l=>l.name).join(", "));
  } finally {
    await browser.close();
  }
}
main().catch(e=>{ console.error(e); process.exitCode=1; });

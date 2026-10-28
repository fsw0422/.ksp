// Playwright MCP init-page hook that launch.sh loads inside a Claude Code session.
// Playwright MCP calls it once for every tab. It keeps the session's open tabs in
// tabs.json and reopens them when the browser starts again, so each session gets
// its own tabs while all sessions share one signed-in profile.
// Set PW_SESSION_RESTORE=0 in the server's environment to only record tabs.
const fs = require('fs');
const path = require('path');

const file = path.join(process.env.PW_SESSION_DIR, 'tabs.json');
const contexts = new WeakMap();
const restoredUrls = new WeakMap();
// Parameter name words that can carry sign-in codes or tokens; never write them to disk.
const SECRET_WORDS = new Set([
  'assertion', 'auth', 'code', 'credential', 'credentials', 'jwt', 'key', 'nonce', 'otp',
  'passwd', 'password', 'pwd', 'samlrequest', 'samlresponse', 'secret', 'session', 'sid',
  'sig', 'signature', 'state', 'ticket', 'token',
]);

function isSecretName(name) {
  return name
      .replace(/([a-z0-9])([A-Z])/g, '$1 $2')
      .toLowerCase()
      .split(/[^a-z0-9]+/)
      .some(word => SECRET_WORDS.has(word));
}

// Returns the address to save for a tab, or undefined for blank, error, and non-web pages.
function scrub(url) {
  let parsed;
  try {
    parsed = new URL(url);
  } catch {
    return undefined;
  }
  if (parsed.protocol !== 'https:' && parsed.protocol !== 'http:')
    return undefined;
  parsed.username = '';
  parsed.password = '';
  for (const name of [...parsed.searchParams.keys()]) {
    if (isSecretName(name))
      parsed.searchParams.delete(name);
  }
  const hashParams = new URLSearchParams(parsed.hash.slice(1));
  if ([...hashParams.keys()].some(isSecretName))
    parsed.hash = '';
  return parsed.toString();
}

function readTabs() {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8')).tabs || [];
  } catch {
    return [];
  }
}

function save(context) {
  const state = contexts.get(context);
  // A fresh browser starts on a blank tab; keep the saved list until a real page loads.
  if (!state.touched)
    return;
  clearTimeout(state.timer);
  state.timer = setTimeout(async () => {
    if (state.closing)
      return;
    try {
      const tabs = [];
      for (const page of context.pages()) {
        const url = scrub(page.url()) ?? restoredUrls.get(page);
        if (url)
          tabs.push({ url, title: await page.title().catch(() => '') });
      }
      const temp = `${file}.${process.pid}.tmp`;
      fs.writeFileSync(temp, JSON.stringify({ updatedAt: new Date().toISOString(), tabs }, null, 2) + '\n', { mode: 0o600 });
      fs.renameSync(temp, file);
    } catch {
      // Saving tabs must never break the browser server.
    }
  }, 1000);
}

exports.default = async ({ page }) => {
  const context = page.context();
  const first = !contexts.has(context);
  if (first) {
    const state = { timer: undefined, closing: false, touched: false };
    contexts.set(context, state);
    // Quitting the browser closes every page first; keep the last real tab list.
    context.on('close', () => {
      state.closing = true;
      clearTimeout(state.timer);
    });
  }
  page.on('framenavigated', frame => {
    if (frame !== page.mainFrame())
      return;
    if (scrub(frame.url()))
      contexts.get(context).touched = true;
    save(context);
  });
  page.on('load', () => save(context));
  page.on('close', () => save(context));

  if (!first || process.env.PW_SESSION_RESTORE === '0')
    return;
  // Reopen in background tabs; Playwright MCP keeps the current tab where it is.
  for (const saved of readTabs()) {
    const url = scrub(saved.url);
    if (!url)
      continue;
    try {
      const tab = await context.newPage();
      restoredUrls.set(tab, url);
      tab.goto(url).catch(() => {});
    } catch {
      break;
    }
  }
};

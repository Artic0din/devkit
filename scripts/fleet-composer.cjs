#!/usr/bin/env node
// Check an unsent draft in a fresh Chrome profile against the installed T3 frontend.
const { execFileSync } = require("node:child_process");
const { readFileSync, realpathSync } = require("node:fs");
const { homedir } = require("node:os");
const { join } = require("node:path");
const puppeteer = require("puppeteer-core");

const home = homedir();
const t3 = join(home, ".t3/bin/t3");
const [repo, provider, name, display] = process.argv.slice(2);
const chrome = process.env.FLEET_CHROME || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

function projectRoot(id) {
  const query = [
    "from pathlib import Path",
    "import sqlite3, sys",
    "path = Path.home() / '.t3/userdata/statev2.sqlite'",
    "db = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)",
    "row = db.execute('SELECT workspace_root FROM projection_projects WHERE project_id=? AND deleted_at IS NULL', (sys.argv[1],)).fetchone()",
    "if row is None: raise SystemExit(1)",
    "print(row[0])",
  ].join("\n");
  return realpathSync.native(execFileSync("python3", ["-c", query, id], { encoding: "utf8" }).trim());
}

async function selectSkill(page, origin) {
  const destination = new URL("/new", origin);
  destination.search = new URLSearchParams({ repo, provider, prompt: "Verify" }).toString();
  await page.goto(destination.href, { waitUntil: "domcontentloaded" });
  const editor = await page.waitForSelector('[data-workspace-area="composer"] [contenteditable=true]', { timeout: 15000 });
  await page.click("[data-chat-provider-model-picker]");
  const button = await page.waitForFunction(id => {
    const row = [...document.querySelectorAll("[data-model-picker-provider]")]
      .find(item => item.dataset.modelPickerProvider === id);
    return row?.querySelector("button:not(:disabled)") || false;
  }, { timeout: 6000 }, provider);
  await button.asElement().click();
  const model = await page.waitForSelector('[data-model-picker-content] [role="option"]:not([aria-disabled=true])', { timeout: 6000 });
  await model.click();
  if (await page.$("[data-model-picker-content]")) {
    await page.keyboard.press("Escape");
    await page.waitForSelector("[data-model-picker-content]", { hidden: true, timeout: 3000 });
  }
  await editor.click();
  await page.keyboard.press("End");
  await page.keyboard.type(" /" + name);

  const label = "/skill:" + display;
  const match = await page.waitForFunction(expected => {
    const matches = [...document.querySelectorAll("[data-composer-item-id]")].filter(item =>
      item.checkVisibility() && item.dataset.composerItemId.startsWith("skill:") && item.innerText.split("\n")[0] === expected);
    return matches.length === 1 && matches[0];
  }, { timeout: 10000 }, label);
  const selectedLabel = await match.evaluate(item => item.innerText.split("\n")[0]);
  await match.evaluate(item => item.click());

  const insertedState = await page.waitForFunction(element => {
    const doc = element.editor?.getJSON() ?? element.pmViewDesc?.view?.state?.doc?.toJSON();
    const content = doc?.content?.flatMap(paragraph => paragraph.content ?? []) ?? [];
    const skills = content.filter(node => node.type === "composer-skill").map(node => node.attrs);
    return skills.length ? skills : false;
  }, { timeout: 5000 }, editor);
  const inserted = await insertedState.jsonValue();
  if (inserted.length !== 1 || inserted[0].skillName !== name || inserted[0].skillLabel !== display) {
    throw Error("Draft did not contain the expected qualified skill");
  }
  const persisted = await page.waitForFunction(() => {
    const data = JSON.parse(localStorage.getItem("t3code:composer-drafts:v1") || "{}").state;
    const records = Object.values(data?.draftsByThreadKey ?? {});
    const projects = Object.values(data?.draftThreadsByThreadKey ?? {});
    if (records.length === 1 && projects.length === 1 && records[0].activeProvider) {
      return { provider: records[0].activeProvider, project: projects[0].projectId };
    }
    return false;
  }, { timeout: 5000 });
  const draft = await persisted.jsonValue();
  return { cold: true, selected: name, selectedLabel, inserted: inserted[0].skillName,
    insertedLabel: inserted[0].skillLabel, provider: draft.provider, workspace: projectRoot(draft.project) };
}

async function main() {
  if (![repo, provider, name, display].every(value => typeof value === "string" && value.trim())) {
    throw Error("Expected repository, provider, skill name and qualified display name");
  }
  const origin = new URL(JSON.parse(readFileSync(join(home, ".t3/userdata/server-runtime.json"))).origin);
  if (!["127.0.0.1", "localhost", "[::1]"].includes(origin.hostname)) throw Error("Expected loopback");
  const session = await (await fetch(new URL("/api/auth/session", origin))).json();
  const token = JSON.parse(execFileSync(t3, ["auth", "session", "issue", "--scope", "orchestration:read",
    "--ttl", "3m", "--label", "Fleet composer verification", "--json"]));
  let browser;
  try {
    browser = await puppeteer.launch({ headless: true, executablePath: chrome,
      args: ["--disable-background-networking", "--disable-sync", "--disable-extensions"] });
    const page = await browser.newPage();
    await page.setRequestInterception(true);
    page.on("request", request => {
      const target = new URL(request.url());
      const allowed = target.origin === origin.origin || ["blob:", "data:"].includes(target.protocol);
      void (allowed ? request.continue() : request.abort()).catch(() => {});
    });
    await page.setCookie({ name: session.auth.sessionCookieName, value: token.token, url: origin.origin, httpOnly: true });
    console.log(JSON.stringify(await selectSkill(page, origin)));
  } finally {
    try { await browser?.close(); }
    finally { execFileSync(t3, ["auth", "session", "revoke", token.sessionId], { stdio: "ignore" }); }
  }
}

main().catch(error => {
  // Child process diagnostics can contain credentials or local application data.
  console.error("Composer verification failed (" + error.name + ").");
  process.exitCode = 1;
});

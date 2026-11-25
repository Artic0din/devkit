// Drive both production entry points against an isolated T3-shaped server and draft editor.
import assert from "node:assert/strict";
import { Database } from "bun:sqlite";
import { mkdtemp, mkdir, rm, symlink, writeFile } from "node:fs/promises";
import { realpathSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const home = realpathSync.native(await mkdtemp(join(tmpdir(), "fleet-test-")));
const workspace = join(home, "project");
const data = join(home, ".t3/userdata");
const name = "nested";
const display = "group:nested";
const instance = "custom-instance";
const token = "offline-fixture-token";
const revoked = join(home, "revoked");
const calls = [];
const front = `<!doctype html><title>Fixture</title>
<main data-workspace-area="composer"><div id="editor" contenteditable="true">Verify</div></main>
<button data-chat-provider-model-picker onclick="picker.hidden=false">Models</button>
<section id="picker" data-model-picker-content hidden>
<div data-model-picker-provider="custom-instance"><button onclick="chosen=this.parentElement.dataset.modelPickerProvider;model.hidden=false">Provider</button></div>
<button id="model" role="option" hidden onclick="active=chosen;picker.hidden=true">Model</button></section>
<button id="candidate" data-composer-item-id="skill:custom-instance:nested" hidden>/skill:group:nested</button>
<script>
let nodes=[], chosen=null, active="decoy";
editor.editor={getJSON:()=>({content:[{content:nodes}]})};
editor.oninput=()=>candidate.hidden=!editor.textContent.includes(' /nested');
candidate.onclick=()=>{
  nodes=[{type:'composer-skill',attrs:{skillName:'nested',skillLabel:'group:nested'}}];
  candidate.hidden=true;
  localStorage.setItem('t3code:composer-drafts:v1',JSON.stringify({state:{
    draftsByThreadKey:{draft:{activeProvider:active}},
    draftThreadsByThreadKey:{draft:{projectId:'project'}}}}));
};
</script>`;
const server = Bun.serve({
  hostname: "127.0.0.1", port: 0,
  fetch(req, server) {
    const path = new URL(req.url).pathname;
    if (path === "/api/auth/session") return Response.json({ auth: { sessionCookieName: "test-session" } });
    if (path === "/ws" && req.headers.get("authorization") === "Bearer " + token && server.upgrade(req)) return;
    if (path === "/new" && req.headers.get("cookie")?.includes("test-session=" + token)) {
      return new Response(front, { headers: { "content-type": "text/html" } });
    }
    return new Response("Unavailable", { status: 404 });
  },
  websocket: {
    message(ws, raw) {
      const msg = JSON.parse(String(raw));
      calls.push([msg.tag, msg.payload]);
      const config = { environment: { environmentId: "offline" }, providers: [{ enabled: true, instanceId: instance }] };
      const catalog = { providers: [{ instanceId: instance, status: "ready", auth: { status: "authenticated" }, version: "1",
        workspaceSnapshots: [{ cwd: workspace, skills: [{ name, displayName: display, enabled: true }], slashCommands: [] }] }] };
      const value = msg.tag === "server.getConfig" ? config : catalog;
      ws.send(JSON.stringify({ _tag: "Exit", requestId: msg.id, exit: { _tag: "Success", value } }));
    },
  },
});

try {
  await mkdir(join(workspace, "child"), { recursive: true });
  await symlink(join(workspace, "child"), join(home, "alias"));
  await mkdir(data, { recursive: true });
  await mkdir(join(home, ".t3/bin"), { recursive: true });
  await writeFile(join(data, "server-runtime.json"), JSON.stringify({ origin: server.url.origin }));
  await writeFile(join(home, ".t3/bin/t3"), `#!/bin/sh
case "$3" in
  issue) printf '%s' '{"token":"${token}","sessionId":"fixture"}' ;;
  revoke) echo revoked >> "$HOME/revoked" ;;
  *) exit 1 ;;
esac\n`, { mode: 0o755 });
  const db = new Database(join(data, "statev2.sqlite"));
  db.run("CREATE TABLE projection_projects(project_id TEXT, workspace_root TEXT, deleted_at TEXT)");
  db.run("INSERT INTO projection_projects VALUES ('project', ?, NULL)", [workspace]);
  db.close();

  const adapter = join(import.meta.dir, "fleet-composer.cjs");
  const provider = { versionCommand: ["echo", "1"], catalogCommand: ["echo", '["nested"]'],
    composerCommand: [Bun.which("node"), adapter, "example/project", instance, name, display] };
  const env = { ...process.env, HOME: home, FLEET_CHROME: process.env.FLEET_CHROME || Bun.which("google-chrome")
      || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" };
  const policy = Buffer.from(JSON.stringify({ providers: { [instance]: provider }, workspace: home + "/alias/../" })).toString("base64");
  const task = Bun.spawn([process.execPath, join(import.meta.dir, "fleet-probe.mjs"), policy],
    { env, stdout: "pipe", stderr: "pipe" });
  const snapshot = JSON.parse(await new Response(task.stdout).text());
  assert.equal(await task.exited, 0);
  assert.deepEqual(calls, [["server.getConfig", {}], ["server.refreshProviders",
    { instanceId: instance, cwd: workspace, fresh: true, workspaceSnapshotsOnDemand: true }]]);
  assert.equal(snapshot.t3.environmentId, "offline");
  assert.deepEqual(snapshot.native[instance], [name]);
  assert.deepEqual(snapshot.t3.catalogs[instance].skills, [name]);
  assert.deepEqual(snapshot.composer[instance], { cold: true, selected: name, selectedLabel: "/skill:" + display,
    inserted: name, insertedLabel: display, provider: instance, workspace });
  assert.equal((await Bun.file(revoked).text()).trim(), "revoked\nrevoked");
  console.log("Verified a fresh workspace RPC and an inserted skill in Chrome.");
} finally {
  server.stop(true);
  await rm(home, { recursive: true, force: true });
}

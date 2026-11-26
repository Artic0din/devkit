// Invoked with Bun on the host being measured. Only catalog identifiers leave the host.
import { execFileSync } from "node:child_process";
import { homedir } from "node:os";
import { join } from "node:path";

const policy = JSON.parse(Buffer.from(process.argv.at(-1), "base64").toString());
const home = homedir();
const requested = policy.workspace.replace(/^~(?=\/)/, () => home);
const cwd = execFileSync("realpath", [requested], { encoding: "utf8" }).replace(/\n$/, "");
const env = { ...process.env, PATH: [join(home, ".local/bin"), "/opt/homebrew/bin", process.env.PATH].join(":") };
const t3 = join(home, ".t3/bin/t3");

function run(args, timeout = 20000) {
  const r = Bun.spawnSync(args, { cwd, env, stdin: "ignore", stdout: "pipe", stderr: "pipe", timeout });
  if (r.exitCode !== 0) throw Error("command failed");
  return r.stdout.toString().trim();
}

function names(entries) {
  if (!Array.isArray(entries)) throw Error("no catalog");
  return entries.filter(row => row?.enabled !== false && !row?.errors?.length).map(row => {
    const name = typeof row === "string" ? row : row?.name;
    if (typeof name !== "string" || !name.trim()) throw Error("invalid catalog entry");
    return name;
  }).sort();
}

async function workspaceCatalogs() {
  const address = new URL((await Bun.file(join(home, ".t3/userdata/server-runtime.json")).json()).origin);
  if (!["127.0.0.1", "localhost", "[::1]"].includes(address.hostname)) throw Error("expected loopback");
  const auth = JSON.parse(run([t3, "auth", "session", "issue", "--ttl", "5m", "--scope", "orchestration:read", "--label", "Fleet verification", "--json"]));
  let socket;
  try {
    const url = new URL("/ws?orchestrationProtocol=2", address);
    url.protocol = address.protocol === "https:" ? "wss:" : "ws:";
    socket = new WebSocket(url, { headers: { Authorization: "Bearer " + auth.token } });
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(Error("open timeout")), 5000);
      socket.onopen = () => { clearTimeout(timer); resolve(); };
      socket.onerror = () => { clearTimeout(timer); reject(Error("open failed")); };
    });
    const pending = new Map();
    let sequence = 0;
    socket.onmessage = event => {
      const response = JSON.parse(typeof event.data === "string" ? event.data : Buffer.from(event.data).toString());
      for (const msg of [].concat(response)) {
        if (msg._tag === "Exit") pending.get(String(msg.requestId ?? msg.id))?.(msg.exit);
      }
    };
    function call(tag, payload) {
      const id = String(++sequence);
      return new Promise((resolve, reject) => {
        const timer = setTimeout(() => { pending.delete(id); reject(Error("RPC timeout")); }, 25000);
        pending.set(id, result => {
          clearTimeout(timer);
          pending.delete(id);
          if (result._tag === "Success") resolve(result.value);
          else reject(Error("RPC failed"));
        });
        socket.send(JSON.stringify({ _tag: "Request", id, tag, payload, headers: [] }));
      });
    }
    const config = await call("server.getConfig", {});
    const enabled = config.providers.filter(p => p.enabled).map(p => p.instanceId).sort();
    const catalogs = {};
    for (const id of Object.keys(policy.providers).filter(id => enabled.includes(id))) {
      try {
        const refresh = await call("server.refreshProviders", { instanceId: id, cwd, fresh: true, workspaceSnapshotsOnDemand: true });
        const p = refresh.providers.find(x => x.instanceId === id);
        const w = p.workspaceSnapshots?.find(x => x.cwd === cwd);
        const active = (w?.skills ?? []).filter(skill => skill.enabled);
        const labels = active.map(skill => skill.displayName ?? skill.name);
        const signatures = active.map(skill => JSON.stringify([skill.name, skill.displayName ?? skill.name,
          skill.scope ?? "", skill.userInvocable !== false, skill.userInvocationOnly === true]));
        catalogs[id] = { labels, signatures, status: p.status, auth: p.auth?.status, version: p.version ?? null,
          workspace: !!w, skills: names(w?.skills ?? []), commands: names(w?.slashCommands ?? p.slashCommands ?? []) };
      } catch { catalogs[id] = null; }
    }
    return { environmentId: config.environment?.environmentId, hostname: config.hostname, enabled, catalogs };
  } finally {
    socket?.close();
    run([t3, "auth", "session", "revoke", auth.sessionId]);
  }
}

const snapshot = { workspace: cwd, hostname: run(["hostname"]).split(".")[0], cli: {}, native: {}, composer: {} };

for (const [id, spec] of Object.entries(policy.providers)) {
  try { snapshot.cli[id] = run(spec.versionCommand).split("\n")[0]; } catch { snapshot.cli[id] = null; }
  try { snapshot.native[id] = names(JSON.parse(run(spec.catalogCommand, 45000))); } catch { snapshot.native[id] = null; }
  if (spec.composerCommand) {
    try { snapshot.composer[id] = JSON.parse(run(spec.composerCommand, 60000)); } catch { snapshot.composer[id] = null; }
  }
}
try { snapshot.t3 = await workspaceCatalogs(); } catch { snapshot.t3 = null; }
console.log(JSON.stringify(snapshot));

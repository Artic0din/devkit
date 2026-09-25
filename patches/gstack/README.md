# Local Gstack iOS daemon changes

This patch preserves six local source changes from the installed Gstack runtime without copying its runtime bundle or generated skill aliases.
It targets [garrytan/gstack revision 51932eceef9cf45ad5fbf2b19e15615f96df2872](https://github.com/garrytan/gstack/tree/51932eceef9cf45ad5fbf2b19e15615f96df2872), version `1.68.2.0`.
The adjacent MIT license preserves the upstream notice and applies to the patched Gstack source.

The changes keep the iOS daemon responsive during device keepalive calls, reuse reachable tunnels during reconnects, and allow longer screenshot and accessibility snapshot requests.
They also preserve the local regression coverage for reconnects and tunnel reuse.
Review found that rejected requests could replace or clear the active session heartbeat.
The preserved patch corrects that behavior and adds two regression cases: session tracking changes only after successful acquisition or a successful release of the tracked session.
An older heartbeat response also cannot clear a newer session.
The installed runtime was left unchanged.

## Apply to a separate Gstack checkout

Use a clean checkout at the exact revision above.
Replace `/path/to/agent-scripts` with this repository's location.

```sh
git clone https://github.com/garrytan/gstack.git gstack-local-ios
cd gstack-local-ios
git checkout --detach 51932eceef9cf45ad5fbf2b19e15615f96df2872
git apply --check /path/to/agent-scripts/patches/gstack/ios-daemon-reconnect.patch
git apply /path/to/agent-scripts/patches/gstack/ios-daemon-reconnect.patch
bun test ios-qa/daemon/test/daemon-integration.test.ts ios-qa/daemon/test/tunnel-bootstrap.test.ts
```

Do not apply this patch blindly to a newer upstream revision.
Recheck the six affected files and rerun the tests when rebasing it.
To remove it from an otherwise unchanged checkout, use `git apply -R` with the same patch path.

## Validation

The patch applied cleanly to a fresh checkout at the pinned revision.
The initial six-file delta was byte-identical to the installed local files.
The final patch retains four of those files unchanged and adds the reviewed session correction in `src/index.ts` and its tests in `test/daemon-integration.test.ts`.
Both new regression cases failed against the original local changes and passed with the correction.
The two suites passed with Bun 1.4.2: 53 tests and 149 assertions.
They use local test doubles; a physical iPhone and Xcode device integration were not exercised.
Generated aliases, compiled outputs, installation markers, and the remaining upstream runtime are excluded.

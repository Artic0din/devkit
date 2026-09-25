# Installed third-party skill library

These two skill directories were installed locally but absent from this repository.
The initial import matched the pinned upstream trees below by Git blob hash.
Review adaptations described below make the source work with this repository's activation and validation rules without activating integrations.

| Local skill | Source revision | Imported source files | License |
| --- | --- | ---: | --- |
| `playwright` | [openai/skills](https://github.com/openai/skills/tree/49f948faa9258a0c61caceaf225e179651397431/skills/.curated/playwright) | 9 | Apache 2.0, license and notice included |
| `find-skills` | [vercel-labs/skills](https://github.com/vercel-labs/skills/tree/7407f3893ad4dceab546ac002c3ef806e4000c73/skills/find-skills) | 1 | MIT, upstream notice added |

The initial import contained 10 existing source files and one additional upstream license notice.
Each directory retains its own license; the repository's license does not replace the upstream terms.

## Runtime requirements

These are source snapshots, not bundled runtimes.
Read each skill's setup instructions before use and follow the current host's tool availability and authorization rules.

- `playwright` requires Node.js, its locked CLI installation, and browser installation.
- `find-skills` uses website and source search; it does not execute a discovery CLI.

## Review adaptations

Playwright uses the canonical mirror path, ignored capture output, and an absolute CLI path installed with `npm ci` from its trusted runtime directory.
The runtime manifest and lockfile pin the already-required CLI and its integrity hashes; install scripts are disabled.
A regression check places a fake executable in a project and verifies it is not selected.
Find Skills requires source and license review at a pinned commit and imports through the canonical repository instead of writing directly to a global store.
Both skills are registered in the catalogue.

Keep future updates tied to an upstream revision and recheck the imported files and license notices together.

## Held imports

Four other installed libraries were checked but are not included in this import.
Their local installations are unchanged.

- `codex-doctor` matched [upstream revision e205be9](https://github.com/YizeSun/codex-doctor/tree/e205be9ccecfefa7e9f4f823a842c27ac1b52c27), but its cache validator accepted an unversioned source directory containing a `Build` folder as disposable.
  A non-destructive fixture reproduced the misclassification.
- `parametric-3d-printing` matched [upstream revision fe42159](https://github.com/flowful-ai/cad-skill/tree/fe4215970d39f388ff1afc411fac49a9c5f79756), but review found floor violations in tilted flat-bottom pockets and failure to extract small scan outlines.
  Its 32 existing tests passed without covering those cases.
- `graphify` matched [upstream revision 4c73561](https://github.com/safishamsi/graphify/tree/4c735618f3d56fd622c2049771584621c31ba9ff), but its cached-only and code-only routes skipped required input files, and incremental updates saved their manifest before export could reject the changed graph.
  Publishing it safely needs a separate workflow correction and regression coverage.
- `skill-creator` matched [upstream revision ad30d62](https://github.com/anthropics/claude-plugins-official/tree/ad30d62cd52ad0d0af1beda1eab7f61c601045d0/plugins/skill-creator/skills/skill-creator), but its viewer embeds arbitrary output in an HTML script without escaping script terminators and terminates processes on its selected port without establishing ownership.
  An inert HTML marker and mocked process calls reproduced both behaviors without executing embedded code or terminating any process.

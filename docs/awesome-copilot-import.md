---
summary: Pinned source and scope for the existing Awesome Copilot library.
read_when:
  - Updating the imported Awesome Copilot skills, agents, or instructions.
---

# Awesome Copilot imports

These files were already installed locally and are now tracked with invocation settings preserved.
Source: [GitHub Awesome Copilot](https://github.com/github/awesome-copilot/tree/1f5644080a525d26a2e24f61a7609fb9b261c21a).
Pinned revision: `1f5644080a525d26a2e24f61a7609fb9b261c21a`.
All 202 candidate source files were verified against the Git blob at their corresponding source path before review.
This import includes 187 of them, with the compatibility corrections below; the 15 React 19 and Swift MCP files described under exclusions remain local only.

## Local compatibility corrections

- `agent-skill-stack/scripts/inventory_skills.py` recognizes YAML block scalars with chomping indicators such as `>-`, as used by the imported `doc-and-modernize` description.
  It also discovers directory-linked skills, deduplicates aliases, and stops cycles, matching the managed skill links used here.
  Focused regression checks cover both paths.
- `webapp-testing/assets/package.json` marks the existing helper as CommonJS within this repository's ES module package.
  The helper itself remains unchanged, and a regression check exercises imports and its three exports.
- `ui-screenshots/SKILL.md` captures a missed before-state in a separate detached worktree instead of overwriting staged and unstaged work with path checkout commands.
- The frontend performance investigator enables its documented Chrome DevTools server tool set using the [VS Code MCP tool-list syntax](https://code.visualstudio.com/docs/agent-customization/custom-agents#custom-agent-file-structure).
  The server still needs to be configured and available; no server is installed by this import.
- `generate-custom-instructions-from-codebase` writes migration rules under `.github/instructions/` with an `applyTo` header so Copilot discovers the generated file.

Run `python3 skills/agent-skill-stack/scripts/test_inventory_skills.py` and `node skills/webapp-testing/assets/test-helper.test.cjs` after updating these assets.

## Scope and licenses

- 49 skill directories under `skills/`, containing 171 source files, retain their upstream paths.
- 13 upstream `agents/` files live under `.github/agents/`.
- Three upstream `instructions/` files live under `.github/instructions/`: `devcontainers`, `html-css-style-color-guide`, and `mvvm-toolkit`.
- The upstream [MIT license, GitHub Inc](licenses/awesome-copilot-MIT.txt) is included.
  The separately supplied [anti-ui-slop Apache license](../skills/anti-ui-slop/LICENSE) is preserved verbatim, along with its upstream metadata.
- Twelve local plugin manifests are excluded because all 29 assets they reference are absent from that local plugin tree.
  No incomplete plugin is advertised as installable by this import.

The existing [Repository Label Governance context](../CONTEXT.md) is local project vocabulary, not part of Awesome Copilot or its upstream attribution.

## Excluded React 19 migration suite

Five agents and three skill directories, totaling 12 files, are excluded and remain untouched in the original local checkout.
The excluded agents are `react19-auditor`, `react19-commander`, `react19-dep-surgeon`, `react19-migrator`, and `react19-test-guardian`.
The excluded skills are `react19-concurrent-patterns` (four files), `react19-source-patterns` (two files), and `react19-test-patterns` (one file).
Review confirmed that migration guidance changes argumentless refs from `undefined` to `null`, falsely claims React 19 no longer replays effects in development StrictMode, and recommends matching assertions to observed counts without establishing intended behavior.
The migration pipeline also skips TypeScript files and applies inconsistent test-file exclusions in its completion gate.
These require a dedicated migration-content review before publication; this import does not attempt that rewrite.

## Excluded Swift MCP lifecycle templates

The `swift-mcp-expert` agent, `swift-mcp-server-generator` skill, and `swift-mcp-server` instruction file remain local only.
All three define a `shutdown()` method that the ServiceLifecycle `Service` protocol does not invoke.
The expert example also returns from `run()` immediately after `Server.start()`, which starts its receive loop in a separate task; the other two use a long sleep instead of the server's completion lifecycle.
These three templates require a dedicated SDK lifecycle correction and compile/runtime validation before publication.

## Imported skills

- [acquire-codebase-knowledge](../skills/acquire-codebase-knowledge/SKILL.md)
- [agent-skill-stack](../skills/agent-skill-stack/SKILL.md)
- [anti-ui-slop](../skills/anti-ui-slop/SKILL.md)
- [apple-appstore-reviewer](../skills/apple-appstore-reviewer/SKILL.md)
- [codeql](../skills/codeql/SKILL.md)
- [context-map](../skills/context-map/SKILL.md)
- [conventional-branch](../skills/conventional-branch/SKILL.md)
- [conventional-commit](../skills/conventional-commit/SKILL.md)
- [copilot-cli-quickstart](../skills/copilot-cli-quickstart/SKILL.md)
- [copilot-instructions-blueprint-generator](../skills/copilot-instructions-blueprint-generator/SKILL.md)
- [copilot-pr-autopilot](../skills/copilot-pr-autopilot/SKILL.md)
- [copilot-sdk](../skills/copilot-sdk/SKILL.md)
- [copilot-spaces](../skills/copilot-spaces/SKILL.md)
- [copilot-usage-metrics](../skills/copilot-usage-metrics/SKILL.md)
- [create-readme](../skills/create-readme/SKILL.md)
- [create-specification](../skills/create-specification/SKILL.md)
- [create-tldr-page](../skills/create-tldr-page/SKILL.md)
- [dependabot](../skills/dependabot/SKILL.md)
- [doc-and-modernize](../skills/doc-and-modernize/SKILL.md)
- [docs-sync-audit](../skills/docs-sync-audit/SKILL.md)
- [documentation-writer](../skills/documentation-writer/SKILL.md)
- [folder-structure-blueprint-generator](../skills/folder-structure-blueprint-generator/SKILL.md)
- [generate-custom-instructions-from-codebase](../skills/generate-custom-instructions-from-codebase/SKILL.md)
- [gh-attach](../skills/gh-attach/SKILL.md)
- [git-commit](../skills/git-commit/SKILL.md)
- [git-flow-branch-creator](../skills/git-flow-branch-creator/SKILL.md)
- [github-actions-efficiency](../skills/github-actions-efficiency/SKILL.md)
- [github-actions-hardening](../skills/github-actions-hardening/SKILL.md)
- [github-actions-runtime-upgrade-conventions](../skills/github-actions-runtime-upgrade-conventions/SKILL.md)
- [github-codespaces-efficiency](../skills/github-codespaces-efficiency/SKILL.md)
- [github-copilot-starter](../skills/github-copilot-starter/SKILL.md)
- [github-issues](../skills/github-issues/SKILL.md)
- [github-release](../skills/github-release/SKILL.md)
- [playwright-automation-fill-in-form](../skills/playwright-automation-fill-in-form/SKILL.md)
- [playwright-explore-website](../skills/playwright-explore-website/SKILL.md)
- [playwright-generate-test](../skills/playwright-generate-test/SKILL.md)
- [pr-dashboard](../skills/pr-dashboard/SKILL.md)
- [pr-screenshots](../skills/pr-screenshots/SKILL.md)
- [premium-frontend-ui](../skills/premium-frontend-ui/SKILL.md)
- [repo-standardizer](../skills/repo-standardizer/SKILL.md)
- [suggest-awesome-github-copilot-agents](../skills/suggest-awesome-github-copilot-agents/SKILL.md)
- [suggest-awesome-github-copilot-instructions](../skills/suggest-awesome-github-copilot-instructions/SKILL.md)
- [suggest-awesome-github-copilot-skills](../skills/suggest-awesome-github-copilot-skills/SKILL.md)
- [technology-stack-blueprint-generator](../skills/technology-stack-blueprint-generator/SKILL.md)
- [ui-screenshots](../skills/ui-screenshots/SKILL.md)
- [update-specification](../skills/update-specification/SKILL.md)
- [web-design-reviewer](../skills/web-design-reviewer/SKILL.md)
- [webapp-testing](../skills/webapp-testing/SKILL.md)
- [what-context-needed](../skills/what-context-needed/SKILL.md)

## Validation boundaries

Skill and Copilot Markdown frontmatter, bundled executable syntax, JSON, local reference links, and offline helper behavior are checked during import.
Template links such as a generated project's `LICENSE`, `/spec/`, and sample screenshot URLs describe future output rather than files bundled here.
Publishing these source files does not prove every external integration or product workflow works in this environment.
Use each skill's prerequisites and current tool authorization when invoking it.

Before an update, compare the selected files against a new pinned upstream revision and review the complete diff.
Keep the compatibility checks passing and record any source deviations here.
Do not silently rewrite imported instructions or change automatic invocation while updating provenance.

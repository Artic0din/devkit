# Global instruction entrypoints

Cursor reads `~/.cursor/rules/metisary.mdc`, linked to this repository's `config/cursor.rules.mdc`.
GitHub Copilot CLI reads `~/.copilot/copilot-instructions.md`, linked to the canonical `AGENTS.MD`.
These local integrations do not require copying the rules into a settings field.

For GitHub Copilot on github.com, optional personal instructions can be pasted under Settings → Copilot → Personal instructions:

```text
Read and follow AGENTS.md at the repository root before any work.
Follow the i-have-adhd skill for output shape: lead with the answer, result, or decision needed; number sequential steps.
Explain unfamiliar technical terms and prerequisites in plain language, preserving essential reasoning and requested detail.
Perform authorised work yourself; end with one small user action only when their input is needed.
Never commit secrets. Never commit directly to main. Never mark work complete without validation.
```

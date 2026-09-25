# Local reporting skills

The pull-request walkthrough source was already installed locally but absent from the remote repository.
Publishing it does not read session history or create a report from private data.

`pr-walkthrough` documents its adaptation of Warp's review-orientation concept and retains the Denver Technologies MIT license in its directory.
Its linear renderer is local code and does not use D3.
Publication validation fixed single-step browser checks, separated displayed code from executable network checks, and restricted generated links to HTTP(S).
Browser validation now visits every step, detects JavaScript errors, and accepts consecutive steps with the same title.
The page opens with its review findings visible.
The HTML blocks runtime network connections; links to the pull request are intentional user navigation.
Use a task-owned worktree for reading PR code and retain generated walkthroughs only in the repository's local exclude path.

No real session logs, generated reports, production records or credentials are included.
Run the synthetic suite with `python3 -m pytest skills/pr-walkthrough/tests -q`.
The walkthrough suite requires Playwright and an available Chromium or Chrome installation for browser validation.

The separate local `session-insights` collector remains withheld.
Its synthetic tests do not cover Codex free-form tool calls or formatted command-result failures, so it can omit editing activity and error evidence from its reports.
Its installed original and the partial reviewed corrections remain local; no collector, transcript, cache, or generated report is published here.

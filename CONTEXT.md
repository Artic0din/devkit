# Repository Label Governance

This context defines the shared language for labels across Ryan's GitHub repositories.

## Language

**Canonical label**:
A label in the mandatory core that every in-scope repository must contain with the same name, colour, and description.
_Avoid_: Global label, standard label

**Operational label**:
A canonical label describing work type, workflow state, release impact, or work rank.
_Avoid_: Process label, management label

**Community label**:
A canonical label used to classify contributions and closure outcomes without controlling workflow.
_Avoid_: Default label

**Work-rank label**:
One of `critical`, `high`, `medium`, or `low`, combining impact and urgency to inform the order in which work is handled.
_Avoid_: Severity label, priority label

**Triage-state label**:
One of `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, or `wontfix`, describing an issue's current triage outcome.
These labels do not apply to pull requests.

**Triaged issue**:
An issue labelled `ready-for-agent` or `ready-for-human`.
`triaged` is not itself a label.

**Issue-backed pull request**:
A pull request linked to an issue that was already triaged before implementation began.
Its issue retains the readiness and work-rank labels; the pull request does not duplicate them.

**Standalone pull request**:
A focused pull request that legitimately requires no tracking issue.
It has no triage-state requirement and may carry a work-rank label when useful.

**Semantic alias**:
A non-canonical label with the same meaning as a canonical label whose assignments can be migrated without changing intent.
_Avoid_: Duplicate label

**Repository-specific label**:
An optional label whose meaning is relevant to one repository and does not conflict with a canonical label.
_Avoid_: Custom label, local label

**Approved extension label**:
A repository-specific label explicitly declared in the label manifest because active automation or a durable domain workflow requires it.
_Avoid_: Preserved label, legacy label

**In-scope repository**:
An active, non-fork repository owned by `Artic0din` or the `Plaintext-Lab` organisation, including private repositories and excluding archived repositories.
_Avoid_: All repositories, managed repository

**Label manifest**:
The single declarative source of truth for canonical label names, colours, and descriptions.
_Avoid_: Label list, label config

**Label sync**:
An idempotent operation that brings canonical and approved extension labels into agreement with the label manifest, replaces mapped semantic aliases, and removes undeclared labels.
_Avoid_: Label cleanup, label reset

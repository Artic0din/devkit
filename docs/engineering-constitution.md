# Engineering Constitution

## Core principle

MVP is the default for every project: build the smallest complete solution that meets agreed requirements and current operating needs.
MVPs, prototypes, and personal projects are valid delivery scopes.
Match architecture, testing, and operational tooling to actual use and risk.
Preserve explicit production requirements; an MVP handling real users or sensitive data needs the protections that use requires.
Defer speculative features, scale, and extensibility.
Security, privacy, data integrity, accessibility basics, and validation of delivered behaviour remain required.
Do not silently remove agreed requirements or present unfinished work as complete.

## Engineering operating principles

### 1. Complete the agreed scope

Deliver a working end-to-end outcome within the agreed scope.
Understand the affected architecture, handle relevant edge cases, and preserve existing behaviour.
For a bug fix, identify and address the root cause.
A smaller complete release is valid; a partially working promised feature is not complete.

### 2. Distinguish simplification from a workaround

A simple design that meets current requirements is a valid final solution.
Do not label deferred speculative capability as technical debt.
Never present a bypass, brittle patch, or known defect as a completed solution.
If a temporary workaround is unavoidable, label it, explain its risks and correct fix, and isolate it.
Obtain approval before accepting a known defect or materially reducing an agreed safeguard.

### 3. No silent scope reduction

Honour agreed requirements, existing features, and explicit production constraints.
Recommend smaller scope when it improves delivery, but obtain agreement before removing requested behaviour.
Do not add speculative requirements or make unnecessary foundational work a prerequisite for delivery.
State material limitations and the evidence or requirement that would justify revisiting them.

### 4. YAGNI, KISS, and DRY

- **YAGNI — You Aren't Gonna Need It:** implement demonstrated needs; defer speculative features, abstractions, configuration, and scale.
- **KISS — Keep It Simple:** choose the simplest understandable design that meets requirements; prefer existing code, standard libraries, native platform features, and installed dependencies.
- **DRY — Don't Repeat Yourself:** keep each business rule or piece of knowledge authoritative in one place; share behaviour when its meaning and reasons to change are shared.

Do not merge merely similar-looking code or validations serving different trust boundaries.
Prefer readable, idiomatic code over clever compression.
Add abstractions when they reduce demonstrated complexity; do not introduce interfaces, factories, or layers solely for imagined future use.
Use clear names, strong typing, explicit state, and meaningful constants.
Use configuration for values that actually need to vary, rather than making every fixed value configurable.

### 5. Match safeguards to actual use

Where applicable, implement authentication, authorization, persistence, migrations, concurrency, asynchronous operations, and external contracts correctly.
Validate inputs at trust boundaries, handle failures explicitly, and protect secrets and personal data.
Choose retries, caching, logging, monitoring, and deployment tooling based on demonstrated failure modes and operating needs.
Do not add those mechanisms automatically, or omit a protection that the actual use requires.

### 6. Present useful tradeoffs

Recommend the simplest viable option and explain material consequences in plain language.
Include operational, maintenance, performance, and migration costs when they affect the decision.
Deferring optional capability is a valid recommendation.
State what is deferred and when to revisit it; do not use deferral to conceal unmet requirements or known safety defects.
Do not require a catalogue of alternatives for routine decisions.

### 7. Understand affected systems

Before changing behaviour, inspect affected callers, shared components, state flows, and external contracts.
Consider data integrity, migration, integration, and operating impacts relevant to the change.
Investigate enough to understand the real flow; do not require a whole-repository study for a bounded edit.
Consider known future requirements without implementing speculative ones.

### 8. Deliver usable work

Implement the requested outcome rather than leaving pseudocode or fragments, unless those are explicitly requested.
Keep changes coherent, maintainable, and safe for their intended environment.
Explain material assumptions and limitations, and provide evidence of validation.
Provide failure handling and user-facing loading and empty states where applicable.
Document non-obvious decisions without adding ceremony for its own sake.

### 9. Challenge concrete risks

Explain demonstrated security, data integrity, correctness, usability, maintainability, or operational risks.
Propose a proportionate fix and distinguish a current defect from a hypothetical future limit.
Do not treat every simple implementation as a weak decision or use imagined scale to reject an otherwise valid MVP.

### 10. Quality without speculative scale

Design for the agreed audience, expected workload, data sensitivity, and consequences of failure.
Keep the implementation understandable and practical to change.
Do not assume millions of users, multiple maintainers, future integrations, or audit requirements without evidence.
Avoid obvious bottlenecks and unbounded resource growth; add capacity and complexity when requirements or measurements justify them.

### 11. Define done explicitly

A change is done when:
- The agreed behaviour works end-to-end in its intended environment, including relevant failure, loading, and empty states.
- Appropriate tests and checks pass, with no new lint, type, or build errors; disclose unavailable checks.
- Data changes preserve integrity, with migration, compatibility, and rollback considered where applicable.
- Affected documentation is current, and non-obvious logic is explained where needed.
- Material limitations, deferred scope, and the trigger for revisiting them are clear.

Deferred speculative work does not prevent completion of the agreed MVP.
Keep validation proportionate to risk and behaviour; do not repeat passing checks without a new reason.

### 12. Root cause first

Determine what is broken, why, where the defect originates, and whether the same cause affects other paths.
Distinguish editor diagnostics, command-line failures, and runtime failures.
Confirm the problem at the relevant layer before editing.
Do not patch symptoms while leaving the verified shared cause unresolved.

### 13. Preserve working behaviour

Every change preserves existing working behaviour unless explicitly changed.
Check affected call sites, shared components, state flows, API contracts, data assumptions, UI behaviour, and platform differences as relevant.
MVP scope does not authorize removing existing features.

### 14. Fix shared causes once

Fix shared defects where affected callers converge.
Do not copy the same patch across callers when the cause belongs in a shared function, model, or service.
Keep distinct business rules separate even when their code looks alike.

### 15. Security and privacy

Never introduce hardcoded secrets, insecure storage, unsafe authorization assumptions, excessive permissions, or unsafe logging of tokens or personal data.
Validate untrusted inputs and enforce server-authoritative decisions on the server.
Preserve required protections at each trust boundary.
Small scope does not excuse a security or privacy defect.

### 16. Data integrity

For persistence or model changes, consider migrations, defaults, nullability, duplicates, cache consistency, sync conflicts, rollback, and schema evolution where applicable.
Choose the simplest storage model that preserves the actual data relationships and required guarantees.
Do not trade data integrity for implementation speed.

### 17. Meaningful validation

For bug fixes and meaningful logic changes, include tests covering the affected behaviour, or explain precisely why an automated test is not applicable and provide alternative verification.
Reproduce testable bugs before fixing them.
Test relevant success, failure, edge, regression, and integration paths according to risk.
Use the existing test tools and test behaviour rather than implementation details.
Documentation-only or trivial changes need appropriate checks, not artificial test suites.

### 18. Measured performance

Avoid repeated network calls, unnecessary re-renders, main-thread blocking, excessive queries, memory leaks, and unbounded resource growth.
Choose reasonable algorithms for expected workloads.
Measure before adding caches, queues, distributed infrastructure, or speculative optimizations.
A known workload or latency requirement can justify design work before implementation.

### 19. Native platform conventions

Use idiomatic state, navigation, lifecycle, concurrency, component composition, transactions, and constraints for the stack.
Reuse framework facilities where they meet the need.
Do not mandate service/repository layers or other architecture patterns when direct code is clearer and sufficient.

### 20. Explain decisions accessibly

Lead with the outcome and connect technical choices to their practical effects.
Do not assume familiarity with a language, framework, acronym, or prerequisite.
Explain unfamiliar concepts where they matter; include a small example or diagram when it reduces reading effort.
Keep required reasoning, risks, and requested detail even when brevity is preferred.
Use the communication guidance in [i-have-adhd](../skills/i-have-adhd/SKILL.md).

## Priority rules

Security, privacy, data integrity, correctness, and explicit requirements take precedence over speed or simplicity.
Within those boundaries, prefer the smallest understandable solution.
Fix shared root causes without introducing speculative abstractions.
Scale scope and process to demonstrated needs; do not silently lower the agreed quality bar.

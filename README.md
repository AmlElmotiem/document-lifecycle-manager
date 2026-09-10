# document-lifecycle-manager

A regulated-document workflow engine — draft → review → approval →
release → obsolete — with enforced segregation of duties and a
complete, immutable audit trail. Models the kind of process logic
that a PLM system's document control configuration (e.g. CONTACT, in
a MedTech environment under ISO 13485 Sec. 4.2.4) actually has to
enforce, as a small, fully tested, from-scratch state machine.

## Why this exists

Document control in a regulated MedTech environment isn't just
"upload a file" — every status change has to be traceable, certain
role separations are mandatory (an author cannot approve their own
document), and the rules for *when* a document is even allowed to
move to the next state have to be enforced consistently, not just
followed by convention. This project builds exactly that enforcement
logic as testable code, rather than only describing it conceptually.

## What it does

- **`models.py`** — `Document` (id, title, author, revision, current
  state, reviewers, approver, decisions) and `AuditEntry` (an
  immutable, timestamped record of one state change).
- **`workflow.py`** — the actual state machine, one function per
  transition (`submit_for_review`, `record_review`, `approve`,
  `qm_signoff`, `release`, `obsolete`, `new_revision`). Every function
  either performs the transition and logs it, or raises
  `WorkflowError` with a specific reason — there is no way to skip a
  step or bypass a rule through this module.
- **`document_types.py`** — not every document needs the same rigor: a
  construction drawing requires 2 reviewers plus a separate QM
  signoff before release; an internal note only needs 1 reviewer and
  no QM step. `release()` is blocked until QM signoff is recorded, for
  types that require it.
- **`notifications.py`** — the "digitize a paper process" piece: every
  transition automatically generates the notifications the next
  responsible person would need (a reviewer being assigned, QM being
  asked to sign off, the author being told their document shipped),
  instead of relying on someone to remember to forward a form.
- **`analytics.py`** — using nothing but the audit trail every
  document already keeps, computes how long documents actually spend
  in each state (`time_in_each_state`, `bottleneck_report`) and
  renders that as a Mermaid flowchart (`mermaid_flowchart`) with the
  slowest step highlighted — the "trace a document's path and find
  where it's slow" idea, built from real data instead of drawn by hand.
- **`report.py`** — renders a document's full audit trail as a
  readable compliance-style report.
- **`scripts/demo.py`** — walks one document through a realistic
  scenario, including a rejection and rework loop (not just the
  straight-line happy path), and prints the final audit trail.
- **`scripts/demo_notifications_and_bottlenecks.py`** — runs several
  construction drawings through the full workflow (with QM signoff),
  prints the notifications that went out, then reports which step was
  the slowest across all of them and prints a Mermaid flowchart.

## Enforced rules

- A document can only move to the next state in the defined sequence
  (no skipping straight from DRAFT to RELEASED).
- **Segregation of duties**: the author cannot also be a reviewer or
  the approver of their own document.
- Only the actual author may submit a document for review; only the
  designated approver may approve it.
- A document cannot be approved until *every* named reviewer has
  explicitly signed off — a single rejection immediately sends it
  back to DRAFT for rework.
- Every transition is appended to an immutable history: timestamp,
  previous state, new state, who did it, and an optional comment —
  nothing can be changed or deleted after the fact.
- The minimum number of reviewers, and whether a separate QM signoff
  is required before release, depend on the document's **type** —
  a construction drawing is held to a higher bar than an internal
  note (see `document_types.py`).

## Getting started

```bash
pip install -e ".[dev]"
pytest -v                                        # 36 tests
python scripts/demo.py                            # a full scenario, including a rejection/rework loop
python scripts/demo_notifications_and_bottlenecks.py  # notifications + bottleneck report + Mermaid flowchart
```

## What we found (the honest part)

Running the new demo script for the first time surfaced three real
issues, none of which the (still-passing) unit tests had caught:

1. **Mojibake in the terminal.** A notification subject used an en
   dash (`–`); on this Windows setup it printed as `�`. Fixed by using
   a plain ASCII hyphen instead — a small thing, but it's the kind of
   detail that makes a report look broken even when the logic behind
   it is fine.
2. **The bottleneck report showed "0s" for every single state.** Not a
   logic bug — `format_duration()` rounded anything under a minute to
   the nearest whole second, and the demo's artificial delays
   (tens to low-hundreds of milliseconds) all rounded down to zero.
   The report was technically correct and completely useless at the
   same time. Fixed by adding a millisecond-resolution branch to
   `format_duration()` for sub-second durations.
3. **After fixing #2, "released" showed up as the *slowest* step —
   backwards.** `time_in_each_state()` measured the document's current
   (last) state up to `utcnow()`, which is the right thing to do for a
   document still genuinely stuck somewhere (e.g. still `IN_REVIEW`).
   But `RELEASED` and `OBSOLETE` are resting states, not processing
   steps a document is "waiting" to leave — so that same "measure to
   now" logic just picked up however much wall-clock time had passed
   since the demo happened to call `release()`, which has nothing to
   do with the actual process. Fixed by giving terminal states a
   duration of zero for that trailing, still-open segment instead of
   measuring them against `utcnow()`. After the fix, the report
   correctly points at `IN_REVIEW` as the bottleneck in the demo data
   (which was deliberately seeded with a longer review delay than QM
   signoff delay, specifically to check this).

## Limitations

- In-memory only — no persistence layer (database, file storage);
  a real PLM integration would need one.
- No actual user authentication — "actor" is just a plain string
  passed in by the caller, trusted as-is.
- `new_revision()` does not automatically mark the previous revision
  obsolete; the caller has to do that explicitly (documented in the
  function's docstring) since the new Document object only carries
  the old revision's ID, not a live reference to it.
- Notifications are recorded as data (`Notification` objects on
  `document.notifications_sent`), not actually sent anywhere — no real
  mail server in this environment. The integration point where a real
  system would plug in email/Slack sending is exactly where
  `notifications_for_transition()` is called, in `workflow._log()`.
- Only three document types are defined (`drawing`, `test_report`,
  `internal_note`); adding a new type currently means editing
  `DOCUMENT_TYPES` in code rather than configuring it at runtime.

## Roadmap

- A minimal persistence layer (e.g. SQLite) so documents and their
  history survive between runs
- Actually send notifications somewhere real (e.g. write to a local
  file or hook up SMTP) instead of only recording them as data
- A small CLI or web view for browsing the audit trail and bottleneck
  report interactively

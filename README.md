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
  `release`, `obsolete`, `new_revision`). Every function either
  performs the transition and logs it, or raises `WorkflowError` with
  a specific reason — there is no way to skip a step or bypass a rule
  through this module.
- **`report.py`** — renders a document's full audit trail as a
  readable compliance-style report.
- **`scripts/demo.py`** — walks one document through a realistic
  scenario, including a rejection and rework loop (not just the
  straight-line happy path), and prints the final audit trail.

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

## Getting started

```bash
pip install -e ".[dev]"
pytest -v                # 18 tests
python scripts/demo.py   # a full scenario, including a rejection/rework loop
```

## Limitations

- In-memory only — no persistence layer (database, file storage);
  a real PLM integration would need one.
- No actual user authentication — "actor" is just a plain string
  passed in by the caller, trusted as-is.
- `new_revision()` does not automatically mark the previous revision
  obsolete; the caller has to do that explicitly (documented in the
  function's docstring) since the new Document object only carries
  the old revision's ID, not a live reference to it.
- Single approver and a fixed reviewer list per submission — no
  support for parallel approval chains or conditional routing based
  on document type, which a real PLM system typically needs.

## Roadmap

- A minimal persistence layer (e.g. SQLite) so documents and their
  history survive between runs
- Role-based document-type routing (different document types require
  different reviewer/approver sets)
- A small CLI or web view for browsing the audit trail interactively

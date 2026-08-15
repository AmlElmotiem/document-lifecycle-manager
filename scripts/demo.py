"""Walks one document through a realistic scenario -- including a
rejection and rework loop, not just the straight-line happy path --
and prints the full audit trail at the end.

Run: python scripts/demo.py
"""

from doc_lifecycle import (
    Document,
    approve,
    obsolete,
    release,
    submit_for_review,
    record_review,
)
from doc_lifecycle.report import audit_trail_report


def main() -> None:
    doc = Document(
        doc_id="WI-014",
        title="Work Instruction: Reflow Oven Temperature Verification",
        author="Aml",
    )
    print(f"Created {doc.doc_id} in state {doc.state.value}\n")

    submit_for_review(doc, actor="Aml", reviewers=["Bob", "Chris"], approver="Dana")
    print(f"Submitted for review -> {doc.state.value}")

    record_review(doc, reviewer="Bob", approved=True, comment="Looks correct")
    print("Bob approved")

    record_review(doc, reviewer="Chris", approved=False, comment="Missing tolerance spec in step 4")
    print(f"Chris rejected -> {doc.state.value} (kicked back for rework)\n")

    # Rework: resubmit with the same reviewers/approver
    submit_for_review(doc, actor="Aml", reviewers=["Bob", "Chris"], approver="Dana")
    record_review(doc, reviewer="Bob", approved=True)
    record_review(doc, reviewer="Chris", approved=True, comment="Tolerance spec now included")
    print(f"Resubmitted and both reviewers approved -> {doc.state.value}")

    approve(doc, actor="Dana", comment="Approved for release")
    print(f"Approved -> {doc.state.value}")

    release(doc, actor="Dana")
    print(f"Released -> {doc.state.value}\n")

    print(audit_trail_report(doc))


if __name__ == "__main__":
    main()

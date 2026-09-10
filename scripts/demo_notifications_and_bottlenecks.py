"""Demonstrates the two newer pieces together:

1. Notifications -- the system automatically tells the next
   responsible person it's their turn (the "digitize a paper process"
   idea), instead of someone having to remember to forward a printed
   form.
2. Bottleneck analysis -- using nothing but the audit trail every
   document already keeps, find out which step in the process is
   actually the slow one, and draw it as a flowchart.

Run: python scripts/demo_notifications_and_bottlenecks.py
"""

import random
import time

from doc_lifecycle import Document, approve, qm_signoff, release, record_review, submit_for_review
from doc_lifecycle.analytics import bottleneck_report, format_duration, mermaid_flowchart


def run_one_drawing(doc_id: str, review_delay_s: float, qm_delay_s: float) -> Document:
    """Push one construction drawing through the full workflow, with
    artificial delays standing in for "review sat in someone's inbox
    for a while" -- so the bottleneck report has something real to find."""
    doc = Document(doc_id=doc_id, title=f"Bauteilzeichnung {doc_id}", author="Aml", doc_type="drawing")

    submit_for_review(doc, actor="Aml", reviewers=["Bob", "Chris"], approver="Dana", qm_approver="Erin")
    time.sleep(review_delay_s)
    record_review(doc, reviewer="Bob", approved=True)
    record_review(doc, reviewer="Chris", approved=True)

    approve(doc, actor="Dana")
    time.sleep(qm_delay_s)
    qm_signoff(doc, actor="Erin")

    release(doc, actor="Dana")
    return doc


def main() -> None:
    print("=== Notifications on one document ===\n")
    doc = run_one_drawing("DRW-100", review_delay_s=0.05, qm_delay_s=0.02)
    for note in doc.notifications_sent:
        print(f"  -> {note.recipient}: {note.subject}\n     ({note.reason})")

    print("\n=== Running several drawings through the process ===\n")
    random.seed(1)
    documents = [
        run_one_drawing(f"DRW-{100 + i}", review_delay_s=random.uniform(0.02, 0.15), qm_delay_s=random.uniform(0.01, 0.03))
        for i in range(1, 8)
    ]

    report = bottleneck_report(documents)
    print("Average time per state, across 7 documents:")
    for state, avg in sorted(report.items(), key=lambda kv: -kv[1]):
        print(f"  {state.value:12s} {format_duration(avg)}")

    slowest = max(report, key=lambda s: report[s])
    print(f"\nSlowest step: {slowest.value} (avg {format_duration(report[slowest])})")

    chart = mermaid_flowchart(report)
    print("\nMermaid flowchart (paste into https://mermaid.live to view):\n")
    print(chart)


if __name__ == "__main__":
    main()

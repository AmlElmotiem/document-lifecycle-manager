from doc_lifecycle import Document, DocumentState, approve, release, submit_for_review
from doc_lifecycle import record_review
from doc_lifecycle.report import audit_trail_report


def test_history_records_every_transition_in_order():
    doc = Document(doc_id="SOP-004", title="Equipment Maintenance Log", author="Aml")
    submit_for_review(doc, actor="Aml", reviewers=["Bob"], approver="Dana")
    record_review(doc, reviewer="Bob", approved=True)
    approve(doc, actor="Dana")
    release(doc, actor="Dana")

    transitions = [(e.from_state, e.to_state) for e in doc.history]
    assert transitions == [
        (None, DocumentState.DRAFT),
        (DocumentState.DRAFT, DocumentState.IN_REVIEW),
        (DocumentState.IN_REVIEW, DocumentState.APPROVED),
        (DocumentState.APPROVED, DocumentState.RELEASED),
    ]


def test_history_records_the_correct_actor_per_entry():
    doc = Document(doc_id="SOP-005", title="Waste Disposal Procedure", author="Aml")
    submit_for_review(doc, actor="Aml", reviewers=["Bob"], approver="Dana")
    approve_actor = "Dana"

    record_review(doc, reviewer="Bob", approved=True)
    from doc_lifecycle import approve
    approve(doc, actor=approve_actor)

    actors = [e.actor for e in doc.history]
    assert actors == ["Aml", "Aml", "Dana"]


def test_report_contains_key_facts():
    doc = Document(doc_id="SOP-006", title="Nonconformance Handling", author="Aml")
    submit_for_review(doc, actor="Aml", reviewers=["Bob"], approver="Dana")

    report = audit_trail_report(doc)

    assert "SOP-006" in report
    assert "Nonconformance Handling" in report
    assert "IN_REVIEW" in report
    assert "draft -> in_review" in report

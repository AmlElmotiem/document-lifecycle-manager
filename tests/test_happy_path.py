from doc_lifecycle import (
    Document,
    DocumentState,
    approve,
    obsolete,
    release,
    submit_for_review,
    record_review,
)


def make_doc():
    return Document(doc_id="SOP-001", title="Cleanroom Gowning Procedure", author="Aml")


def test_starts_in_draft():
    doc = make_doc()
    assert doc.state == DocumentState.DRAFT


def test_full_lifecycle_reaches_released():
    doc = make_doc()
    submit_for_review(doc, actor="Aml", reviewers=["Bob", "Chris"], approver="Dana")
    assert doc.state == DocumentState.IN_REVIEW

    record_review(doc, reviewer="Bob", approved=True)
    assert doc.state == DocumentState.IN_REVIEW  # still waiting on Chris

    record_review(doc, reviewer="Chris", approved=True)
    assert doc.state == DocumentState.IN_REVIEW  # reviews done, not yet approved

    approve(doc, actor="Dana")
    assert doc.state == DocumentState.APPROVED

    release(doc, actor="Dana")
    assert doc.state == DocumentState.RELEASED

    obsolete(doc, actor="Dana", comment="Superseded by rev 2")
    assert doc.state == DocumentState.OBSOLETE


def test_rejection_sends_document_back_to_draft():
    doc = make_doc()
    submit_for_review(doc, actor="Aml", reviewers=["Bob", "Chris"], approver="Dana")

    record_review(doc, reviewer="Bob", approved=False, comment="Missing step 3")

    assert doc.state == DocumentState.DRAFT
    assert doc.review_decisions["Bob"] is False

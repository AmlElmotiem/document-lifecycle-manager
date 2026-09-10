from doc_lifecycle import (
    Document,
    approve,
    qm_signoff,
    release,
    record_review,
    submit_for_review,
)


def test_submitting_for_review_notifies_every_reviewer():
    doc = Document(doc_id="N-001", title="Pruefanweisung", author="Aml", doc_type="internal_note")
    submit_for_review(doc, actor="Aml", reviewers=["Bob", "Chris"], approver="Dana")

    recipients = [n.recipient for n in doc.notifications_sent]
    assert "Bob" in recipients
    assert "Chris" in recipients


def test_rejection_notifies_the_author():
    doc = Document(doc_id="N-002", title="Messprotokoll", author="Aml", doc_type="internal_note")
    submit_for_review(doc, actor="Aml", reviewers=["Bob"], approver="Dana")
    doc.notifications_sent.clear()

    record_review(doc, reviewer="Bob", approved=False, comment="fehlt was")

    assert any(n.recipient == "Aml" for n in doc.notifications_sent)


def test_release_notifies_the_author():
    doc = Document(doc_id="N-003", title="Arbeitsanweisung", author="Aml", doc_type="internal_note")
    submit_for_review(doc, actor="Aml", reviewers=["Bob"], approver="Dana")
    record_review(doc, reviewer="Bob", approved=True)
    approve(doc, actor="Dana")
    doc.notifications_sent.clear()

    release(doc, actor="Dana")

    assert any(n.recipient == "Aml" for n in doc.notifications_sent)


def test_approval_of_a_drawing_notifies_the_qm_approver():
    doc = Document(doc_id="N-004", title="Bauteilzeichnung", author="Aml", doc_type="drawing")
    submit_for_review(doc, actor="Aml", reviewers=["Bob", "Chris"], approver="Dana", qm_approver="Erin")
    record_review(doc, reviewer="Bob", approved=True)
    record_review(doc, reviewer="Chris", approved=True)
    doc.notifications_sent.clear()

    approve(doc, actor="Dana")

    assert any(n.recipient == "Erin" for n in doc.notifications_sent)


def test_qm_signoff_notifies_the_approver():
    doc = Document(doc_id="N-005", title="Bauteilzeichnung 2", author="Aml", doc_type="drawing")
    submit_for_review(doc, actor="Aml", reviewers=["Bob", "Chris"], approver="Dana", qm_approver="Erin")
    record_review(doc, reviewer="Bob", approved=True)
    record_review(doc, reviewer="Chris", approved=True)
    approve(doc, actor="Dana")
    doc.notifications_sent.clear()

    qm_signoff(doc, actor="Erin")

    assert any(n.recipient == "Dana" for n in doc.notifications_sent)

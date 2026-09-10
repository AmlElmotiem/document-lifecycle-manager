import pytest

from doc_lifecycle import (
    Document,
    WorkflowError,
    approve,
    qm_signoff,
    release,
    record_review,
    submit_for_review,
)


def test_drawing_requires_two_reviewers():
    doc = Document(doc_id="DRW-001", title="Schafttrichter", author="Aml", doc_type="drawing")
    with pytest.raises(WorkflowError, match="at least 2 reviewer"):
        submit_for_review(doc, actor="Aml", reviewers=["Bob"], approver="Dana", qm_approver="Erin")


def test_internal_note_only_needs_one_reviewer():
    doc = Document(doc_id="NOTE-001", title="Meeting-Notiz", author="Aml", doc_type="internal_note")
    submit_for_review(doc, actor="Aml", reviewers=["Bob"], approver="Dana")  # should not raise


def test_drawing_cannot_be_released_without_qm_signoff():
    doc = Document(doc_id="DRW-002", title="Gehaeusedeckel", author="Aml", doc_type="drawing")
    submit_for_review(doc, actor="Aml", reviewers=["Bob", "Chris"], approver="Dana", qm_approver="Erin")
    record_review(doc, reviewer="Bob", approved=True)
    record_review(doc, reviewer="Chris", approved=True)
    approve(doc, actor="Dana")

    with pytest.raises(WorkflowError, match="requires QM signoff"):
        release(doc, actor="Dana")


def test_drawing_releases_after_qm_signoff():
    doc = Document(doc_id="DRW-003", title="Gewindeeinsatz", author="Aml", doc_type="drawing")
    submit_for_review(doc, actor="Aml", reviewers=["Bob", "Chris"], approver="Dana", qm_approver="Erin")
    record_review(doc, reviewer="Bob", approved=True)
    record_review(doc, reviewer="Chris", approved=True)
    approve(doc, actor="Dana")
    qm_signoff(doc, actor="Erin")

    release(doc, actor="Dana")  # should not raise
    assert doc.qm_signoff_done is True


def test_qm_approver_cannot_be_the_author():
    doc = Document(doc_id="DRW-004", title="Distanzhuelse", author="Aml", doc_type="drawing")
    with pytest.raises(WorkflowError, match="cannot also be the QM approver"):
        submit_for_review(doc, actor="Aml", reviewers=["Bob", "Chris"], approver="Dana", qm_approver="Aml")


def test_only_the_designated_qm_approver_may_sign_off():
    doc = Document(doc_id="DRW-005", title="Fixierschraube", author="Aml", doc_type="drawing")
    submit_for_review(doc, actor="Aml", reviewers=["Bob", "Chris"], approver="Dana", qm_approver="Erin")
    record_review(doc, reviewer="Bob", approved=True)
    record_review(doc, reviewer="Chris", approved=True)
    approve(doc, actor="Dana")

    with pytest.raises(WorkflowError, match="Only the designated QM approver"):
        qm_signoff(doc, actor="Bob")


def test_internal_note_cannot_use_qm_signoff():
    doc = Document(doc_id="NOTE-002", title="Kurznotiz", author="Aml", doc_type="internal_note")
    submit_for_review(doc, actor="Aml", reviewers=["Bob"], approver="Dana")
    record_review(doc, reviewer="Bob", approved=True)
    approve(doc, actor="Dana")

    with pytest.raises(WorkflowError, match="does not require a separate QM signoff"):
        qm_signoff(doc, actor="Dana")

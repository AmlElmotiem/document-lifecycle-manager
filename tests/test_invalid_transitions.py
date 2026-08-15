import pytest

from doc_lifecycle import (
    Document,
    WorkflowError,
    approve,
    obsolete,
    release,
    record_review,
    submit_for_review,
)


def make_doc():
    return Document(doc_id="SOP-003", title="Calibration Procedure", author="Aml")


def test_cannot_release_a_draft():
    doc = make_doc()
    with pytest.raises(WorkflowError, match="must be APPROVED"):
        release(doc, actor="Aml")


def test_cannot_approve_a_draft():
    doc = make_doc()
    with pytest.raises(WorkflowError, match="must be IN_REVIEW"):
        approve(doc, actor="Dana")


def test_cannot_obsolete_a_draft():
    doc = make_doc()
    with pytest.raises(WorkflowError, match="must be RELEASED"):
        obsolete(doc, actor="Aml")


def test_cannot_submit_a_document_already_in_review():
    doc = make_doc()
    submit_for_review(doc, actor="Aml", reviewers=["Bob"], approver="Dana")
    with pytest.raises(WorkflowError, match="must be in DRAFT"):
        submit_for_review(doc, actor="Aml", reviewers=["Bob"], approver="Dana")


def test_cannot_approve_before_every_reviewer_has_cleared_it():
    doc = make_doc()
    submit_for_review(doc, actor="Aml", reviewers=["Bob", "Chris"], approver="Dana")
    record_review(doc, reviewer="Bob", approved=True)  # Chris hasn't reviewed yet

    with pytest.raises(WorkflowError, match="still waiting on reviewer"):
        approve(doc, actor="Dana")


def test_unrecognized_reviewer_cannot_record_a_review():
    doc = make_doc()
    submit_for_review(doc, actor="Aml", reviewers=["Bob"], approver="Dana")
    with pytest.raises(WorkflowError, match="not a designated reviewer"):
        record_review(doc, reviewer="Eve", approved=True)

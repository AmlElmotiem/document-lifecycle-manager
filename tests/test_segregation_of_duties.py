import pytest

from doc_lifecycle import Document, WorkflowError, approve, submit_for_review


def make_doc():
    return Document(doc_id="SOP-002", title="Incoming Inspection", author="Aml")


def test_author_cannot_be_a_reviewer():
    doc = make_doc()
    with pytest.raises(WorkflowError, match="cannot also be a reviewer"):
        submit_for_review(doc, actor="Aml", reviewers=["Aml", "Bob"], approver="Dana")


def test_author_cannot_be_the_approver():
    doc = make_doc()
    with pytest.raises(WorkflowError, match="cannot also be the approver"):
        submit_for_review(doc, actor="Aml", reviewers=["Bob"], approver="Aml")


def test_only_author_may_submit():
    doc = make_doc()
    with pytest.raises(WorkflowError, match="Only the author"):
        submit_for_review(doc, actor="Bob", reviewers=["Chris"], approver="Dana")


def test_only_the_designated_approver_may_approve():
    doc = make_doc()
    submit_for_review(doc, actor="Aml", reviewers=["Bob"], approver="Dana")
    from doc_lifecycle import record_review

    record_review(doc, reviewer="Bob", approved=True)

    with pytest.raises(WorkflowError, match="Only the designated approver"):
        approve(doc, actor="Bob")  # Bob was a reviewer, not the approver

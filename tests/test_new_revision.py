import pytest

from doc_lifecycle import (
    Document,
    DocumentState,
    WorkflowError,
    approve,
    new_revision,
    release,
    record_review,
    submit_for_review,
)


def released_doc():
    doc = Document(doc_id="SOP-007", title="Pipette Calibration", author="Aml")
    submit_for_review(doc, actor="Aml", reviewers=["Bob"], approver="Dana")
    record_review(doc, reviewer="Bob", approved=True)
    approve(doc, actor="Dana")
    release(doc, actor="Dana")
    return doc


def test_new_revision_starts_fresh_in_draft():
    doc = released_doc()
    rev2 = new_revision(doc, actor="Aml")

    assert rev2.state == DocumentState.DRAFT
    assert rev2.revision == 2
    assert rev2.previous_revision_id == "SOP-007 rev1"
    assert doc.state == DocumentState.RELEASED  # the old revision is untouched


def test_cannot_start_a_new_revision_from_a_draft():
    doc = Document(doc_id="SOP-008", title="Sample Retention Policy", author="Aml")
    with pytest.raises(WorkflowError, match="must be RELEASED"):
        new_revision(doc, actor="Aml")

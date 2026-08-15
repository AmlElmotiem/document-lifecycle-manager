"""The document lifecycle state machine and its enforcement rules.

Models the kind of process a regulated-document PLM configuration (e.g.
ISO 13485 Sec. 4.2.4, "control of documents") has to enforce:

    DRAFT --submit--> IN_REVIEW --approve--> APPROVED --release--> RELEASED --obsolete--> OBSOLETE
       ^                  |
       +---- reject -------+

Every transition is a plain function that either mutates the document
and appends an AuditEntry, or raises WorkflowError with a specific
reason -- there is no way to silently skip a step or bypass a rule
through this module.
"""

from __future__ import annotations

from .models import AuditEntry, Document, DocumentState, utcnow


class WorkflowError(Exception):
    """Raised whenever a requested transition violates a workflow rule."""


def _log(document: Document, from_state: DocumentState, to_state: DocumentState, actor: str, comment: str = "") -> None:
    document.state = to_state
    document.history.append(
        AuditEntry(timestamp=utcnow(), from_state=from_state, to_state=to_state, actor=actor, comment=comment)
    )


def submit_for_review(document: Document, actor: str, reviewers: list[str], approver: str) -> None:
    """DRAFT -> IN_REVIEW. Only the author may submit; segregation of
    duties requires the reviewers and the approver to be different
    people from the author (nobody reviews or approves their own
    document)."""
    if document.state != DocumentState.DRAFT:
        raise WorkflowError(f"Cannot submit for review from state {document.state.value!r}; must be in DRAFT.")
    if actor != document.author:
        raise WorkflowError(f"Only the author ({document.author!r}) may submit this document for review, not {actor!r}.")
    if not reviewers:
        raise WorkflowError("At least one reviewer is required.")
    if document.author in reviewers:
        raise WorkflowError("The author cannot also be a reviewer (segregation of duties).")
    if approver == document.author:
        raise WorkflowError("The author cannot also be the approver (segregation of duties).")

    document.reviewers = list(reviewers)
    document.approver = approver
    document.review_decisions = {}
    _log(document, DocumentState.DRAFT, DocumentState.IN_REVIEW, actor,
         f"Submitted for review. Reviewers: {reviewers}. Approver: {approver}.")


def record_review(document: Document, reviewer: str, approved: bool, comment: str = "") -> None:
    """Record one reviewer's decision. A single rejection immediately
    sends the document back to DRAFT -- in this model, review is not
    a majority vote; every named reviewer must clear it."""
    if document.state != DocumentState.IN_REVIEW:
        raise WorkflowError(f"Cannot record a review from state {document.state.value!r}; must be IN_REVIEW.")
    if reviewer not in document.reviewers:
        raise WorkflowError(f"{reviewer!r} is not a designated reviewer for this document.")

    document.review_decisions[reviewer] = approved

    if not approved:
        _log(document, DocumentState.IN_REVIEW, DocumentState.DRAFT, reviewer,
             f"Rejected: {comment}" if comment else "Rejected, sent back to draft.")


def approve(document: Document, actor: str, comment: str = "") -> None:
    """IN_REVIEW -> APPROVED. Only the designated approver may approve,
    and only once every reviewer has cleared the document."""
    if document.state != DocumentState.IN_REVIEW:
        raise WorkflowError(f"Cannot approve from state {document.state.value!r}; must be IN_REVIEW.")
    if actor != document.approver:
        raise WorkflowError(f"Only the designated approver ({document.approver!r}) may approve, not {actor!r}.")
    if not document.all_reviewers_approved:
        pending = [r for r in document.reviewers if document.review_decisions.get(r) is not True]
        raise WorkflowError(f"Cannot approve: still waiting on reviewer(s) {pending}.")

    _log(document, DocumentState.IN_REVIEW, DocumentState.APPROVED, actor, comment)


def release(document: Document, actor: str, comment: str = "") -> None:
    """APPROVED -> RELEASED."""
    if document.state != DocumentState.APPROVED:
        raise WorkflowError(f"Cannot release from state {document.state.value!r}; must be APPROVED.")
    _log(document, DocumentState.APPROVED, DocumentState.RELEASED, actor, comment)


def obsolete(document: Document, actor: str, comment: str = "") -> None:
    """RELEASED -> OBSOLETE."""
    if document.state != DocumentState.RELEASED:
        raise WorkflowError(f"Cannot obsolete from state {document.state.value!r}; must be RELEASED.")
    _log(document, DocumentState.RELEASED, DocumentState.OBSOLETE, actor, comment)


def new_revision(document: Document, actor: str) -> Document:
    """Create the next revision of a RELEASED document, starting fresh
    in DRAFT and linked to the previous one via PREVIOUS_REVISION_ID.
    The previous revision's own state is left untouched here -- this
    function only creates the new one; call OBSOLETE() on the old
    Document object separately once the new revision is released, if
    you want only one revision ever marked RELEASED at a time. (Not
    done automatically: this function only has the old revision's ID
    string, not a live reference back to that Document object.)"""
    if document.state != DocumentState.RELEASED:
        raise WorkflowError(f"Cannot create a new revision from state {document.state.value!r}; must be RELEASED.")

    return Document(
        doc_id=document.doc_id,
        title=document.title,
        author=actor,
        revision=document.revision + 1,
        previous_revision_id=f"{document.doc_id} rev{document.revision}",
    )

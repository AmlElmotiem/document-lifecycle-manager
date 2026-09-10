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

from .document_types import rules_for
from .models import AuditEntry, Document, DocumentState, utcnow
from .notifications import Notification, notifications_for_transition


class WorkflowError(Exception):
    """Raised whenever a requested transition violates a workflow rule."""


def _log(document: Document, from_state: DocumentState, to_state: DocumentState, actor: str, comment: str = "") -> None:
    """Perform the transition, log it, AND generate whatever
    notifications that transition implies -- the "digitized paper
    process" piece: nobody has to remember to tell the next person,
    the system does it as part of the transition itself."""
    document.state = to_state
    document.history.append(
        AuditEntry(timestamp=utcnow(), from_state=from_state, to_state=to_state, actor=actor, comment=comment)
    )
    document.notifications_sent.extend(notifications_for_transition(document, from_state, to_state))


def submit_for_review(
    document: Document,
    actor: str,
    reviewers: list[str],
    approver: str,
    qm_approver: str | None = None,
) -> None:
    """DRAFT -> IN_REVIEW. Only the author may submit; segregation of
    duties requires the reviewers, the approver, and (if applicable)
    the QM approver to all be different people from the author (nobody
    reviews or approves their own document).

    How many reviewers are required, and whether a separate QM signoff
    is mandatory before release, depends on the document's TYPE (see
    document_types.py) -- a construction drawing is held to a higher
    bar than an internal note."""
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

    rules = rules_for(document.doc_type)
    if len(reviewers) < rules.min_reviewers:
        raise WorkflowError(
            f"{rules.name} requires at least {rules.min_reviewers} reviewer(s), got {len(reviewers)}."
        )
    if rules.requires_qm_signoff:
        if qm_approver is None:
            raise WorkflowError(f"{rules.name} requires a QM approver to be designated.")
        if qm_approver == document.author:
            raise WorkflowError("The author cannot also be the QM approver (segregation of duties).")

    document.reviewers = list(reviewers)
    document.approver = approver
    document.qm_approver = qm_approver
    document.qm_signoff_done = False
    document.review_decisions = {}
    _log(document, DocumentState.DRAFT, DocumentState.IN_REVIEW, actor,
         f"Submitted for review. Reviewers: {reviewers}. Approver: {approver}."
         + (f" QM approver: {qm_approver}." if qm_approver else ""))


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


def qm_signoff(document: Document, actor: str, comment: str = "") -> None:
    """A separate quality-management signoff, required for document
    types where RULES.requires_qm_signoff is True (e.g. construction
    drawings) before RELEASE() will let the document through. Does not
    change the document's state itself -- it clears a precondition
    that RELEASE() checks."""
    rules = rules_for(document.doc_type)
    if not rules.requires_qm_signoff:
        raise WorkflowError(f"{rules.name} does not require a separate QM signoff.")
    if document.state != DocumentState.APPROVED:
        raise WorkflowError(f"Cannot record QM signoff from state {document.state.value!r}; must be APPROVED.")
    if actor != document.qm_approver:
        raise WorkflowError(f"Only the designated QM approver ({document.qm_approver!r}) may sign off, not {actor!r}.")

    document.qm_signoff_done = True
    document.history.append(
        AuditEntry(
            timestamp=utcnow(),
            from_state=document.state,
            to_state=document.state,
            actor=actor,
            comment=f"QM signoff: {comment}" if comment else "QM signoff recorded.",
        )
    )
    document.notifications_sent.append(
        Notification(
            recipient=document.approver or document.author,
            subject=f"QM-Freigabe erteilt: {document.doc_id}",
            reason="QM hat freigegeben -- das Dokument kann jetzt veroeffentlicht werden.",
        )
    )


def release(document: Document, actor: str, comment: str = "") -> None:
    """APPROVED -> RELEASED. Blocked until QM signoff is recorded, for
    document types that require one."""
    if document.state != DocumentState.APPROVED:
        raise WorkflowError(f"Cannot release from state {document.state.value!r}; must be APPROVED.")

    rules = rules_for(document.doc_type)
    if rules.requires_qm_signoff and not document.qm_signoff_done:
        raise WorkflowError(f"{rules.name} requires QM signoff before it can be released.")

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

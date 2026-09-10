"""Notifications: who needs to be told when a document changes state,
and why.

Models the "digitize a paper process" idea directly: instead of a
printed release form being walked from desk to desk, the system
itself tells the next responsible person it's their turn. Implemented
as a list of Notification records rather than actually sending email
(no real mail server in this environment) -- the same information a
real system would hand off to its email/Slack integration at this
exact point.
"""

from __future__ import annotations

from dataclasses import dataclass

from .document_types import rules_for
from .models import Document, DocumentState


@dataclass
class Notification:
    recipient: str
    subject: str
    reason: str


def notifications_for_transition(
    document: Document, from_state: DocumentState | None, to_state: DocumentState
) -> list[Notification]:
    """Given a document that just transitioned FROM_STATE -> TO_STATE,
    return the notifications that should go out to whoever needs to
    act next."""
    notes: list[Notification] = []

    if to_state == DocumentState.IN_REVIEW:
        for reviewer in document.reviewers:
            notes.append(Notification(
                recipient=reviewer,
                subject=f"Review angefragt: {document.doc_id} – {document.title}",
                reason="Sie wurden als Pruefer/in eingetragen.",
            ))

    elif to_state == DocumentState.DRAFT and from_state == DocumentState.IN_REVIEW:
        notes.append(Notification(
            recipient=document.author,
            subject=f"Ueberarbeitung noetig: {document.doc_id}",
            reason="Das Dokument wurde abgelehnt und zurueck in den Entwurf geschickt.",
        ))

    elif to_state == DocumentState.APPROVED:
        rules = rules_for(document.doc_type)
        if rules.requires_qm_signoff and document.qm_approver:
            notes.append(Notification(
                recipient=document.qm_approver,
                subject=f"QM-Freigabe angefragt: {document.doc_id}",
                reason="Das Dokument wartet auf die QM-Freigabe vor der Veroeffentlichung.",
            ))

    elif to_state == DocumentState.RELEASED:
        notes.append(Notification(
            recipient=document.author,
            subject=f"Veroeffentlicht: {document.doc_id}",
            reason="Ihr Dokument wurde freigegeben und veroeffentlicht.",
        ))

    elif to_state == DocumentState.OBSOLETE:
        notes.append(Notification(
            recipient=document.author,
            subject=f"Veraltet gesetzt: {document.doc_id}",
            reason="Ihr Dokument wurde als veraltet markiert.",
        ))

    return notes

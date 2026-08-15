"""Data model for a controlled document and its audit trail.

The state machine and its rules live in workflow.py -- this module only
defines the shapes of the data, deliberately kept dumb (no validation
logic here) so there is exactly one place (workflow.py) that decides
whether a transition is allowed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class DocumentState(Enum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    RELEASED = "released"
    OBSOLETE = "obsolete"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class AuditEntry:
    """One immutable, timestamped record of what happened to a document."""

    timestamp: datetime
    from_state: DocumentState | None
    to_state: DocumentState
    actor: str
    comment: str = ""


@dataclass
class Document:
    doc_id: str
    title: str
    author: str
    revision: int = 1
    previous_revision_id: str | None = None

    state: DocumentState = DocumentState.DRAFT
    reviewers: list[str] = field(default_factory=list)
    approver: str | None = None
    review_decisions: dict[str, bool] = field(default_factory=dict)

    history: list[AuditEntry] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.history.append(
            AuditEntry(
                timestamp=utcnow(),
                from_state=None,
                to_state=self.state,
                actor=self.author,
                comment="Document created",
            )
        )

    @property
    def all_reviewers_approved(self) -> bool:
        if not self.reviewers:
            return False
        return all(self.review_decisions.get(r) is True for r in self.reviewers)

    @property
    def any_reviewer_rejected(self) -> bool:
        return any(self.review_decisions.get(r) is False for r in self.reviewers)

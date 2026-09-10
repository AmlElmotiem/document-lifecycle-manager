"""Per-document-type workflow rules.

Not every controlled document needs the same rigor: an internal note
and a construction drawing that ends up on a production floor clearly
don't carry the same risk if something is wrong. Modeling that
difference explicitly -- rather than applying one generic workflow to
everything -- is exactly the kind of "which workflow for which
document type" decision a real PLM document-control configuration has
to make.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentTypeRules:
    name: str
    min_reviewers: int
    requires_qm_signoff: bool


DOCUMENT_TYPES: dict[str, DocumentTypeRules] = {
    "drawing": DocumentTypeRules(
        name="Konstruktionszeichnung", min_reviewers=2, requires_qm_signoff=True
    ),
    "test_report": DocumentTypeRules(
        name="Pruefprotokoll", min_reviewers=1, requires_qm_signoff=True
    ),
    "internal_note": DocumentTypeRules(
        name="Interne Notiz", min_reviewers=1, requires_qm_signoff=False
    ),
}


def rules_for(doc_type: str) -> DocumentTypeRules:
    if doc_type not in DOCUMENT_TYPES:
        valid = ", ".join(sorted(DOCUMENT_TYPES))
        raise KeyError(f"Unknown document type {doc_type!r}. Valid types: {valid}.")
    return DOCUMENT_TYPES[doc_type]

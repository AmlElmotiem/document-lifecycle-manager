"""Renders a Document's audit trail as a readable compliance-style report."""

from __future__ import annotations

from .models import Document


def audit_trail_report(document: Document) -> str:
    lines = [
        f"Document: {document.doc_id}  (rev {document.revision})",
        f"Title:    {document.title}",
        f"Author:   {document.author}",
        f"Current state: {document.state.value.upper()}",
        "",
        "Audit trail:",
    ]
    for entry in document.history:
        from_label = entry.from_state.value if entry.from_state is not None else "-"
        ts = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
        line = f"  [{ts}] {from_label} -> {entry.to_state.value}  (by {entry.actor})"
        if entry.comment:
            line += f" -- {entry.comment}"
        lines.append(line)

    return "\n".join(lines)

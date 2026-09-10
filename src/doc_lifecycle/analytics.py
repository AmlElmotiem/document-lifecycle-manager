"""Trace how long documents actually spend in each workflow state, and
turn that into a bottleneck report and a flowchart -- the "follow a
document's path and find out where it's slow" idea, using the audit
trail that's already being recorded for every document rather than
requiring anything extra to be logged separately.
"""

from __future__ import annotations

from datetime import timedelta

from .models import Document, DocumentState, utcnow


def time_in_each_state(document: Document) -> dict[DocumentState, timedelta]:
    """From one document's audit trail, compute how long it has spent
    (so far) in each state it has passed through. A document that
    visited a state more than once (e.g. DRAFT after a rejection) has
    those durations summed together."""
    durations: dict[DocumentState, timedelta] = {}
    entries = document.history
    for i, entry in enumerate(entries):
        state = entry.to_state
        start = entry.timestamp
        end = entries[i + 1].timestamp if i + 1 < len(entries) else utcnow()
        durations[state] = durations.get(state, timedelta()) + (end - start)
    return durations


def bottleneck_report(documents: list[Document]) -> dict[DocumentState, timedelta]:
    """Average time spent per state, across many documents -- flags
    which step in the real process is the slow one, not just how slow
    one particular document happened to be."""
    totals: dict[DocumentState, list[timedelta]] = {}
    for document in documents:
        for state, duration in time_in_each_state(document).items():
            totals.setdefault(state, []).append(duration)

    return {
        state: sum(durations, timedelta()) / len(durations)
        for state, durations in totals.items()
    }


def format_duration(duration: timedelta) -> str:
    total_seconds = duration.total_seconds()
    if total_seconds < 60:
        return f"{total_seconds:.0f}s"
    if total_seconds < 3600:
        return f"{total_seconds / 60:.1f}min"
    if total_seconds < 86400:
        return f"{total_seconds / 3600:.1f}h"
    return f"{total_seconds / 86400:.1f}d"


def mermaid_flowchart(bottlenecks: dict[DocumentState, timedelta]) -> str:
    """A Mermaid flowchart of the document lifecycle, each state
    labeled with the average time documents spend there -- the
    "draw the workflow, mark where it's slow" deliverable, generated
    from real data instead of drawn by hand."""
    def label(state: DocumentState) -> str:
        avg = bottlenecks.get(state)
        return f"{state.value}<br/>&#248; {format_duration(avg)}" if avg is not None else state.value

    lines = ["flowchart LR"]
    lines.append(f'    DRAFT["{label(DocumentState.DRAFT)}"]')
    lines.append(f'    IN_REVIEW["{label(DocumentState.IN_REVIEW)}"]')
    lines.append(f'    APPROVED["{label(DocumentState.APPROVED)}"]')
    lines.append(f'    RELEASED["{label(DocumentState.RELEASED)}"]')
    lines.append(f'    OBSOLETE["{label(DocumentState.OBSOLETE)}"]')
    lines.append("    DRAFT --> IN_REVIEW")
    lines.append("    IN_REVIEW -- rejected --> DRAFT")
    lines.append("    IN_REVIEW --> APPROVED")
    lines.append("    APPROVED --> RELEASED")
    lines.append("    RELEASED --> OBSOLETE")

    if bottlenecks:
        slowest_state = max(bottlenecks, key=lambda s: bottlenecks[s])
        node_id = slowest_state.name  # e.g. DocumentState.IN_REVIEW -> "IN_REVIEW",
        # matching the uppercase node IDs used above (NOT state.value,
        # which is lowercase and would silently fail to match any node)
        lines.append(f"    style {node_id} fill:#f4a261,stroke:#e76f51")

    return "\n".join(lines)

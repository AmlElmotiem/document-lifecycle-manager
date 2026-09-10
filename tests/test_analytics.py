from datetime import datetime, timedelta, timezone

from doc_lifecycle import AuditEntry, Document, DocumentState
from doc_lifecycle.analytics import bottleneck_report, format_duration, mermaid_flowchart, time_in_each_state


def _t(seconds_offset: int) -> datetime:
    return datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=seconds_offset)


def _document_with_history(entries: list[AuditEntry]) -> Document:
    """Build a document with a hand-crafted history, so timing tests
    are deterministic instead of depending on real wall-clock time."""
    doc = Document(doc_id="A-001", title="Testdokument", author="Aml")
    doc.history = entries
    doc.state = entries[-1].to_state
    return doc


def test_time_in_each_state_sums_correctly():
    entries = [
        AuditEntry(timestamp=_t(0), from_state=None, to_state=DocumentState.DRAFT, actor="Aml"),
        AuditEntry(timestamp=_t(100), from_state=DocumentState.DRAFT, to_state=DocumentState.IN_REVIEW, actor="Aml"),
        AuditEntry(timestamp=_t(400), from_state=DocumentState.IN_REVIEW, to_state=DocumentState.APPROVED, actor="Dana"),
    ]
    doc = _document_with_history(entries)

    durations = time_in_each_state(doc)

    assert durations[DocumentState.DRAFT] == timedelta(seconds=100)
    assert durations[DocumentState.IN_REVIEW] == timedelta(seconds=300)


def test_revisits_to_the_same_state_are_summed():
    entries = [
        AuditEntry(timestamp=_t(0), from_state=None, to_state=DocumentState.DRAFT, actor="Aml"),
        AuditEntry(timestamp=_t(50), from_state=DocumentState.DRAFT, to_state=DocumentState.IN_REVIEW, actor="Aml"),
        AuditEntry(timestamp=_t(100), from_state=DocumentState.IN_REVIEW, to_state=DocumentState.DRAFT, actor="Bob"),
        AuditEntry(timestamp=_t(180), from_state=DocumentState.DRAFT, to_state=DocumentState.IN_REVIEW, actor="Aml"),
    ]
    doc = _document_with_history(entries)

    durations = time_in_each_state(doc)

    # DRAFT: 0->50 (50s) plus 100->180 (80s) = 130s total
    assert durations[DocumentState.DRAFT] == timedelta(seconds=130)


def test_bottleneck_report_averages_across_documents():
    doc1 = _document_with_history([
        AuditEntry(timestamp=_t(0), from_state=None, to_state=DocumentState.DRAFT, actor="A"),
        AuditEntry(timestamp=_t(100), from_state=DocumentState.DRAFT, to_state=DocumentState.IN_REVIEW, actor="A"),
        AuditEntry(timestamp=_t(300), from_state=DocumentState.IN_REVIEW, to_state=DocumentState.APPROVED, actor="B"),
    ])
    doc2 = _document_with_history([
        AuditEntry(timestamp=_t(0), from_state=None, to_state=DocumentState.DRAFT, actor="A"),
        AuditEntry(timestamp=_t(300), from_state=DocumentState.DRAFT, to_state=DocumentState.IN_REVIEW, actor="A"),
        AuditEntry(timestamp=_t(500), from_state=DocumentState.IN_REVIEW, to_state=DocumentState.APPROVED, actor="B"),
    ])

    report = bottleneck_report([doc1, doc2])

    # DRAFT: (100 + 300) / 2 = 200s
    assert report[DocumentState.DRAFT] == timedelta(seconds=200)


def test_format_duration_picks_sensible_units():
    assert format_duration(timedelta(seconds=30)) == "30s"
    assert format_duration(timedelta(minutes=5)) == "5.0min"
    assert format_duration(timedelta(hours=2)) == "2.0h"
    assert format_duration(timedelta(days=3)) == "3.0d"


def test_mermaid_flowchart_highlights_the_slowest_state():
    bottlenecks = {
        DocumentState.DRAFT: timedelta(seconds=10),
        DocumentState.IN_REVIEW: timedelta(days=5),  # the bottleneck
    }

    chart = mermaid_flowchart(bottlenecks)

    assert "flowchart LR" in chart
    assert "style IN_REVIEW fill:" in chart
    assert "style DRAFT fill:" not in chart

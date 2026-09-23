"""PHI guardrail: reject any file carrying patient names, birth dates, or
record numbers before it is stored or logged (REQ-009, STORY-010).

HosPulse's own hard rule is "no PHI" (see CLAUDE.md): only public CMS HCRIS
data and aggregate financial/operational figures are handled until BAAs and
a HIPAA review exist. STORY-005 (operator uploads: general ledger, A/R
aging, denials summary, staffing) does not exist yet, so this module is
built the same way grounding_guardrail.py was for STORY-011 -- a standalone,
testable check ready for that upload path to call the moment it lands.

Usage at the call site (once STORY-005 exists):

    rows = list(csv.DictReader(uploaded_file))
    result = scan_file_for_phi(rows)
    if not result.ok:
        entry = result.to_audit_entry(file_name=uploaded_file.name)
        log.error("phi_rejected", **entry.as_dict())
        return reject(entry.reason)  # never store or log `rows` itself

Detection has two layers:

1. Header-based (primary): a column whose header names a patient name,
   birth date, or record-number field (e.g. "Patient Name", "DOB", "MRN").
   This is deterministic and is what the acceptance criteria actually
   describe -- a hospital-system export carrying these fields labels them.
2. Content-based (defense in depth): a cell value shaped like a Social
   Security Number, regardless of what its column is called, since an SSN
   is unambiguous PHI/PII even mislabeled. Scoped under "record numbers"
   (REQ-009's three named categories: names, birth dates, record numbers)
   -- an assumption logged here since REQ-009 does not say SSN explicitly,
   but a nine-digit government identifier tied to a patient is exactly the
   kind of record number the requirement means to keep out.

Deliberately NOT attempted: generic content-based detection of names or
birth dates (e.g. "any date-shaped value is a birth date"). Financial
exports are full of legitimate business dates (report date, posting date),
and free text can't be reliably classified as "a name" without a model far
beyond this guardrail's scope -- that would trade false rejections of
ordinary ledger data for a coverage gain the header check already provides
in the realistic case. This is a known limitation, not an oversight.

The audit entry never carries the PHI value itself, only the column name
and category that triggered rejection -- logging patient data while
rejecting a file *for containing* patient data would defeat the point.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Mapping, Sequence

_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")


def _normalize_header(header: str) -> str:
    return re.sub(r"[\s_\-]+", " ", header.strip().lower())


_PATIENT_NAME_HEADERS = {
    "patient name",
    "patientname",
    "full name",
    "first name",
    "last name",
    "patient first name",
    "patient last name",
    "member name",
    "name",
}
_BIRTH_DATE_HEADERS = {
    "dob",
    "date of birth",
    "birth date",
    "birthdate",
}
_RECORD_NUMBER_HEADERS = {
    "mrn",
    "medical record number",
    "medical record no",
    "record number",
    "patient id",
    "patient identifier",
    "chart number",
    "ssn",
    "social security number",
    "social security no",
}

_CATEGORY_HEADERS = {
    "patient_name": _PATIENT_NAME_HEADERS,
    "birth_date": _BIRTH_DATE_HEADERS,
    "record_number": _RECORD_NUMBER_HEADERS,
}


@dataclass(frozen=True)
class PhiFinding:
    """One column that triggered rejection. Never carries a cell value."""

    category: str  # "patient_name" | "birth_date" | "record_number"
    column: str
    basis: str  # "header" | "content"


@dataclass(frozen=True)
class PhiAuditEntry:
    """What gets logged for a rejected file -- reason only, never content."""

    timestamp: str
    decision: str  # "rejected" | "accepted"
    reason: str
    categories: list[str]
    file_name: str | None = None

    def as_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "file_name": self.file_name,
            "decision": self.decision,
            "reason": self.reason,
            "categories": self.categories,
        }


@dataclass(frozen=True)
class PhiScanResult:
    ok: bool
    findings: list[PhiFinding] = field(default_factory=list)

    def reason(self) -> str:
        if self.ok:
            return "no patient name, birth date, or record number field detected"
        parts = ", ".join(f"{f.column!r} ({f.category})" for f in self.findings)
        return f"{len(self.findings)} PHI field(s) detected: {parts}"

    def to_audit_entry(self, file_name: str | None = None, *, now: datetime | None = None) -> PhiAuditEntry:
        moment = now or datetime.now(timezone.utc)
        return PhiAuditEntry(
            timestamp=moment.isoformat(),
            file_name=file_name,
            decision="accepted" if self.ok else "rejected",
            reason=self.reason(),
            categories=sorted({f.category for f in self.findings}),
        )


def scan_file_for_phi(rows: Sequence[Mapping[str, object]]) -> PhiScanResult:
    """Scan parsed file rows (e.g. `csv.DictReader` output) for patient
    names, birth dates, or record numbers, by column header first and then
    by SSN-shaped content in any column the header check didn't already
    catch. Rejects on the first pass over headers plus one pass over
    values -- deterministic, no partial/streamed state to get wrong.
    An empty `rows` (no data at all) is trivially clean: there is nothing
    to protect from yet.
    """
    findings: list[PhiFinding] = []
    flagged_columns: set[str] = set()

    headers: set[str] = set()
    for row in rows:
        headers.update(str(h) for h in row.keys())

    for header in sorted(headers):
        normalized = _normalize_header(header)
        for category, known in _CATEGORY_HEADERS.items():
            if normalized in known:
                findings.append(PhiFinding(category=category, column=header, basis="header"))
                flagged_columns.add(header)
                break  # one category per column is enough

    for row in rows:
        for header, value in row.items():
            header = str(header)
            if header in flagged_columns or value is None:
                continue
            if _SSN_RE.search(str(value)):
                findings.append(PhiFinding(category="record_number", column=header, basis="content"))
                flagged_columns.add(header)

    return PhiScanResult(ok=not findings, findings=findings)


class PhiRejectedError(Exception):
    """Raised by `ingest_file_with_phi_gate` when a file is rejected, after
    the audit entry has already been logged. Carries the entry so a caller
    can surface `.reason` without re-deriving it."""

    def __init__(self, audit_entry: PhiAuditEntry):
        super().__init__(audit_entry.reason)
        self.audit_entry = audit_entry


def ingest_file_with_phi_gate(
    file_name: str,
    rows: Sequence[Mapping[str, object]],
    *,
    store: Callable[[Sequence[Mapping[str, object]]], None],
    log_audit: Callable[[PhiAuditEntry], None],
    now: datetime | None = None,
) -> PhiAuditEntry:
    """The real enforcement point for REQ-009, not just the detector.

    Scans `rows` first. `log_audit` runs exactly once either way, with an
    entry that never carries row content -- only the column names and
    categories that triggered rejection, or an empty list when clean.
    `store` runs only when the scan is clean, and never runs at all for a
    rejected file: rejection happens before storage, not after, by
    construction rather than by caller discipline. Raises `PhiRejectedError`
    on rejection (after logging) so a caller cannot silently ignore it and
    proceed as if the file had been accepted.

    `store` and `log_audit` are injected rather than hardcoded because the
    real Supabase write and the real logger do not exist yet (STORY-005);
    this lets the gate be genuinely exercised now and be handed the real
    implementations later without changing this function.
    """
    result = scan_file_for_phi(rows)
    entry = result.to_audit_entry(file_name=file_name, now=now)
    log_audit(entry)
    if not result.ok:
        raise PhiRejectedError(entry)
    store(rows)
    return entry

"""REQ-017: persist real uploaded export files in Supabase Storage.

Uses the service_role key -- the same trust model as every Postgres write
in this project (the pipeline connects as table owner and bypasses RLS;
here it bypasses Storage policies the same way). The Next.js upload route
has only the anon key and never touches Supabase directly; this module is
only ever called from the trusted Python pipeline.

A Storage upload failure never fails the whole conversion: the metrics
(the primary, already-proven value) still save regardless.
upload_export_file() returns None on any failure rather than raising, so a
NULL storage_path honestly means "not archived," never a silent lie that
it worked. No retry here -- a retry would delay the operator's HTTP
response for a nice-to-have; a missed archive can be reconciled later by
re-running the normalizer against the same file if it still exists.
"""
from __future__ import annotations

import requests

BUCKET = "hospital-exports"
REQUEST_TIMEOUT_SECONDS = 10.0


def upload_export_file(
    content: bytes,
    source_file_hash: str,
    supabase_url: str,
    service_role_key: str,
) -> str | None:
    """Uploads to exports/{source_file_hash}.csv -- the same hash already
    used as export_conversions' idempotency key, so re-uploading identical
    bytes never needs a second object. Returns the storage path on
    success, None on any failure (network, auth, or otherwise)."""
    path = f"exports/{source_file_hash}.csv"
    url = f"{supabase_url}/storage/v1/object/{BUCKET}/{path}"
    try:
        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {service_role_key}",
                "apikey": service_role_key,
                "Content-Type": "text/csv",
                "x-upsert": "true",
            },
            data=content,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        if response.status_code not in (200, 201):
            print(f"error: Storage upload failed ({response.status_code}): {response.text}")
            return None
        return path
    except requests.RequestException as exc:
        print(f"error: Storage upload failed: {exc!r}")
        return None

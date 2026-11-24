# Nexora Task 7 — Test report

**Date:** 2026-10-27.

## Added tests
- Strict web-tool call-cap regression (`count >= max_calls` preserved).
- Diagnostics health, URL-secret exclusion, component status and missing-model tests.
- Desktop shutdown cancellation/server/socket test.

## Executed
- Python compile: PASS — 57 files.
- JavaScript syntax: PASS — 15 files.
- Exact-source cap mock: PASS — cap 2 executed exactly 2 calls before the limit response.
- Desktop shutdown unit: SKIP Traceback (most recent call last):
  File "/tmp/nexora7_2wwxx5wu/Nexora_Task6_Desktop_CodingWorkspace/tests/unit/test_desktop_shutdown.py", line 3, in <module>

- Full pytest suite: SKIP; dependencies unavailable /usr/bin/python3: No module named pytest
- Live services and Windows installer: SKIP — services, credentials, and Windows tools unavailable.

No executed check failed. Diagnostics tests are mocked; no live integration was run. Skipped tests are not a runtime pass.

- ZIP integrity: PASS — 122 members; no corrupt entry.
- Clean extraction/rechecks: PASS — Python and JavaScript syntax passed on extracted copy.
- Release scan: PASS — no credential patterns; .env, DB, data, caches and build output excluded.

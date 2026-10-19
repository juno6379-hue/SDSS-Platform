# 332 independent static review (read-only reviewer agent, 2026-10-19 KST)

## Round 1 (code before review fixes; files archived in pre-review332/)

VERDICT: no data-safety BLOCKING defects. The stated property "any failure stops the adapter" was untrue (F1).

- F1 [BLOCKING for the claim; data-safe] budget.py reserve/settle: legacy-level failures between _read and _save did not stop the adapter (429, over-budget, existing pending, already settled, measured > reserved). test_settle_measurement_bounds relied on that.
- F2 [NON-BLOCKING] bind(): failures before its try block did not stop the adapter, so a failed adapter could be re-bound.
- F3 [NON-BLOCKING] save(): validated and wrote the live caller object. A mutation in between could make the written bytes or _before differ from what was validated.
- F4 [NOTE] metadata_io is a public attribute, so the adapter is not a security boundary.
- F5 [NOTE] Legacy locked(): lock I/O is uncharged, and on Windows an unlink failure can mask the original exception.
- F6 [NOTE] Path case and drive-letter mismatch fails closed. Dual import trips the identity check. A preserved writer temp file blocks later writes.
- F7 [NOTE] History files must be JSON objects of at most 8MiB, which is stricter than legacy.
- F8 [NOTE] The adapter writes compact, sort_keys JSON (format change).
- F9 [NOTE] A direct _save does not check that the lock is held; the exact pin prevents lost updates.
- Test gaps were listed. Most are now covered by the test_review_* tests.

## Round 2 (fix delta)

VERDICT: no blocking defects.

- F1 fixed with _guard() / stop_on_failure. With metadata_io=None it is a nullcontext no-op. The original exception object is re-raised, so the outcome attributes are preserved.
- F2 fixed: every bind failure stops the adapter, and LEDGER_ADAPTER_STOPPED is raised on entry.
- F3 fixed: one deep-copied candidate is validated, written and recorded.
- Mutation run: the 7 expected F1/F2/F3 failures against the pre-review code.
- NOTES: lock contention permanently stops the instance; a second bind disables the originally bound ledger. Both are fail-closed by design.
- Remaining non-blocking gaps: no test that STOPPED on guard entry creates no lock file; no test for F5 (unlink masking).

"""Synthetic-only tests: no operational recovery snapshots or ledger writes."""
import copy
import unittest
from unittest.mock import patch

from backend.app.data.recovery_commit_contract import validate_recovery_commit_transition as check


PHASES = ("PREPARED", "LEDGER_RECORDED", "AGGREGATE_RECORDED", "COMMITTED")
TARGETS = ("ledger_sha256", "aggregate_sha256", "run_result_sha256")


def observation(phase="PREPARED"):
    before = dict(zip(TARGETS, (str(i) * 64 for i in (1, 2, 3))))
    after = dict(zip(TARGETS, (str(i) * 64 for i in (4, 5, 6))))
    return {
        "schema_version": 1, "operation_id": "recovery-op-1", "batch_key": "parallel-v2-banten-2023",
        "config_sha256": "a" * 64, "terminal_sha256": "b" * 64,
        "reconciliation_sha256": "c" * 64, "phase": phase,
        "phase_evidence_sha256": "d" * 64, "before": before, "expected_after": after,
        "observed": {key: (after if index < PHASES.index(phase) else before)[key]
                     for index, key in enumerate(TARGETS)},
    }


class RecoveryCommitContractTests(unittest.TestCase):
    def assert_safety(self, result):
        self.assertEqual(len(result), 18)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["claim_verification"], "UNVERIFIED")
        self.assertEqual(result["exactly_once_applied"], "UNKNOWN")
        for key in ("settlement_authorized", "refund_authorized", "restart_authorized",
                    "write_authorized", "execution_authorized", "commit_executed"):
            self.assertIs(result[key], False)
        for key in ("proposed_refund_bytes", "source_files_read", "source_files_written", "network_requests"):
            self.assertIs(type(result[key]), int)
            self.assertEqual(result[key], 0)

    def test_initial_and_all_three_adjacent_transitions_remain_blocked(self):
        previous = None
        for phase in PHASES:
            current = observation(phase)
            result = check(previous, current)
            self.assertEqual(result["metadata_transition"], "INITIAL_PREPARED" if previous is None else "NEXT_PHASE")
            self.assertIsNone(result["issue"])
            self.assert_safety(result)
            previous = current

    def test_identical_replay_for_each_phase_and_conflicting_replay(self):
        for phase in PHASES:
            before = observation(phase)
            self.assertEqual(check(before, copy.deepcopy(before))["metadata_transition"], "IDENTICAL_REPLAY")
            after = copy.deepcopy(before)
            after["phase_evidence_sha256"] = "e" * 64
            self.assertEqual(check(before, after)["issue"]["code"], "REPLAY_CONFLICT")

    def test_all_phase_pairs_skip_regression_and_initial_rules(self):
        for i, prior_phase in enumerate(PHASES):
            for j, next_phase in enumerate(PHASES):
                result = check(observation(prior_phase), observation(next_phase))
                self.assert_safety(result)
                if j < i:
                    self.assertEqual(result["issue"]["code"], "PHASE_REGRESSION")
                elif j > i + 1:
                    self.assertEqual(result["issue"]["code"], "PHASE_SKIP")
            if i:
                self.assertEqual(check(None, observation(prior_phase))["issue"]["code"], "INITIAL_PHASE_INVALID")

    def test_crash_after_aggregate_does_not_imply_run_result_committed(self):
        previous = observation("AGGREGATE_RECORDED")
        current = observation("COMMITTED")
        current["observed"]["run_result_sha256"] = current["before"]["run_result_sha256"]
        result = check(previous, current)
        self.assertEqual(result["issue"], {"code": "PHASE_OBSERVATION_MISMATCH", "field": "observed.run_result_sha256", "side": "CURRENT"})
        current["observed"]["run_result_sha256"] = None
        self.assertEqual(check(previous, current)["issue"]["code"], "EVIDENCE_MISSING")

    def test_missing_proofs_and_observations_are_not_filled(self):
        for field in ("terminal_sha256", "reconciliation_sha256", "phase_evidence_sha256"):
            current = observation("COMMITTED")
            current[field] = None
            result = check(None, current)
            self.assertEqual(result["issue"], {"code": "EVIDENCE_MISSING", "field": field, "side": "CURRENT"})
        for target in TARGETS:
            current = observation()
            current["observed"][target] = None
            self.assertEqual(check(None, current)["issue"]["field"], "observed." + target)

    def test_identity_conflicts_include_all_pins_and_maps(self):
        for field in ("operation_id", "batch_key", "config_sha256", "terminal_sha256", "reconciliation_sha256", "before", "expected_after"):
            previous, current = observation(), observation("LEDGER_RECORDED")
            if field in ("before", "expected_after"):
                current[field]["ledger_sha256"] = "e" * 64
                if field == "expected_after":
                    current["observed"]["ledger_sha256"] = "e" * 64
            else:
                current[field] = "other" if field.endswith("id") or field == "batch_key" else "e" * 64
            result = check(previous, current)
            self.assertEqual(result["issue"], {"code": "OPERATION_IDENTITY_CONFLICT", "field": field, "side": "COMPARISON"})

    def test_exact_shapes_and_builtin_types(self):
        class DictSubclass(dict):
            pass
        bad = [None, [], True, DictSubclass(observation())]
        for value in bad:
            self.assertEqual(check(None, value)["issue"]["code"], "OBSERVATION_SCHEMA_INVALID")
        for value in (True, 1.0, "1", 2):
            current = observation()
            current["schema_version"] = value
            self.assertEqual(check(None, current)["issue"]["field"], "schema_version")
        for field in observation():
            current = observation()
            del current[field]
            self.assertEqual(check(None, current)["issue"]["code"], "OBSERVATION_SCHEMA_INVALID")
        for field in ("before", "expected_after", "observed"):
            for mapping in ({}, DictSubclass(observation()[field]), {**observation()[field], "extra": None}):
                current = observation()
                current[field] = mapping
                self.assertEqual(check(None, current)["issue"]["field"], field)
        current = observation()
        current["extra"] = current
        self.assertEqual(check(None, current)["issue"]["code"], "OBSERVATION_SCHEMA_INVALID")

    def test_bounded_ids_control_surrogate_and_path_rejected(self):
        for field in ("operation_id", "batch_key"):
            for value in ("", ".", "..", "a/b", "a\\b", "a:b", "https://x", " a", "a\n", "\ud800", "a" * 129, True, 12):
                current = observation()
                current[field] = value
                self.assertEqual(check(None, current)["issue"]["code"], "OBSERVATION_ID_INVALID")
            current = observation()
            current[field] = "a" * 128
            self.assertEqual(check(None, current)["metadata_transition"], "INITIAL_PREPARED")

    def test_exact_builtin_keys_reject_string_subclasses(self):
        class Key(str):
            pass
        current = observation()
        current[Key("phase")] = current.pop("phase")
        self.assertEqual(check(None, current)["issue"]["field"], "observation")
        for field in ("before", "expected_after", "observed"):
            current = observation()
            mapping = current[field]
            mapping[Key("ledger_sha256")] = mapping.pop("ledger_sha256")
            self.assertEqual(check(None, current)["issue"]["field"], field)

    def test_strict_sha_and_phase_types(self):
        for field in ("config_sha256", "terminal_sha256", "reconciliation_sha256", "phase_evidence_sha256"):
            for value in (True, 1, "A" * 64, "a" * 63, "a" * 65, "a" * 63 + "\n", "\ud800" * 64):
                current = observation()
                current[field] = value
                self.assertEqual(check(None, current)["issue"]["code"], "SHA256_INVALID")
        for field in ("before", "expected_after", "observed"):
            current = observation()
            current[field]["ledger_sha256"] = False
            self.assertEqual(check(None, current)["issue"]["code"], "SHA256_INVALID")
        for value in (True, 1, "prepared", " COMMITTED", None):
            current = observation()
            current["phase"] = value
            self.assertEqual(check(None, current)["issue"]["code"], "PHASE_INVALID")

    def test_invalid_collision_key_never_invokes_equality(self):
        class PoisonKey:
            def __hash__(self):
                return hash("phase")

            def __eq__(self, other):
                raise AssertionError("invalid key callback")

        current = observation()
        del current["phase"]
        current[PoisonKey()] = "PREPARED"
        result = check(None, current)
        self.assertEqual(result["issue"]["code"], "OBSERVATION_SCHEMA_INVALID")
        self.assertIsNone(result["current_phase"])
        self.assert_safety(result)

    def test_previous_invalid_and_format_missing_mismatch_priority(self):
        previous, current = observation(), observation("COMMITTED")
        previous["terminal_sha256"] = None
        current["schema_version"] = True
        self.assertEqual(check(previous, current)["issue"]["side"], "PREVIOUS")
        current = observation("COMMITTED")
        current["terminal_sha256"] = None
        current["observed"]["run_result_sha256"] = "bad"
        self.assertEqual(check(None, current)["issue"]["code"], "SHA256_INVALID")
        current["observed"]["run_result_sha256"] = "f" * 64
        self.assertEqual(check(None, current)["issue"]["field"], "terminal_sha256")
        current["terminal_sha256"] = "b" * 64
        self.assertEqual(check(None, current)["issue"]["code"], "PHASE_OBSERVATION_MISMATCH")

    def test_identical_before_after_and_opaque_proof_do_not_authorize(self):
        previous = None
        for phase in PHASES:
            current = observation(phase)
            current["expected_after"] = copy.deepcopy(current["before"])
            current["observed"] = copy.deepcopy(current["before"])
            result = check(previous, current)
            self.assertIsNone(result["issue"])
            self.assert_safety(result)
            previous = current

    def test_pure_no_io_no_mutation_no_sensitive_echo(self):
        previous, current = observation(), observation("LEDGER_RECORDED")
        original = copy.deepcopy((previous, current))
        with patch("builtins.open", side_effect=AssertionError("file IO")), patch("pathlib.Path.open", side_effect=AssertionError("path IO")), patch("socket.socket", side_effect=AssertionError("network IO")):
            result = check(previous, current)
            result["issue"] = "caller edit"
            rejected = check(None, {**current, "terminal_sha256": "secret-path"})
        self.assertEqual((previous, current), original)
        self.assertNotIn("secret-path", repr(rejected))
        self.assertNotIn(current["operation_id"], repr(rejected))


if __name__ == "__main__":
    unittest.main()

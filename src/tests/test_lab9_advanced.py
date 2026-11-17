"""M5-M7 self-check (Advanced/Expert). Run: python -m pytest -q -m student -o addopts= -k advanced
Public vectors only; the instructor grades with hidden ones."""
import copy
import math

import pytest

pytestmark = pytest.mark.student


@pytest.fixture(scope="module")
def stats():
    from lab9 import stats

    return stats


@pytest.mark.parametrize("n,c,k,want", [(5, 5, 5, 1.0), (5, 0, 1, 0.0), (5, 2, 1, 0.4), (10, 3, 3, 1 - 35 / 120)])
def test_pass_at_k(stats, n, c, k, want):
    assert math.isclose(stats.pass_at_k(n, c, k), want, abs_tol=1e-9)


@pytest.mark.parametrize("n,c,k,want", [(5, 5, 5, 1.0), (5, 4, 5, 0.0), (5, 4, 3, 0.4), (10, 8, 2, 28 / 45)])
def test_pass_hat_k(stats, n, c, k, want):
    assert math.isclose(stats.pass_hat_k(n, c, k), want, abs_tol=1e-9)


def test_pass_k_rejects_bad_args(stats):
    for args in [(5, 6, 1), (5, 2, 0), (3, 1, 4)]:
        with pytest.raises(ValueError):
            stats.pass_at_k(*args)


def _report(rows, metrics, items=4, seeds=(1, 2)):
    return {"manifest": {"eval_set_sha": "x", "items": items, "seeds": list(seeds)},
            "rows": rows, "metrics": metrics, "evaluator_failures": []}


ROWS = [{"item_id": f"E-{i:03d}", "seed": s, "pass_rate": True, "slices": ["denial"] if i < 2 else []}
        for i in range(4) for s in (1, 2)]
SPEC = {"eval_set_version": "v2", "metrics": [{"id": "pass_rate", "kind": "capability", "blocking": True,
                                               "threshold": {"min": 0.8}}]}


def test_integrity_flags_nan_and_dropped_rows():
    from lab9 import gate

    base = _report(copy.deepcopy(ROWS), {"pass_rate": 1.0})
    assert gate.integrity_check(base, base, SPEC) == []
    nan = _report(copy.deepcopy(ROWS), {"pass_rate": float("nan")})
    assert gate.integrity_check(nan, base, SPEC)
    dropped = _report(copy.deepcopy(ROWS[:-1]), {"pass_rate": 1.0})
    assert gate.integrity_check(dropped, base, SPEC)


def test_integrity_flags_loosened_spec():
    from lab9 import gate

    base = _report(copy.deepcopy(ROWS), {"pass_rate": 1.0})
    loose = copy.deepcopy(SPEC)
    loose["metrics"][0]["threshold"]["min"] = 0.5
    assert gate.integrity_check(base, base, loose, SPEC)
    assert gate.integrity_check(base, base, SPEC, SPEC) == []


def test_slice_check_blocks_a_slice_below_floor():
    from lab9 import gate

    base = _report(copy.deepcopy(ROWS), {"pass_rate": 1.0})
    rows = copy.deepcopy(ROWS)
    for r in rows:
        if "denial" in r["slices"] and r["seed"] == 1:
            r["pass_rate"] = False
    spec = dict(SPEC, slices=[{"name": "denial", "metric": "pass_rate", "min": 0.9, "blocking": True}])
    blocked, _ = gate.slice_check(_report(rows, {"pass_rate": 0.75}), base, spec)
    assert blocked == ["slice:denial/pass_rate"]


@pytest.mark.parametrize("fn_name", ["pass_at_k", "pass_hat_k"])
@pytest.mark.parametrize("args", [(0, 0, 1), (-1, 0, 1), (5, -1, 1), (5, 6, 1),
                                  (5, 1, 6), (5, 1, 0), (5.0, 1, 1), (5, True, 1)])
def test_advanced_pass_estimators_validate_inputs(stats, fn_name, args):
    with pytest.raises(ValueError):
        getattr(stats, fn_name)(*args)


def test_advanced_slice_checks_missing_items():
    from lab9 import gate
    base = _report(copy.deepcopy(ROWS), {"pass_rate": 1.0})
    spec = dict(SPEC, slices=[{"name": "money_movement", "metric": "pass_rate", "min": 0.95, "blocking": True}])
    blocked, _ = gate.slice_check(base, base, spec)
    assert blocked == ["slice:money_movement/pass_rate"]


@pytest.mark.parametrize("mutation", ["duplicate", "evaluator_failure", "missing_value", "nan_row", "slice_tags", "seeds"])
def test_advanced_integrity_rejects_report_tampering(mutation):
    from lab9 import gate
    base = _report(copy.deepcopy(ROWS), {"pass_rate": 1.0})
    pr = copy.deepcopy(base)
    if mutation == "duplicate":
        pr["rows"][-1] = copy.deepcopy(pr["rows"][0])
    elif mutation == "evaluator_failure":
        pr["evaluator_failures"] = ["grader crashed"]
    elif mutation == "missing_value":
        pr["rows"][0]["pass_rate"] = None
    elif mutation == "nan_row":
        pr["rows"][0]["pass_rate"] = float("nan")
    elif mutation == "slice_tags":
        pr["rows"][0]["slices"] = []
    elif mutation == "seeds":
        pr["manifest"]["seeds"] = [1]
    assert gate.integrity_check(pr, base, SPEC)


@pytest.mark.parametrize("mutation", ["drop_metric", "disable_blocking", "drop_slice", "drop_ci", "lower_slice_floor"])
def test_advanced_integrity_ratchet_rejects_constraint_removal(mutation):
    from lab9 import gate
    base = _report(copy.deepcopy(ROWS), {"pass_rate": 1.0})
    original = copy.deepcopy(SPEC)
    original["slices"] = [{"name": "denial", "metric": "pass_rate", "min": 0.9,
                           "no_significant_drop": True, "blocking": True}]
    loose = copy.deepcopy(original)
    if mutation == "drop_metric":
        loose["metrics"] = []
    elif mutation == "disable_blocking":
        loose["metrics"][0]["blocking"] = False
    elif mutation == "drop_slice":
        loose["slices"] = []
    elif mutation == "drop_ci":
        loose["slices"][0].pop("no_significant_drop")
    elif mutation == "lower_slice_floor":
        loose["slices"][0]["min"] = 0.5
    assert gate.integrity_check(base, base, loose, original)


def test_advanced_integrity_accepts_stricter_spec():
    from lab9 import gate
    base = _report(copy.deepcopy(ROWS), {"pass_rate": 1.0})
    stricter = copy.deepcopy(SPEC)
    stricter["metrics"][0]["threshold"]["min"] = 0.9
    assert gate.integrity_check(base, base, stricter, SPEC) == []

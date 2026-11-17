"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, load_spec, per_item


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate.
    Must catch at least:
      - any metric value in pr["metrics"] that is NaN or inf
      - len(pr["rows"]) != manifest items x len(manifest seeds)   (dropped / duplicated rows)
      - the (item_id, seed) set of PR differs from the baseline's (cherry-picked seeds/items)
      - pr["evaluator_failures"] non-empty, or a row whose value for a graded spec metric is
        None (a crashed grader silently scores as "missing" and drops out of the mean)
      - base_spec given and a threshold in spec is LOOSER than in base_spec for the same
        eval-set version (ratchet: max may not rise, min may not fall, a blocking metric may
        not become non-blocking, a metric may not disappear; the same for spec["slices"],
        including dropping no_significant_drop)
      - an item's slice tags in PR rows differ from the baseline's (relabelling an item out of a
        slice hides its regression from the slice gate)"""
    from collections import Counter
    from math import isfinite
    from lab9.graders import GRADERS

    problems = []

    def finite_number(value):
        return isinstance(value, (int, float)) and isfinite(value)

    def inspect_report(report, prefix):
        manifest = report.get("manifest", {})
        rows = report.get("rows", [])
        seeds = manifest.get("seeds", [])
        items = manifest.get("items")
        if not isinstance(items, int) or isinstance(items, bool) or items <= 0:
            problems.append(f"{prefix}: invalid item count")
        if not seeds or len(set(seeds)) != len(seeds):
            problems.append(f"{prefix}: empty or duplicate seeds")
        if isinstance(items, int) and len(rows) != items * len(seeds):
            problems.append(f"{prefix}: row count differs from items x seeds")
        pairs = [(r.get("item_id"), r.get("seed")) for r in rows]
        if any(count != 1 for count in Counter(pairs).values()):
            problems.append(f"{prefix}: duplicate item/seed rows")
        ids = {item for item, seed in pairs}
        if len(ids) != items or None in ids:
            problems.append(f"{prefix}: item count or item ids invalid")
        if set(pairs) != {(item, seed) for item in ids for seed in seeds}:
            problems.append(f"{prefix}: incomplete item/seed grid")
        if report.get("evaluator_failures"):
            problems.append(f"{prefix}: evaluator_failures is not empty")
        metrics = report.get("metrics", {})
        for mid, value in metrics.items():
            if not finite_number(value):
                problems.append(f"{prefix}: non-finite or missing metric {mid}")
        for m in spec.get("metrics", []):
            mid = m["id"]
            if mid not in metrics:
                problems.append(f"{prefix}: missing metric {mid}")
            if mid in GRADERS:
                for row in rows:
                    value = row.get(mid)
                    if not isinstance(value, bool) and not (
                        finite_number(value) and value in (0, 1)
                    ):
                        problems.append(f"{prefix}: invalid row value for {mid}")
                        break
        tags_by_item = {}
        for row in rows:
            tags = row.get("slices", [])
            if not isinstance(tags, list) or any(not isinstance(t, str) for t in tags):
                problems.append(f"{prefix}: invalid slice tags")
                continue
            tags = frozenset(tags)
            item = row.get("item_id")
            if item in tags_by_item and tags_by_item[item] != tags:
                problems.append(f"{prefix}: inconsistent slice tags across seeds")
            tags_by_item[item] = tags
        return set(pairs), tags_by_item

    pr_pairs, pr_tags = inspect_report(pr, "PR")
    base_pairs, base_tags = inspect_report(base, "baseline")
    if pr_pairs != base_pairs:
        problems.append("PR item/seed set differs from baseline")
    if pr_tags != base_tags:
        problems.append("PR slice tags differ from baseline")

    # Ratchet: so sánh ràng buộc trong cùng phiên bản eval set.
    if base_spec is not None and spec.get("eval_set_version") == base_spec.get("eval_set_version"):
        def compare_constraints(old, new, name, thresholds):
            if old.get("blocking") and not new.get("blocking"):
                problems.append(f"ratchet: {name} lost blocking")
            old_th = old.get("threshold", {}) if thresholds else old
            new_th = new.get("threshold", {}) if thresholds else new
            for key in ("min", "max", "max_increase"):
                if key not in old_th:
                    continue
                value = new_th.get(key)
                if not finite_number(value) or (
                    value < old_th[key] if key == "min" else value > old_th[key]
                ):
                    problems.append(f"ratchet: {name} loosened {key}")
            if old_th.get("no_significant_drop") and not new_th.get("no_significant_drop"):
                problems.append(f"ratchet: {name} lost no_significant_drop")

        current_metrics = {m["id"]: m for m in spec.get("metrics", [])}
        for old in base_spec.get("metrics", []):
            mid = old["id"]
            new = current_metrics.get(mid)
            if new is None:
                problems.append(f"ratchet: missing metric {mid}")
                continue
            compare_constraints(old, new, mid, True)
            for key in ("kind", "grader", "level"):
                if key in old and new.get(key) != old[key]:
                    problems.append(f"ratchet: {mid} changed {key}")
        current_slices = {(m["name"], m["metric"]): m for m in spec.get("slices", [])}
        for old in base_spec.get("slices", []):
            key = (old["name"], old["metric"])
            if key not in current_slices:
                problems.append(f"ratchet: missing slice {key}")
            else:
                compare_constraints(old, current_slices[key], f"slice:{key}", False)
    return list(dict.fromkeys(problems))


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice.
    For each entry of spec["slices"] ({"name", "metric", "min"?, "no_significant_drop"?, "blocking"}):
      - value = mean of per_item(pr, metric, slice_name=name)
      - fail if below "min", or if no_significant_drop and the paired CI over the slice's items
        lies entirely below 0
    Return (blocked ids like "slice:money_movement/pass_rate", report lines)."""
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for entry in spec.get("slices", []):
        name, metric = entry["name"], entry["metric"]
        sid = f"slice:{name}/{metric}"
        a = per_item(pr, metric, slice_name=name)
        b = per_item(base, metric, slice_name=name)
        problems = []
        note = ""
        if not a or set(a) != set(b):
            problems.append("missing_or_mismatched_items")
            value = None
        else:
            value = sum(a.values()) / len(a)
            if "min" in entry and value < entry["min"]:
                problems.append("below_floor")
            if entry.get("no_significant_drop"):
                keys = sorted(a)
                delta, lo, hi = stats.paired_bootstrap(
                    [a[k] for k in keys], [b[k] for k in keys],
                    n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027),
                    confidence=bs.get("confidence", 0.95))
                note = f"delta={delta:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
                if hi < 0:
                    problems.append("significant_drop")
        if problems and entry.get("blocking"):
            blocked.append(sid)
        verdict = "BLOCK" if problems and entry.get("blocking") else "warn" if problems else "ok"
        lines.append(f"  {sid} value={value} {note} {verdict} {','.join(problems)}")
    return blocked, lines


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid):
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            keys = sorted(set(a) & set(b))
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

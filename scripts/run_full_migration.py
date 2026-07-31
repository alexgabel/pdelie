"""v0.36a-beta: orchestrate the migration audit over a scope of experiments.

The generalization of :mod:`scripts.run_alpha_migration` from one experiment to
a scope config naming many. Everything the alpha orchestrator measured about the
two environments still holds and is not restated here; see that module's
docstring for the CPython 3.11 constraint, the ``[downstream]`` extra, and the
``setuptools>=68`` floor.

What changes at beta
====================

**The wheels are built once, not once per experiment.** Alpha built two wheels
for its single experiment. Beta runs five, and rebuilding would be both slow and
wrong: five builds of the same source could in principle differ, and then a
per-experiment difference would be unattributable. One build per side, reused
across the scope, keeps the wheel identity constant so any difference is a
property of the experiment rather than of the build.

**Alpha is re-run through this orchestrator.** ``--include-alpha-regression``
replays the alpha experiment under beta's tooling and asserts the label counts
match what alpha froze. Beta exit gate 6 asks that alpha's conclusions remain
valid under generalized tooling; that is a claim about behaviour, so it is
checked by running it rather than by inspection.

**Per-experiment reports plus one aggregate.** Each experiment gets its own
report; the aggregate sums the label counts and lists every unexplained
regression across the whole scope. A scope is clean only if every experiment is.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
LEGACY_TAG = "v0.22.0"
LEGACY_PYTHON = "3.11"
MODERN_PYTHON = "3.12"
LEGACY_BUILD_PINS = ("setuptools==68.2.2", "wheel==0.38.4")

#: What alpha froze, per ``docs/planning/V0_36A_ALPHA_MIGRATION_FREEZE.md``.
#: Compared on non-zero entries only: ``label_counts`` reports all seven labels
#: of the vocabulary, and the zeros are noise in an equality check.
ALPHA_EXPECTED_LABEL_COUNTS: dict[str, int] = {
    "exactly_preserved": 6,
    "numerically_equivalent_within_tolerance": 9,
    "blocked_missing_legacy_dependency": 1,
}


def nonzero(counts: dict[str, int]) -> dict[str, int]:
    """Drop zero-count labels so two label-count maps compare on substance."""
    return {label: count for label, count in counts.items() if count}


def run(command: list[str], *, cwd: Path | None = None) -> None:
    print(f"$ {' '.join(command)}")
    subprocess.run(command, cwd=cwd, check=True)


def build_wheel(source: Path, outdir: Path, python: str, pins: tuple[str, ...]) -> Path:
    venv = outdir / f"buildenv_{python.replace('.', '')}"
    run(["uv", "venv", "--python", python, "--seed", str(venv), "--quiet"])
    interpreter = venv / "bin" / "python"
    run([
        str(interpreter), "-m", "pip", "install", "-q",
        "--disable-pip-version-check", *pins, "build",
    ])
    run([
        str(interpreter), "-m", "build", "--wheel", "--no-isolation",
        "--outdir", str(outdir), str(source),
    ])
    wheels = sorted(outdir.glob("*.whl"))
    if not wheels:
        raise SystemExit(f"no wheel produced in {outdir}")
    return wheels[-1]


_COMPARE_SOURCE = """\
import json, sys
from pathlib import Path
from pdelie.audit import (
    compare_pipeline_stages,
    PipelineMigrationComparisonPolicy,
    StagePolicy,
)

config = json.loads(Path(sys.argv[1]).read_text())
spec = json.loads(Path(sys.argv[5]).read_text())
tol = spec['default_tolerance_numeric']
inv = spec.get('qualitative_invariants', {})
over = spec.get('stage_overrides', {})
stages = {}
for item in config['stages']:
    sid, cls = item['stage_id'], item['comparison_class']
    kw = dict(over.get(sid, {}))
    if cls == 'tolerance_numeric':
        kw.setdefault('rtol', tol['rtol'])
        kw.setdefault('atol', tol['atol'])
    if cls == 'qualitative_invariant':
        kw.setdefault('invariant', inv.get(sid, 'sign'))
    stages[sid] = StagePolicy(stage_id=sid, **kw)
report = compare_pipeline_stages(
    legacy_bundle_dir=Path(sys.argv[2]),
    modern_bundle_dir=Path(sys.argv[3]),
    experiment_config=config,
    comparison_policy=PipelineMigrationComparisonPolicy(
        policy_id=spec['policy_id'], stage_policies=stages
    ),
)
Path(sys.argv[4]).write_text(
    json.dumps(report, indent=2, sort_keys=True, allow_nan=False)
)
print('label counts:', json.dumps(report['label_counts'], sort_keys=True))
"""


def _run_experiment(
    *,
    experiment: str,
    config_path: Path,
    policy_path: Path,
    out: Path,
    legacy_python: Path,
    legacy_wheel: Path,
    legacy_src: Path,
    modern_python: Path,
    modern_wheel: Path,
    compare_script: Path,
) -> dict[str, Any]:
    """Export both sides for one experiment and compare them."""
    legacy_bundles = out / "bundles" / experiment / "legacy"
    modern_bundles = out / "bundles" / experiment / "modern"

    # cwd is the legacy worktree so provenance describes v0.22.0.
    run([
        str(legacy_python), str(REPO_ROOT / "scripts/legacy_exporter.py"),
        "--config", str(config_path),
        "--output-dir", str(legacy_bundles),
        "--wheel", str(legacy_wheel),
    ], cwd=legacy_src)
    run([
        str(modern_python), str(REPO_ROOT / "scripts/modern_exporter.py"),
        "--config", str(config_path),
        "--output-dir", str(modern_bundles),
        "--wheel", str(modern_wheel),
    ], cwd=REPO_ROOT)

    report_path = out / f"migration_report_{experiment}.json"
    run([
        str(modern_python), str(compare_script), str(config_path),
        str(legacy_bundles), str(modern_bundles), str(report_path),
        str(policy_path),
    ])
    report: dict[str, Any] = json.loads(report_path.read_text())
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the v0.36a-beta full migration audit over a scope."
    )
    parser.add_argument(
        "--scope",
        type=Path,
        default=REPO_ROOT / "configs/full_migration/full_migration_scope.json",
        help="scope manifest naming the experiments, config dir and policy",
    )
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--include-alpha-regression",
        action="store_true",
        help="also replay the alpha experiment and assert its frozen label counts",
    )
    args = parser.parse_args(argv)

    scope = json.loads(Path(args.scope).read_text())
    out = Path(args.output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)

    # --- build both sides once, reused across the whole scope ---------------
    legacy_src = out / "legacy_src"
    if not legacy_src.exists():
        run(["git", "worktree", "add", "--detach", str(legacy_src), LEGACY_TAG], cwd=REPO_ROOT)

    legacy_dist = out / "legacy_dist"
    legacy_dist.mkdir(exist_ok=True)
    legacy_wheel = build_wheel(legacy_src, legacy_dist, LEGACY_PYTHON, LEGACY_BUILD_PINS)

    legacy_venv = out / "legacy_venv"
    run(["uv", "venv", "--python", LEGACY_PYTHON, "--seed", str(legacy_venv), "--quiet"])
    legacy_python = legacy_venv / "bin" / "python"
    run([
        str(legacy_python), "-m", "pip", "install", "-q",
        "--disable-pip-version-check", f"{legacy_wheel}[downstream]",
    ])

    modern_dist = out / "modern_dist"
    modern_dist.mkdir(exist_ok=True)
    modern_wheel = build_wheel(REPO_ROOT, modern_dist, MODERN_PYTHON, ("setuptools", "wheel"))

    modern_venv = out / "modern_venv"
    run(["uv", "venv", "--python", MODERN_PYTHON, "--seed", str(modern_venv), "--quiet"])
    modern_python = modern_venv / "bin" / "python"
    run([
        str(modern_python), "-m", "pip", "install", "-q",
        "--disable-pip-version-check", f"{modern_wheel}[downstream]",
    ])

    compare_script = out / "_compare.py"
    compare_script.write_text(_COMPARE_SOURCE, encoding="utf-8")

    shared = {
        "out": out,
        "legacy_python": legacy_python,
        "legacy_wheel": legacy_wheel,
        "legacy_src": legacy_src,
        "modern_python": modern_python,
        "modern_wheel": modern_wheel,
        "compare_script": compare_script,
    }

    # --- the scope ----------------------------------------------------------
    config_dir = REPO_ROOT / scope["config_dir"]
    policy_path = REPO_ROOT / scope["comparison_policy"]
    totals: dict[str, int] = {}
    unexplained: list[str] = []
    per_experiment: dict[str, Any] = {}

    for experiment in scope["experiments"]:
        config_path = config_dir / f"{experiment}.json"
        if not config_path.is_file():
            raise SystemExit(f"unknown experiment config: {config_path}")
        report = _run_experiment(
            experiment=experiment,
            config_path=config_path,
            policy_path=policy_path,
            **shared,  # type: ignore[arg-type]
        )
        for label, count in report["label_counts"].items():
            totals[label] = totals.get(label, 0) + count
        unexplained.extend(
            f"{experiment}/{stage}" for stage in report["unexplained_regression_stage_ids"]
        )
        per_experiment[experiment] = {
            "label_counts": report["label_counts"],
            "all_stages_explained": report["all_stages_explained"],
        }

    # --- alpha regression, beta exit gate 6 ---------------------------------
    alpha_regression: dict[str, Any] | None = None
    if args.include_alpha_regression:
        alpha = scope["alpha_regression_manifest"]
        alpha_dir = REPO_ROOT / alpha["config_dir"]
        alpha_policy = REPO_ROOT / alpha["comparison_policy"]
        alpha_counts: dict[str, int] = {}
        for experiment in alpha["experiments"]:
            report = _run_experiment(
                experiment=experiment,
                config_path=alpha_dir / f"{experiment}.json",
                policy_path=alpha_policy,
                **shared,  # type: ignore[arg-type]
            )
            for label, count in report["label_counts"].items():
                alpha_counts[label] = alpha_counts.get(label, 0) + count
        alpha_counts = nonzero(alpha_counts)
        matches = alpha_counts == ALPHA_EXPECTED_LABEL_COUNTS
        alpha_regression = {
            "expected_label_counts": dict(ALPHA_EXPECTED_LABEL_COUNTS),
            "observed_label_counts": alpha_counts,
            "alpha_conclusions_reproduced": matches,
        }
        if not matches:
            raise SystemExit(
                f"beta exit gate 6 failed: replaying alpha under the generalized "
                f"orchestrator gave {alpha_counts}, but alpha froze "
                f"{ALPHA_EXPECTED_LABEL_COUNTS}."
            )

    aggregate = {
        "report_type": "pdelie_full_migration_aggregate_report",
        "schema_version": "0.1",
        "scope_id": scope["scope_id"],
        "experiments": list(scope["experiments"]),
        "experiment_count": len(scope["experiments"]),
        "label_counts": totals,
        "stage_count": sum(totals.values()),
        "per_experiment": per_experiment,
        "unexplained_regression_stage_ids": unexplained,
        "all_stages_explained": not unexplained,
        "alpha_regression": alpha_regression,
    }
    aggregate_path = out / "migration_report_aggregate.json"
    aggregate_path.write_text(
        json.dumps(aggregate, indent=2, sort_keys=True, allow_nan=False), encoding="utf-8"
    )

    print(f"\naggregate report written to {aggregate_path}")
    print(json.dumps(totals, indent=2, sort_keys=True))
    if unexplained:
        print(f"UNEXPLAINED REGRESSIONS: {unexplained}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

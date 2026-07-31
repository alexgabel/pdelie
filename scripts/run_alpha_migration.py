"""v0.36a-alpha: orchestrate the paper-critical migration audit.

Runs in a third process that owns neither environment. Builds two wheels, makes
two virtualenvs, runs each exporter inside its own, then compares the resulting
bundles with the modern comparator.

Measured environment facts this script encodes
==============================================

* The legacy venv must be **CPython 3.11**: ``v0.22.0`` gates ``pysindy`` and
  ``scikit-learn`` behind ``python_version < '3.12'``.
* Those packages are in the ``[downstream]`` extra, so the install target is
  ``pdelie[downstream]``, not bare ``pdelie``.
* The legacy wheel needs ``setuptools>=68`` -- its own ``[build-system]`` says
  so. The v0.36 plan's ``setuptools==65.5.0`` pin fails with
  ``Missing dependencies: setuptools>=68``. Pinned here to ``68.2.2``.
* The legacy exporter is run with ``cwd`` set to the legacy worktree, so the
  ``git_commit`` and ``source_dirty`` it records describe **v0.22.0**, not
  whatever the operator happens to have checked out.

The legacy worktree is added detached at the tag and is never written to; exit
gate A-alpha-5 asserts the legacy artifacts are untouched.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LEGACY_TAG = "v0.22.0"
LEGACY_PYTHON = "3.11"
MODERN_PYTHON = "3.12"
LEGACY_BUILD_PINS = ("setuptools==68.2.2", "wheel==0.38.4")

#: The legacy runtime venv needs setuptools as well. PySINDy 1.7.5 imports
#: ``pkg_resources``, which setuptools removed in 81+, and ``uv venv --seed``
#: seeds a current setuptools. Alpha routes around PySINDy so it never trips
#: this, but the venv is otherwise identical to beta's and the pin belongs in
#: both. See scripts/run_full_migration.py for the measurement.
LEGACY_RUNTIME_PINS = ("setuptools==68.2.2",)


def run(command: list[str], *, cwd: Path | None = None) -> None:
    print(f"$ {' '.join(command)}")
    subprocess.run(command, cwd=cwd, check=True)


def build_wheel(source: Path, outdir: Path, python: str, pins: tuple[str, ...]) -> Path:
    venv = outdir / f"buildenv_{python.replace('.', '')}"
    run(["uv", "venv", "--python", python, "--seed", str(venv), "--quiet"])
    interpreter = venv / "bin" / "python"
    run([str(interpreter), "-m", "pip", "install", "-q", "--disable-pip-version-check", *pins, "build"])
    run([str(interpreter), "-m", "build", "--wheel", "--no-isolation", "--outdir", str(outdir), str(source)])
    wheels = sorted(outdir.glob("*.whl"))
    if not wheels:
        raise SystemExit(f"no wheel produced in {outdir}")
    return wheels[-1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the v0.36a-alpha migration audit.")
    parser.add_argument("--experiment", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args(argv)

    out = Path(args.output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    config_path = REPO_ROOT / "configs/alpha_migration" / f"{args.experiment}.json"
    if not config_path.is_file():
        raise SystemExit(f"unknown experiment config: {config_path}")

    # --- legacy side -------------------------------------------------------
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
        str(legacy_python), "-m", "pip", "install", "-q", "--disable-pip-version-check",
        *LEGACY_RUNTIME_PINS, f"{legacy_wheel}[downstream]",
    ])

    legacy_bundles = out / "legacy_bundles"
    # cwd is the legacy worktree so provenance describes v0.22.0.
    run([
        str(legacy_python), str(REPO_ROOT / "scripts/legacy_exporter.py"),
        "--config", str(config_path),
        "--output-dir", str(legacy_bundles),
        "--wheel", str(legacy_wheel),
    ], cwd=legacy_src)

    # --- modern side -------------------------------------------------------
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

    modern_bundles = out / "modern_bundles"
    run([
        str(modern_python), str(REPO_ROOT / "scripts/modern_exporter.py"),
        "--config", str(config_path),
        "--output-dir", str(modern_bundles),
        "--wheel", str(modern_wheel),
    ], cwd=REPO_ROOT)

    # --- comparison (third process, modern interpreter) --------------------
    compare_script = out / "_compare.py"
    compare_script.write_text(
        "import json, sys\n"
        "from pathlib import Path\n"
        "from pdelie.audit import compare_pipeline_stages, "
        "PipelineMigrationComparisonPolicy, StagePolicy\n"
        "def _policy(spec):\n"
        "    tol = spec['default_tolerance_numeric']\n"
        "    inv = spec.get('qualitative_invariants', {})\n"
        "    over = spec.get('stage_overrides', {})\n"
        "    stages = {}\n"
        "    for item in config['stages']:\n"
        "        sid, cls = item['stage_id'], item['comparison_class']\n"
        "        kw = dict(over.get(sid, {}))\n"
        "        if cls == 'tolerance_numeric':\n"
        "            kw.setdefault('rtol', tol['rtol']); kw.setdefault('atol', tol['atol'])\n"
        "        if cls == 'qualitative_invariant':\n"
        "            kw.setdefault('invariant', inv.get(sid, 'sign'))\n"
        "        stages[sid] = StagePolicy(stage_id=sid, **kw)\n"
        "    return PipelineMigrationComparisonPolicy("
        "policy_id=spec['policy_id'], stage_policies=stages)\n"
        "config = json.loads(Path(sys.argv[1]).read_text())\n"
        "report = compare_pipeline_stages(\n"
        "    legacy_bundle_dir=Path(sys.argv[2]),\n"
        "    modern_bundle_dir=Path(sys.argv[3]),\n"
        "    experiment_config=config,\n"
        "    comparison_policy=_policy(json.loads("
        "Path(sys.argv[5]).read_text())),\n"
        ")\n"
        "Path(sys.argv[4]).write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))\n"
        "print('label counts:', json.dumps(report['label_counts'], sort_keys=True))\n",
        encoding="utf-8",
    )
    report_path = out / f"migration_report_{args.experiment}.json"
    run([
        str(modern_python), str(compare_script), str(config_path),
        str(legacy_bundles), str(modern_bundles), str(report_path),
        str(REPO_ROOT / "configs/alpha_migration/comparison_policy.json"),
    ])

    print(f"\nreport written to {report_path}")
    print(json.dumps(json.loads(report_path.read_text())["label_counts"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

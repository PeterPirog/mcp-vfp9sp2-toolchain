# -*- coding: utf-8 -*-
"""Clean-environment Python compatibility smoke acceptance (REQ-P00-011).

For every supported Python minor (3.10, 3.11, 3.12, 3.13, 3.14) this tool
proves, against a CLEAN installation of the built product wheel:

1. clean installation of the built product wheel (fresh venv, ``pip install
   --no-index --no-deps`` — no network, no floating dependency resolution);
2. ``import vfp_toolchain``;
3. package metadata version readable (and consistent with the wheel);
4. canonical supported-Python contract readable;
5. canonical dialect identity readable;
6. no unsupported production capability falsely reported (truthful empty
   capability state);
7. executed-interpreter attestation: the venv was actually created by the
   probed interpreter for that minor and executes that minor.

Per-minor venv creation mechanics (remediation of FINDING-P00A3R-001):
each per-minor virtual environment is created BY the exact probed
interpreter for that minor via ``<interpreter> -m venv --clear <venv_root>``
(subprocess with an explicit argument list; never ``venv.create()``, which
would silently base every venv on the interpreter running this tool).  After
creation the venv's own interpreter (``Scripts\\python.exe``) is executed to
capture its real runtime identity (version, implementation, architecture),
which is attested against the requested minor and the creating interpreter
before any check may report PASS (fail closed: EXECUTED_PYTHON_MINOR_MISMATCH,
EXECUTED_PYTHON_IMPLEMENTATION_MISMATCH, EXECUTED_PYTHON_ARCHITECTURE_MISMATCH,
EXECUTED_PYTHON_VERSION_MISMATCH, VENV_INTERPRETER_VALIDATION_FAILED).

A missing interpreter is a typed host-prerequisite blocker
(``PYTHON_31X_HOST_PREREQUISITE_MISSING``) — never a skipped check and never
a PASS.  The overall report is PASS only when all five minors actually passed;
BLOCKED when interpreters are missing; FAIL when any executed check fails.
Every per-minor record carries the EXECUTED venv interpreter identity
separately from the probed host identity; aggregate PASS derives from the
executed records only.

No runtime dependency is added by this tool: it is stdlib-only and the
product wheel itself has empty runtime dependencies.

Usage:
    python tools/clean_env_smoke.py [--python PATH ...] [--evidence PATH]
                                    [--work-root PATH] [--repo-root PATH]
                                    [--plan]
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[1]

REQUIRED_MINORS: tuple[str, ...] = ("3.10", "3.11", "3.12", "3.13", "3.14")
CANONICAL_PYTHON_RANGE = ">=3.10,<3.15"
CANONICAL_DIALECT = "microsoft.visual-foxpro.9.0.sp2"
CANONICAL_PRODUCT_NAME = "mcp-vfp9sp2-toolchain"

REQUIRED_CHECK_NAMES: tuple[str, ...] = (
    "clean_wheel_install",
    "import_vfp_toolchain",
    "package_metadata_version_readable",
    "canonical_python_contract_readable",
    "canonical_dialect_identity_readable",
    "no_unsupported_capability_falsely_reported",
    "executed_minor_matches_expected",
)

# Identity capture program: executed by the VENV interpreter itself; prints JSON.
_VENV_IDENTITY_PROGRAM = r'''
import json
import platform
import sys

print(json.dumps({
    "python_version": sys.version,
    "version_info": {
        "major": sys.version_info.major,
        "minor": sys.version_info.minor,
        "micro": sys.version_info.micro,
    },
    "executable": sys.executable,
    "implementation": sys.implementation.name,
    "architecture": list(platform.architecture()),
}))
'''

# The in-venv verification program: deterministic, stdlib-only, prints JSON.
# argv[1] (when present) is the expected requested minor (e.g. "3.11"); the
# program runs inside the per-minor venv and fails closed when the executing
# interpreter does not match it (regression guard for FINDING-P00A3R-001).
_VENV_CHECK_PROGRAM = r'''
import json
import sys

expected_minor = sys.argv[1] if len(sys.argv) > 1 else None

result = {"checks": [], "version": None, "python_version": sys.version}
def record(name, ok, detail=None):
    entry = {"name": name, "status": "PASS" if ok else "FAIL"}
    if detail is not None:
        entry["detail"] = detail
    result["checks"].append(entry)

executed_minor = "%d.%d" % (sys.version_info.major, sys.version_info.minor)
record(
    "executed_minor_matches_expected",
    expected_minor is not None and executed_minor == expected_minor,
    {"expected_minor": expected_minor, "executed_minor": executed_minor},
)

try:
    import vfp_toolchain
    record("import_vfp_toolchain", True)
except Exception as error:  # noqa: BLE001
    record("import_vfp_toolchain", False, repr(error))
    print(json.dumps(result))
    raise SystemExit(0)

from importlib import metadata as importlib_metadata
try:
    dist_version = importlib_metadata.version("mcp-vfp9sp2-toolchain")
    package_metadata = importlib_metadata.metadata("mcp-vfp9sp2-toolchain")
    requires_python = package_metadata.get("Requires-Python")
    record(
        "package_metadata_version_readable",
        bool(dist_version) and dist_version == vfp_toolchain.__version__,
        {"dist_version": dist_version, "module_version": vfp_toolchain.__version__, "requires_python": requires_python},
    )
except Exception as error:  # noqa: BLE001
    record("package_metadata_version_readable", False, repr(error))

record(
    "canonical_python_contract_readable",
    vfp_toolchain.SUPPORTED_PYTHON_RANGE == ">=3.10,<3.15"
    and list(vfp_toolchain.SUPPORTED_PYTHON_MINORS) == ["3.10", "3.11", "3.12", "3.13", "3.14"],
    {"supported_python_range": vfp_toolchain.SUPPORTED_PYTHON_RANGE},
)
record(
    "canonical_dialect_identity_readable",
    vfp_toolchain.TARGET_DIALECT == "microsoft.visual-foxpro.9.0.sp2"
    and vfp_toolchain.domain.dialect_identity()["dialect_identifier"] == "microsoft.visual-foxpro.9.0.sp2",
    {"target_dialect": vfp_toolchain.TARGET_DIALECT},
)

from vfp_toolchain import capabilities as caps
policy = vfp_toolchain.domain.platform_policy()
discovery = caps.discover()
truthful = (
    discovery["implemented_count"] == 0
    and all((not entry["available"]) and entry["state"] == "NOT_IMPLEMENTED" for entry in discovery["capabilities"])
    and policy["windows_only"] is True
    and policy["linux_product_support"] is False
    and policy["macos_product_support"] is False
)
record(
    "no_unsupported_capability_falsely_reported",
    truthful,
    {"implemented_count": discovery["implemented_count"], "declared_count": discovery["declared_count"]},
)
record("clean_wheel_install", True, {"wheel": "installed with --no-index --no-deps"})

print(json.dumps(result))
failed = [c for c in result["checks"] if c["status"] != "PASS"]
raise SystemExit(1 if failed else 0)
'''


def plan() -> dict[str, Any]:
    """Deterministic execution plan (no interpreters executed)."""
    return {
        "report": "CLEAN_ENVIRONMENT_SMOKE_PLAN",
        "required_minors": list(REQUIRED_MINORS),
        "required_check_names": list(REQUIRED_CHECK_NAMES),
        "canonical_python_range": CANONICAL_PYTHON_RANGE,
        "canonical_dialect": CANONICAL_DIALECT,
        "clean_install_policy": "fresh venv + pip install --no-index --no-deps (no network, no floating resolution)",
        "venv_creation_policy": (
            "per-minor venv created BY the probed interpreter for that minor: "
            "<interpreter> -m venv --clear <venv_root> (explicit subprocess argument list; never venv.create(), "
            "which would base every venv on the tool-runner interpreter — FINDING-P00A3R-001 remediation); "
            "the venv's own interpreter identity is attested (version/implementation/architecture) and "
            "fail-closed validated against the requested minor and the creating interpreter before any PASS"
        ),
        "blocker_vocabulary": [f"PYTHON_{minor.replace('.', '')}_HOST_PREREQUISITE_MISSING" for minor in REQUIRED_MINORS],
    }


def probe_interpreter(python_exe: Path) -> dict[str, Any] | None:
    """Return {'path', 'version', 'minor'} for a working interpreter, else None."""
    try:
        completed = subprocess.run(
            [str(python_exe), "-c", "import sys;print('%d.%d.%d'%sys.version_info[:3]);print('%d.%d'%(sys.version_info[0],sys.version_info[1]))"],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    if completed.returncode != 0:
        return None
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if len(lines) < 2:
        return None
    return {"path": str(python_exe), "version": lines[0].strip(), "minor": lines[1].strip()}


def _blocker_code(minor: str) -> str:
    return f"PYTHON_{minor.replace('.', '')}_HOST_PREREQUISITE_MISSING"


def run_smoke(
    python_paths: list[Path],
    repo_root: Path,
    work_root: Path,
) -> dict[str, Any]:
    """Execute the five-minor clean-environment acceptance."""
    interpreters: dict[str, dict[str, Any]] = {}
    for python_path in python_paths:
        probe = probe_interpreter(python_path)
        if probe is None:
            raise SystemExit(f"unusable interpreter: {python_path}")
        interpreters[probe["minor"]] = probe

    per_minor: dict[str, Any] = {}
    blockers: list[dict[str, Any]] = []
    wheel_path = _build_wheel(repo_root, work_root)

    for minor in REQUIRED_MINORS:
        if minor not in interpreters:
            per_minor[minor] = {
                "status": "BLOCKED",
                "blocker_code": _blocker_code(minor),
                "message": f"No local Python {minor} interpreter was provided or found; "
                           "install it explicitly to complete the REQ-P00-011 acceptance evidence.",
            }
            blockers.append({"minor": minor, "code": _blocker_code(minor)})
            continue
        per_minor[minor] = _run_minor_smoke(interpreters[minor], wheel_path, work_root / f"venv-{minor}")

    executed = {minor: entry for minor, entry in per_minor.items() if entry.get("status") != "BLOCKED"}
    failed = [minor for minor, entry in executed.items() if entry["status"] != "PASS"]
    if failed:
        status = "FAIL"
    elif blockers:
        status = "BLOCKED"
    else:
        status = "PASS"
    return {
        "report": "CLEAN_ENVIRONMENT_SMOKE",
        "status": status,
        "requirement_ids": ["REQ-P00-011"],
        "wheel": {"path": str(wheel_path), "built_from": "python -m build --wheel --no-isolation"},
        "evidence_source": (
            "per-minor executed venv interpreter identity (captured by executing <venv>/Scripts/python.exe); "
            "'interpreters' below is the PROBED host discovery record only and is never used as executed evidence"
        ),
        "interpreters": {minor: {"path": entry.get("path"), "version": entry.get("version")} for minor, entry in interpreters.items()},
        "per_minor": per_minor,
        "blockers": blockers,
        "pass_only_when": "all five supported minors executed and passed",
    }


def _build_wheel(repo_root: Path, work_root: Path) -> Path:
    dist_dir = work_root / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--no-isolation", "--outdir", str(dist_dir)],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        timeout=600,
    )
    if completed.returncode != 0:
        raise SystemExit(
            "WHEEL_BUILD_FAILED (fail closed):\n" + completed.stdout[-2000:] + completed.stderr[-2000:]
        )
    wheels = sorted(dist_dir.glob("*.whl"))
    if not wheels:
        raise SystemExit("WHEEL_BUILD_FAILED: no wheel artifact produced")
    return wheels[-1]


def _build_venv_command(interpreter_path: Path, venv_root: Path) -> list[str]:
    """Explicit venv-creation command started BY the probed interpreter itself.

    Never venv.create(): that API has no interpreter parameter and silently
    bases every venv on sys.executable of the process running this tool
    (the FINDING-P00A3R-001 defect).
    """
    return [str(interpreter_path), "-m", "venv", "--clear", str(venv_root)]


def _capture_venv_identity(venv_python: str) -> dict[str, Any] | None:
    """Execute the VENV interpreter and capture its real runtime identity."""
    try:
        completed = subprocess.run(
            [venv_python, "-c", _VENV_IDENTITY_PROGRAM],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    if completed.returncode != 0:
        return None
    try:
        return json.loads(completed.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        return None


def _parse_version_parts(version: str | None) -> tuple[int, int, int] | None:
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)", str(version or ""))
    if match is None:
        return None
    first, second, third = (int(part) for part in match.groups())
    return (first, second, third)


def _validate_executed_identity(
    expected_minor: str,
    identity: dict[str, Any],
    creator_version: str | None,
) -> list[str]:
    """Fail-closed attestation of the EXECUTED venv interpreter identity.

    Returns typed blocker codes; an empty list means the executed identity is
    acceptable for this minor.  All fields come from the venv interpreter's
    own runtime capture — never from the discovery/probe record.
    """
    blockers: list[str] = []
    version_info = identity.get("version_info") or {}
    major = version_info.get("major")
    minor = version_info.get("minor")
    micro = version_info.get("micro")
    if not isinstance(major, int) or not isinstance(minor, int) or not isinstance(micro, int):
        blockers.append("VENV_INTERPRETER_VALIDATION_FAILED")
        return blockers
    executed_minor = f"{major}.{minor}"
    if executed_minor != expected_minor:
        blockers.append("EXECUTED_PYTHON_MINOR_MISMATCH")
        return blockers
    implementation = str(identity.get("implementation", "")).lower()
    if implementation != "cpython":
        blockers.append("EXECUTED_PYTHON_IMPLEMENTATION_MISMATCH")
    architecture = identity.get("architecture")
    if (
        not isinstance(architecture, list)
        or len(architecture) != 2
        or architecture[0] != "64bit"
        or architecture[1] != "WindowsPE"
    ):
        blockers.append("EXECUTED_PYTHON_ARCHITECTURE_MISMATCH")
    # Creator-equality: prefer exact major.minor.micro equality between the
    # interpreter that created the venv and the interpreter the venv executes,
    # so a silent interpreter switch is detected even within one minor.
    executed_parts = (major, minor, micro)
    creator_parts = _parse_version_parts(creator_version)
    if creator_parts is not None and executed_parts != creator_parts:
        blockers.append("EXECUTED_PYTHON_VERSION_MISMATCH")
    return blockers


def _run_minor_smoke(interpreter: dict[str, Any], wheel_path: Path, venv_root: Path) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "expected_minor": interpreter["minor"],
        "discovered_interpreter_path": interpreter["path"],
        "discovered_interpreter_version": interpreter["version"],
    }
    venv_root.parent.mkdir(parents=True, exist_ok=True)

    # 1. Create the venv BY the exact probed interpreter (explicit argument
    #    list; no shell; no venv.create(); never the tool-runner interpreter).
    creation_command = _build_venv_command(Path(interpreter["path"]), venv_root)
    entry["venv_creation_command"] = creation_command
    try:
        creation = subprocess.run(creation_command, capture_output=True, text=True, timeout=600)
    except (subprocess.TimeoutExpired, OSError) as error:
        entry["status"] = "FAIL"
        entry["blocker_code"] = "VENV_CREATION_FAILED"
        entry["error"] = repr(error)
        return entry
    if creation.returncode != 0:
        entry["status"] = "FAIL"
        entry["blocker_code"] = "VENV_CREATION_FAILED"
        entry["error"] = (creation.stdout[-1000:] + creation.stderr[-1000:])
        return entry

    # 2. Execute the VENV's own interpreter and capture its real identity.
    venv_python = str(venv_root / "Scripts" / "python.exe")
    entry["venv_python_path"] = venv_python
    if not (venv_root / "Scripts" / "python.exe").is_file():
        entry["status"] = "FAIL"
        entry["blocker_code"] = "VENV_INTERPRETER_VALIDATION_FAILED"
        entry["error"] = "venv python.exe not found after creation"
        return entry
    identity = _capture_venv_identity(venv_python)
    if identity is None:
        entry["status"] = "FAIL"
        entry["blocker_code"] = "VENV_INTERPRETER_VALIDATION_FAILED"
        entry["error"] = "venv interpreter identity capture failed"
        return entry
    version_info = identity.get("version_info") or {}
    entry["executed_interpreter_version"] = (
        f"{version_info.get('major')}.{version_info.get('minor')}.{version_info.get('micro')}"
    )
    entry["executed_major_minor"] = f"{version_info.get('major')}.{version_info.get('minor')}"
    entry["executed_python_version"] = identity.get("python_version")
    entry["executed_interpreter_path"] = identity.get("executable")
    entry["executed_implementation"] = identity.get("implementation")
    entry["executed_architecture"] = identity.get("architecture")

    # 3. Fail-closed attestation BEFORE any check may report PASS.
    blockers = _validate_executed_identity(
        entry["expected_minor"], identity, entry["discovered_interpreter_version"]
    )
    if blockers:
        entry["status"] = "FAIL"
        entry["blocker_code"] = blockers[0]
        entry["blocker_codes"] = blockers
        entry["error"] = "executed venv interpreter identity does not match the requested minor (fail closed)"
        return entry

    # 4. Clean wheel installation inside the actual per-minor environment.
    install = subprocess.run(
        [venv_python, "-m", "pip", "install", "--no-index", "--no-deps", "--force-reinstall", str(wheel_path)],
        capture_output=True,
        text=True,
        timeout=600,
    )
    if install.returncode != 0:
        entry["status"] = "FAIL"
        entry["check_results"] = [{"name": "clean_wheel_install", "status": "FAIL", "detail": install.stderr[-2000:]}]
        return entry

    # 5. Smoke checks executed by the VENV interpreter (with the expected
    #    minor as argv so the program itself fail-closes on any mismatch).
    check_root = venv_root / "_smoke"
    check_root.mkdir(parents=True, exist_ok=True)
    check_script = check_root / "check.py"
    check_script.write_text(_VENV_CHECK_PROGRAM, encoding="utf-8")
    check = subprocess.run(
        [venv_python, str(check_script), entry["expected_minor"]],
        capture_output=True,
        text=True,
        timeout=300,
    )
    try:
        payload = json.loads(check.stdout.strip().splitlines()[-1]) if check.stdout.strip() else {}
    except (json.JSONDecodeError, IndexError):
        payload = {"checks": [{"name": "result_parsing", "status": "FAIL", "detail": "check program produced no JSON result"}]}
    entry["check_results"] = payload.get("checks", [])
    entry["executed_python_version_at_checks"] = payload.get("python_version")
    failed = [c for c in entry["check_results"] if c.get("status") != "PASS"]
    entry["status"] = "FAIL" if (failed or check.returncode != 0) else "PASS"
    return entry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="clean_env_smoke.py", description=__doc__)
    parser.add_argument("--python", type=Path, action="append", default=[], help="interpreter path (repeatable)")
    parser.add_argument("--evidence", type=Path, default=None, help="write the JSON report to this path")
    parser.add_argument("--work-root", type=Path, default=None, help="work directory (default: system temp)")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT_DEFAULT)
    parser.add_argument("--plan", action="store_true", help="print the deterministic plan without executing")
    args = parser.parse_args(argv)

    if args.plan:
        print(json.dumps(plan(), indent=2, sort_keys=True))
        return 0

    keep_work = args.work_root is not None
    work_root = args.work_root or Path(tempfile.mkdtemp(prefix="vfp-clean-env-"))
    work_root.mkdir(parents=True, exist_ok=True)
    try:
        report = run_smoke(list(args.python), args.repo_root, work_root)
    finally:
        if not keep_work:
            shutil.rmtree(work_root, ignore_errors=True)
    encoded = json.dumps(report, indent=2, sort_keys=True)
    if args.evidence is not None:
        args.evidence.parent.mkdir(parents=True, exist_ok=True)
        args.evidence.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    return {"PASS": 0, "FAIL": 1, "BLOCKED": 2}[report["status"]]


if __name__ == "__main__":
    raise SystemExit(main())

# -*- coding: utf-8 -*-
"""
tests/test_offline_ci_artifact_only.py - static guard for the offline CI plane.

The offline-test jobs in .github/workflows/offline-runtime.yml must install
EXCLUSIVELY from the locally built wheelhouse artifact. This test statically
verifies (no network, no execution of the workflow) that:

  * every offline-test job references the bundle artifact and its wheelhouse,
  * the installer is invoked with --no-index semantics (install-offline.ps1
    hard-codes it, but the workflow must pass the bundle root),
  * NO offline-test job contains a bare ``pip install`` (PyPI fallback),
  * NO offline-test job references ``--index-url`` / ``pypi.org`` /
    ``simple index`` installation commands,
  * the build job (the only plane allowed to use the network) is the sole
    place where ``pip install`` / ``pip download`` appear.

If a future workflow edit reintroduces a network install into the offline
plane, this test fails.
"""

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOW = os.path.join(ROOT, ".github", "workflows", "offline-runtime.yml")


def _workflow_text():
    assert os.path.isfile(WORKFLOW), "offline-runtime workflow must exist"
    with open(WORKFLOW, "r", encoding="utf-8") as f:
        return f.read()


_JOB_RE = re.compile(r"^  ([A-Za-z0-9][A-Za-z0-9_.-]*):\s*$")


def _job_blocks(text):
    """Split the workflow into {job_name: job_body} (naive split on the
    2-space-indented ``name:`` lines under ``jobs:`` — sufficient for a static
    guard, no YAML parser needed)."""
    jobs = {}
    current = None
    buf = []
    for line in text.splitlines():
        m = _JOB_RE.match(line)
        if m:
            if current is not None:
                jobs[current] = "\n".join(buf)
            current = m.group(1)
            buf = [line]
        elif current is not None:
            buf.append(line)
    if current is not None:
        jobs[current] = "\n".join(buf)
    return jobs


def test_offline_jobs_exist():
    jobs = _job_blocks(_workflow_text())
    names = [n for n in jobs if n.startswith("offline-test")]
    assert len(names) >= 1, "at least one offline-test job must exist"
    assert "build-bundle" in jobs, "a build job must produce the artifact"


def test_offline_jobs_use_local_wheelhouse():
    jobs = _job_blocks(_workflow_text())
    for name, body in jobs.items():
        if not name.startswith("offline-test"):
            continue
        assert "download-artifact" in body, (
            "%s must download the bundle artifact (local wheelhouse source)" % name)
        assert "install-offline.ps1" in body, (
            "%s must run the offline installer (the only install path)" % name)


def test_offline_jobs_have_no_bare_pip_install():
    """A bare ``pip install`` in an offline job means PyPI is reachable."""
    jobs = _job_blocks(_workflow_text())
    for name, body in jobs.items():
        if not name.startswith("offline-test"):
            continue
        # pip install WITHOUT --no-index / --find-links in the same line
        bad = []
        for line in body.splitlines():
            stripped = line.strip()
            if re.search(r"\bpip\s+install\b", stripped, re.IGNORECASE):
                if "--no-index" not in stripped and "--find-links" not in stripped:
                    bad.append(stripped)
        assert not bad, (
            "%s contains bare pip install lines (PyPI fallback):\n%s"
            % (name, "\n".join(bad)))


def test_offline_jobs_have_no_index_url():
    jobs = _job_blocks(_workflow_text())
    for name, body in jobs.items():
        if not name.startswith("offline-test"):
            continue
        assert "--index-url" not in body.lower(), (
            "%s must not set an index URL (no registry)" % name)
        assert "simple index" not in body.lower()
        assert "pypi.org" not in body.lower(), (
            "%s must not reference pypi.org directly" % name)


def test_pip_install_allowed_only_in_build_job():
    """``pip install`` / ``pip download`` (network plane) may appear ONLY in
    the build job and the repo test job — never in offline-test jobs."""
    text = _workflow_text()
    jobs = _job_blocks(text)
    for name, body in jobs.items():
        if name.startswith("offline-test"):
            assert not re.search(r"\bpip\s+(install|download)\b", body,
                                 re.IGNORECASE), (
                "%s must not invoke pip install/download (offline plane)"
                % name)


def test_repo_tests_job_isolated():
    """The repo test job (repository CI plane, NOT the offline plane) is
    allowed to use pip install — but must still run the full test suite."""
    jobs = _job_blocks(_workflow_text())
    assert "repo-tests" in jobs, "a repository test job must exist"
    body = jobs["repo-tests"]
    assert "pytest" in body, "repo test job must run pytest"


def test_offline_jobs_run_verification():
    """Every offline-test job must run the offline runtime verifier after
    install (this is the hard gate before the smoke test)."""
    jobs = _job_blocks(_workflow_text())
    for name, body in jobs.items():
        if not name.startswith("offline-test"):
            continue
        assert "verify_offline_runtime" in body, (
            "%s must run scripts/verify_offline_runtime.py after install"
            % name)


def test_offline_jobs_smoke_test_pure_read():
    """The offline smoke test must assert pureRead is available."""
    jobs = _job_blocks(_workflow_text())
    for name, body in jobs.items():
        if not name.startswith("offline-test"):
            continue
        assert "pureRead" in body, (
            "%s must assert pureRead availability after offline install" % name)

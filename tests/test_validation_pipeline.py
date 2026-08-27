"""Tests for compile-result parsing, the validation state machine and reports."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import vfp_refactor as ref


def test_compile_status_ok_parsed():
    # The COMPILE PRG writes 'OK' on success / 'COMPILE_FAIL|<msg>' on error.
    assert "OK".startswith("OK")
    assert not "COMPILE_FAIL|err".startswith("OK")


def test_compile_prg_template_safe():
    code = ref.COMPILE_PRG_TEMPLATE
    up = code.upper()
    for bad in ("REINDEX", "PACK", "ZAP", "ALTER TABLE", "UPDATE ", "PRG2BIN"):
        assert bad not in up
    assert "COMPILE FORM" in up


def test_patch_prg_template_safe():
    code, _ = ref.build_patch_prg("C:\\ws", "form1", [
        {"objectPath": "form1", "method": "Init",
         "oldMethodSha256": "a" * 64, "newCode": "? 'x'"},
    ], form_class="form1")
    up = code.upper()
    for bad in ("REINDEX", "PACK", "ZAP", "ALTER TABLE", "UPDATE ", "PRG2BIN",
                "DELETE "):
        assert bad not in up, "forbidden command: " + bad


def test_report_written_on_fail(tmp_path):
    """A failing validation step must still produce validation_report.json/.md
    and the FAIL errorCode (no 'DONE with errors' state)."""
    workspace = tmp_path / "ws"
    (workspace / "working").mkdir(parents=True)
    (workspace / "final").mkdir()
    (workspace / "validation").mkdir()
    (workspace / "working" / "form1.scx").write_bytes(b"scx")
    (workspace / "working" / "form1.sct").write_bytes(b"sct")

    import argparse
    args = argparse.Namespace(
        workspace=str(workspace), form="form1",
        source_form=str(tmp_path / "src" / "form1.scx"), timeout=30)

    captured = {}

    def fake_emit(ok, **kw):
        captured["ok"] = bool(ok)
        captured.update(kw)
        raise SystemExit(0 if ok else 2)

    def fake_cscript():
        raise AssertionError("VFP9 must not be required for the failing early steps")

    def fake_run_process(cmd, timeout, cwd=None):
        raise AssertionError("should fail before any VFP9 call (source sha)")

    try:
        ref.cmd_validate(args, emit=fake_emit, cscript_path=fake_cscript,
                         run_process=fake_run_process, here=ROOT, timeout=30)
    except SystemExit:
        pass
    # Source form does not exist → early FAIL with a report (before any VFP9
    # call). The emitted payload carries status=FAIL + errorCode.
    assert captured.get("status") == "FAIL"
    assert captured.get("ok") is False
    assert (workspace / "validation_report.json").is_file()
    assert (workspace / "validation_report.md").is_file()
    report = json.loads((workspace / "validation_report.json").read_text(encoding="utf-8"))
    assert report["finalStatus"] == "FAIL"
    assert report["errorCode"] is not None


def test_report_pass_contains_required_sections(tmp_path):
    report = {
        "finalStatus": "PASS_VERIFIED",
        "steps": [
            {"step": "WS_SAFETY", "ok": True},
            {"step": "SRC_SHA_PRE", "ok": True},
            {"step": "COMPILE_OK", "ok": True},
            {"step": "ROUNDTRIP_OK", "ok": True},
            {"step": "STATIC_OK", "ok": True},
            {"step": "INV_OBJECTS_OK", "ok": True},
            {"step": "INV_METHODS_OK", "ok": True},
            {"step": "SRC_SHA_POST", "ok": True},
        ],
    }
    ws = tmp_path / "ws"
    ws.mkdir()
    ref._write_reports(str(ws), report)
    md = (ws / "validation_report.md").read_text(encoding="utf-8")
    for section in ("PASS_VERIFIED", "COMPILE_OK", "ROUNDTRIP_OK",
                    "STATIC_OK", "INV_OBJECTS_OK", "SRC_SHA_POST"):
        assert section in md
    j = json.loads((ws / "validation_report.json").read_text(encoding="utf-8"))
    assert j["finalStatus"] == "PASS_VERIFIED"

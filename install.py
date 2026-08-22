#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
install.py - One-step installer for the VFP integration toolchain.

Usage:
    py install.py [--toolchain-dir PATH] [--opencode-config PATH] [--foxbin2prg-dir PATH]

What it does:
1. Sets VFP_TOOLCHAIN_HOME in the current shell (and optionally in PATH).
2. Symlinks (or copies on Windows) tools/vfp.ts -> ~/.config/opencode/tools/vfp.ts
3. Symlinks agents/vfp-analyst.md -> ~/.config/opencode/agents/vfp-analyst.md
4. Resolves FoxBin2Prg directory: env var, provided path, or checks default location.
5. Verifies vfp9.exe is available.
6. Tests the toolchain with vfp_status.

Cross-platform: works on Windows (PowerShell symlinks via mklink) and
Linux/macOS (symlink).  On Windows without admin privileges, falls back
to file copy.
"""

import argparse
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def is_windows():
    return os.name == "nt"


def get_default_opencode_config():
    home = os.environ.get("USERPROFILE") or os.environ.get("HOME") or ""
    if is_windows():
        return os.path.join(home, ".config", "opencode")
    return os.path.expanduser("~/.config/opencode")


def symlink_or_copy(src, dst):
    """Create symlink, or copy if symlinks fail (e.g. Windows without privilege)."""
    if os.path.exists(dst) or os.path.islink(dst):
        os.remove(dst)
    try:
        os.symlink(src, dst)
        return "symlink"
    except (OSError, NotImplementedError):
        shutil.copy2(src, dst)
        return "copy"


def find_foxbin2prg(explicit_dir):
    candidates = []
    if explicit_dir:
        candidates.append(explicit_dir)
    env_dir = os.environ.get("VFP_FOXBIN2PRG_DIR")
    if env_dir:
        candidates.append(env_dir)
    home = os.environ.get("USERPROFILE") or os.environ.get("HOME") or ""
    candidates.append(os.path.join(home, ".config", "opencode", "tools", "foxbin2prg"))
    candidates.append(os.path.join(HERE, "tools", "foxbin2prg"))
    for c in candidates:
        prg = os.path.join(c, "foxbin2prg.prg")
        if os.path.isfile(prg):
            return c
    return None


def find_vfp9():
    env = os.environ.get("VFP9_EXE")
    if env and os.path.isfile(env):
        return env
    default = r"C:\Program Files (x86)\Microsoft Visual FoxPro 9\vfp9.exe"
    if os.path.isfile(default):
        return default
    return None


def main():
    ap = argparse.ArgumentParser(prog="install")
    ap.add_argument("--toolchain-dir", default=HERE,
                    help="Root directory of the VFP toolchain (default: this script's dir)")
    ap.add_argument("--opencode-config", default=None,
                    help="OpenCode config directory (default: ~/.config/opencode)")
    ap.add_argument("--foxbin2prg-dir", default=None,
                    help="Directory containing foxbin2prg.prg")
    ap.add_argument("--no-symlink", action="store_true",
                    help="Copy files instead of symlinking (useful on Windows without admin)")
    ap.add_argument("--no-verify", dest="verify", action="store_false",
                    help="Skip post-install verification")
    ap.add_argument("--verify", dest="verify", action="store_true",
                    help="Run vfp_status to verify after install (default)")
    ap.set_defaults(verify=True)
    a = ap.parse_args()

    toolchain = os.path.abspath(a.toolchain_dir)
    opencod = os.path.abspath(a.opencode_config or get_default_opencode_config())

    print("=" * 60)
    print("VFP Integration Toolchain Installer")
    print("=" * 60)
    print()
    print("Toolchain root:", toolchain)
    print("OpenCode config:", opencod)
    print()

    # Validate toolchain
    driver = os.path.join(toolchain, "vfp_driver.py")
    if not os.path.isfile(driver):
        print("ERROR: vfp_driver.py not found at", driver)
        sys.exit(1)

    # 1. FoxBin2Prg
    fbdir = find_foxbin2prg(a.foxbin2prg_dir)
    if fbdir:
        print("[OK] FoxBin2Prg found: %s" % fbdir)
    else:
        print("[WARN] FoxBin2Prg NOT found.")
        print("       Download from: https://github.com/fdbozzo/foxbin2prg")
        print("       Place foxbin2prg.prg (and .fxv) in one of:")
        for c in [os.path.join(opencod, "tools", "foxbin2prg"), os.path.join(toolchain, "tools", "foxbin2prg")]:
            print("         -", c)
        print("       Or set environment variable: VFP_FOXBIN2PRG_DIR")
        print()

    # 2. VFP9
    vfp9 = find_vfp9()
    if vfp9:
        print("[OK] VFP9 found: %s" % vfp9)
    else:
        print("[WARN] VFP9 not found at default location.")
        print("       Set VFP9_EXE environment variable to vfp9.exe path.")
        print()

    # 3. Symlink tools
    tools_dst = os.path.join(opencod, "tools")
    os.makedirs(tools_dst, exist_ok=True)
    ts_src = os.path.join(toolchain, "tools", "vfp.ts")
    ts_dst = os.path.join(tools_dst, "vfp.ts")
    if a.no_symlink:
        shutil.copy2(ts_src, ts_dst)
        print("[OK] Copied: %s -> %s" % (ts_src, ts_dst))
    else:
        method = symlink_or_copy(ts_src, ts_dst)
        print("[OK] Linked (%s): %s -> %s" % (method, ts_src, ts_dst))

    # 4. Symlink agents
    agents_dst = os.path.join(opencod, "agents")
    os.makedirs(agents_dst, exist_ok=True)
    agent_src = os.path.join(toolchain, "agents", "vfp-analyst.md")
    agent_dst = os.path.join(agents_dst, "vfp-analyst.md")
    if a.no_symlink:
        shutil.copy2(agent_src, agent_dst)
        print("[OK] Copied: %s -> %s" % (agent_src, agent_dst))
    else:
        method = symlink_or_copy(agent_src, agent_dst)
        print("[OK] Linked (%s): %s -> %s" % (method, agent_src, agent_dst))

    # 5. Set VFP_TOOLCHAIN_HOME env (instructions)
    print()
    print("Environment variable to set:")
    print("  VFP_TOOLCHAIN_HOME = %s" % toolchain)

    # 6. Verify
    if a.verify and vfp9 and fbdir:
        print()
        print("--- Verifying ---")
        env = os.environ.copy()
        env["VFP_TOOLCHAIN_HOME"] = toolchain
        env["VFP_FOXBIN2PRG_DIR"] = fbdir
        prg_path = os.path.join(fbdir, "foxbin2prg.prg")
        result = subprocess.run(
            [sys.executable or "py", driver, "verno", "--prg", prg_path],
            capture_output=True, text=True, env=env, timeout=120
        )
        print(result.stdout.strip())
        if result.stderr:
            print("stderr:", result.stderr.strip())
        if result.returncode == 0:
            print("[OK] Toolchain verified successfully!")
        else:
            print("[FAIL] Verification failed (rc=%d)" % result.returncode)
    elif a.verify and not (vfp9 and fbdir):
        print()
        print("Skipping verification (VFP9 or FoxBin2Prg not found)")

    print()
    print("To complete setup, add to your shell profile:")
    print()
    if is_windows():
        print('  $env:VFP_TOOLCHAIN_HOME = "%s"' % toolchain)
        if fbdir:
            print('  $env:VFP_FOXBIN2PRG_DIR = "%s"' % fbdir)
        if vfp9:
            print('  $env:VFP9_EXE = "%s"' % vfp9)
        print()
        print("  Or for persistent install:")
        print('  [System.Environment]::SetEnvironmentVariable("VFP_TOOLCHAIN_HOME", "%s", "User")' % toolchain)
    else:
        print('  export VFP_TOOLCHAIN_HOME="%s"' % toolchain)
        if fbdir:
            print('  export VFP_FOXBIN2PRG_DIR="%s"' % fbdir)
        if vfp9:
            print('  export VFP9_EXE="%s"' % vfp9)
    print()
    print("Done! Restart OpenCode and use: opencode vfp_status")


if __name__ == "__main__":
    main()

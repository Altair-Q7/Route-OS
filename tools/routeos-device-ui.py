#!/usr/bin/env python3
"""ADB semantic UI probe: --tap LABEL or --expect LABEL. No simulated app data."""
import argparse
import re
import subprocess
import time
import xml.etree.ElementTree as ET


def adb(*args):
    return subprocess.check_output(["adb", *args], text=True, timeout=15)


def nodes():
    output = adb("shell", "uiautomator", "dump", "/sdcard/routeos-ui-test.xml")
    if "dumped to:" not in output:
        raise RuntimeError("Android did not produce a fresh UI hierarchy")
    return ET.fromstring(adb("shell", "cat", "/sdcard/routeos-ui-test.xml")).iter("node")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tap")
    parser.add_argument("--expect")
    parser.add_argument("--timeout", type=float, default=20)
    args = parser.parse_args()
    target = args.tap or args.expect
    deadline = time.monotonic() + args.timeout
    while time.monotonic() < deadline:
        try:
            hierarchy = list(nodes())
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, ET.ParseError, RuntimeError):
            time.sleep(.25)
            continue
        for node in hierarchy:
            label = (node.get("content-desc") or node.get("text", "")).replace("\n", " | ")
            if target and target.lower() not in label.lower():
                continue
            if args.tap and node.get("clickable") != "true":
                continue
            bounds = list(map(int, re.findall(r"\d+", node.get("bounds", ""))))
            if len(bounds) != 4:
                continue
            if not target:
                print(label.replace("\n", " | "), bounds)
                continue
            if args.tap:
                adb("shell", "input", "tap", str((bounds[0]+bounds[2])//2), str((bounds[1]+bounds[3])//2))
            print("PASS:", label.replace("\n", " | "))
            return
        if not target:
            return
        time.sleep(.25)
    raise SystemExit("FAIL: UI did not expose " + target)


if __name__ == "__main__":
    main()

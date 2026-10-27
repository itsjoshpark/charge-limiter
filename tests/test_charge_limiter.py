#!/usr/bin/env python3
import os
import subprocess
import sys
import plistlib

APP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "Charge Limiter.app"))
BCLM_PATH = os.path.join(APP_PATH, "Contents", "Resources", "bclm")
PLIST_PATH = "/Library/LaunchDaemons/com.zackelia.bclm.plist"

def run(cmd, check=True):
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if check and res.returncode != 0:
        raise RuntimeError(f"Command {' '.join(cmd)} failed with exit {res.returncode}:\n{res.stderr}\n{res.stdout}")
    return res

def test():
    print("=" * 60)
    print("RUNNING CHARGE LIMITER & BCLM AUTOMATED TEST SUITE")
    print("=" * 60)

    # 1. Binary existence
    print("[1/12] Checking bclm helper executable exists...")
    assert os.path.isfile(BCLM_PATH), f"bclm not found at {BCLM_PATH}"
    assert os.access(BCLM_PATH, os.X_OK), "bclm is not executable"
    print("  PASS")

    # 2. Version check
    print("[2/12] Checking bclm version...")
    res = run([BCLM_PATH, "--version"])
    version = res.stdout.strip()
    print(f"  bclm version: {version}")
    assert len(version) > 0
    print("  PASS")

    # 3. Read current value
    print("[3/12] Reading current BCLM...")
    res = run([BCLM_PATH, "read"])
    initial_val = int(res.stdout.strip())
    print(f"  Current BCLM: {initial_val}%")
    assert 40 <= initial_val <= 100
    print("  PASS")

    # 4. Non-root write validation
    print("[4/12] Testing non-root write rejection...")
    res = run([BCLM_PATH, "write", "80"], check=False)
    assert res.returncode != 0, "Non-root write should have failed"
    assert "root" in res.stderr.lower() or "root" in res.stdout.lower()
    print("  PASS (rejected non-root as expected)")

    # 5. Out of bounds validation
    print("[5/12] Testing out-of-bounds write rejection (e.g., 39 and 101)...")
    res_low = run(["sudo", BCLM_PATH, "write", "39"], check=False)
    assert res_low.returncode != 0, "Writing 39 should fail validation"
    res_high = run(["sudo", BCLM_PATH, "write", "101"], check=False)
    assert res_high.returncode != 0, "Writing 101 should fail validation"
    print("  PASS (correctly bounded between 40-100)")

    # 6. Valid write (80) and read-back
    print("[6/12] Writing valid limit (80%) and verifying SMC read-back...")
    run(["sudo", BCLM_PATH, "write", "80"])
    res = run([BCLM_PATH, "read"])
    assert res.stdout.strip() == "80", f"Expected 80, got {res.stdout.strip()}"
    print("  PASS (SMC successfully updated to 80%)")

    # 7. Persistence creation
    print("[7/12] Testing persistence creation (launchd daemon)...")
    run(["sudo", BCLM_PATH, "persist"])
    assert os.path.isfile(PLIST_PATH), f"Plist file not created at {PLIST_PATH}"
    
    # Check permissions (must be 0644, root:wheel)
    st = os.stat(PLIST_PATH)
    mode = oct(st.st_mode)[-3:]
    print(f"  Plist file mode: {mode}, uid: {st.st_uid}, gid: {st.st_gid}")
    assert mode in ("644", "600"), f"Unexpected mode {mode}"
    assert st.st_uid == 0, "Plist must be owned by root"

    # Verify launchd registered service
    res = run(["sudo", "/bin/launchctl", "print", "system/com.zackelia.bclm.plist"])
    assert "com.zackelia.bclm.plist" in res.stdout
    print("  PASS (daemon registered and verified in system launchd domain)")

    # 8. Persistence idempotency
    print("[8/12] Testing persistence idempotency (running persist again)...")
    res = run(["sudo", BCLM_PATH, "persist"])
    assert "error" not in res.stderr.lower() and "failed" not in res.stderr.lower()
    print("  PASS (idempotent; no duplicate registration crashes)")

    # 9. Unpersistence
    print("[9/12] Testing unpersist...")
    run(["sudo", BCLM_PATH, "unpersist"])
    assert not os.path.exists(PLIST_PATH), "Plist was not removed"
    res = run(["sudo", "/bin/launchctl", "print", "system/com.zackelia.bclm.plist"], check=False)
    assert res.returncode != 0 or "could not find" in res.stderr.lower() or "bad request" in res.stdout.lower()
    print("  PASS (daemon booted out and plist deleted cleanly)")

    # 10. Unpersist idempotency
    print("[10/12] Testing unpersist idempotency...")
    res = run(["sudo", BCLM_PATH, "unpersist"])
    print("  PASS (cleanly handled already-unpersisted state)")

    # 11. Code signature of App bundle
    print("[11/12] Verifying code signature of Charge Limiter.app...")
    res = run(["codesign", "-vvv", "--deep", APP_PATH])
    print("  PASS (App bundle signature is valid)")

    # 12. Restore initial value
    print(f"[12/12] Restoring initial BCLM value to {initial_val}%...")
    run(["sudo", BCLM_PATH, "write", str(initial_val)])
    res = run([BCLM_PATH, "read"])
    assert res.stdout.strip() == str(initial_val)
    print("  PASS (restored)")

    print("=" * 60)
    print("ALL 12 TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    test()

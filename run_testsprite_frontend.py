"""Run all testsprite frontend E2E tests in sequence and report results."""
import asyncio
import importlib
import sys
import time
import traceback
from pathlib import Path

# Path to testsprite_tests
TESTS_DIR = Path(__file__).parent / "testsprite_tests"

# Frontend E2E test files (use Playwright). Filter out API tests (post_, get_, patch_, delete_)
FRONTEND_TEST_FILES = sorted([
    f.name for f in TESTS_DIR.glob("TC*.py")
    if not any(f.name.startswith(p) for p in ("TC001_post_", "TC002_post_", "TC003_get_",
                                                  "TC004_post_", "TC005_post_", "TC006_get_",
                                                  "TC007_patch_", "TC008_delete_", "TC009_post_",
                                                  "TC010_get_"))
])

# Also remove the two duplicate TC001 files (keep only TC001_Sign_in_to_access_the_workspace.py)
# which is the correct one
def _dedupe(names):
    seen_topics = set()
    out = []
    for n in names:
        # The two TC001_* files are essentially the same — keep the first one
        topic = n.split("_")[1] if n.count("_") > 1 else n
        if topic == "Sign":
            key = "Sign"
        else:
            key = topic
        if key in seen_topics and "_Sign" in n:
            continue
        seen_topics.add(key)
        out.append(n)
    return out

FRONTEND_TEST_FILES = _dedupe(FRONTEND_TEST_FILES)


def run_test_module(mod_name: str, path: Path) -> tuple[str, bool, str]:
    """Run a test module's standalone async function. Returns (name, ok, error)."""
    try:
        spec = importlib.util.spec_from_file_location(mod_name, str(path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return (mod_name, True, "")
    except SystemExit:
        return (mod_name, True, "")
    except BaseException as e:
        return (mod_name, False, f"{type(e).__name__}: {e}")
    finally:
        # Give Playwright a moment to release the browser between tests
        time.sleep(0.5)


async def run_async_module(mod_name: str, path: Path) -> tuple[str, bool, str]:
    """Run a test module that uses async internally. Since the modules
    call asyncio.run() at import time, we just import them and catch errors."""
    try:
        # Run in a fresh event loop in a thread
        import concurrent.futures
        def _run():
            return run_test_module(mod_name, path)
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(_run)
            return fut.result(timeout=120)
    except Exception as e:
        return (mod_name, False, f"{type(e).__name__}: {e}")


def main():
    print(f"Running {len(FRONTEND_TEST_FILES)} frontend E2E tests...")
    print()
    passed = 0
    failed = 0
    results = []
    for name in FRONTEND_TEST_FILES:
        path = TESTS_DIR / name
        # The test modules call asyncio.run() at import time, so we just
        # exec them in a subprocess so each test gets a fresh event loop
        # and a fresh browser context.
        import subprocess
        t0 = time.time()
        try:
            r = subprocess.run(
                [sys.executable, str(path)],
                capture_output=True,
                text=True,
                timeout=180,
            )
            elapsed = time.time() - t0
            ok = r.returncode == 0
            if ok:
                passed += 1
                results.append((name, "PASS", elapsed, ""))
            else:
                failed += 1
                err = (r.stderr or r.stdout).strip().splitlines()[-3:] if (r.stderr or r.stdout) else ["no output"]
                results.append((name, "FAIL", elapsed, "\n".join(err)))
        except subprocess.TimeoutExpired:
            failed += 1
            results.append((name, "TIMEOUT", 180.0, "Test exceeded 180s"))
        except Exception as e:
            failed += 1
            results.append((name, "ERROR", 0.0, str(e)))
        # Print progress
        status = "PASS" if results[-1][1] == "PASS" else "FAIL"
        mark = "[OK]" if status == "PASS" else "[X]"
        print(f"  {mark} {name} ({elapsed:.1f}s)")

    print()
    print("=" * 60)
    print(f"Frontend E2E results: {passed} passed, {failed} failed")
    print("=" * 60)
    for name, status, elapsed, err in results:
        if status != "PASS":
            print(f"\n  [{status}] {name} ({elapsed:.1f}s)")
            if err:
                # Strip non-ASCII to avoid cp1252 errors on Windows
                safe_err = err.encode("ascii", "replace").decode("ascii")
                print(f"    {safe_err}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
PhoneSplat Full Pipeline Test

Tests the complete capture pipeline without requiring a phone:
1. Starts the WebSocket server
2. Runs the test client to simulate frame capture
3. Validates the captured session
4. Prepares MonoGS config

Usage:
    python test_full_pipeline.py
    python test_full_pipeline.py --duration 30 --fps 15
    python test_full_pipeline.py --skip-monogs
"""

import argparse
import asyncio
import subprocess
import sys
import time
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent
SERVER_DIR = PROJECT_ROOT / "server"
CAPTURES_DIR = PROJECT_ROOT / "captures"

# Add server to path
sys.path.insert(0, str(SERVER_DIR))


class PipelineTest:
    """End-to-end pipeline test."""

    def __init__(self, duration: int = 10, fps: int = 10, skip_monogs: bool = False):
        self.duration = duration
        self.fps = fps
        self.skip_monogs = skip_monogs

        self.server_process = None
        self.session_id = None

    async def run(self) -> bool:
        """Run the full pipeline test."""
        print("=" * 60)
        print("  PhoneSplat Full Pipeline Test")
        print("=" * 60)
        print()
        print(f"  Duration:    {self.duration}s")
        print(f"  Target FPS:  {self.fps}")
        print(f"  Skip MonoGS: {self.skip_monogs}")
        print()

        success = True
        steps = [
            ("Starting server", self.start_server),
            ("Running test capture", self.run_test_capture),
            ("Stopping server", self.stop_server),
            ("Finding captured session", self.find_session),
            ("Validating capture", self.validate_capture),
        ]

        if not self.skip_monogs:
            steps.append(("Preparing MonoGS", self.prepare_monogs))

        for step_name, step_func in steps:
            print(f"\n[Step] {step_name}...")
            print("-" * 40)

            try:
                result = await step_func() if asyncio.iscoroutinefunction(step_func) else step_func()
                if not result:
                    print(f"FAILED: {step_name}")
                    success = False
                    break
                print(f"OK: {step_name}")
            except Exception as e:
                print(f"ERROR: {step_name} - {e}")
                success = False
                break

        # Cleanup
        if self.server_process:
            self.stop_server()

        # Summary
        print()
        print("=" * 60)
        if success:
            print("  Pipeline Test: PASSED")
            if self.session_id:
                print(f"  Session: {self.session_id}")
                print()
                print("  Next steps:")
                print(f"    1. View session: captures/{self.session_id}/")
                print(f"    2. Run MonoGS:   python server/monogs_bridge.py run {self.session_id}")
        else:
            print("  Pipeline Test: FAILED")
        print("=" * 60)

        return success

    def start_server(self) -> bool:
        """Start the WebSocket server."""
        main_script = SERVER_DIR / "main.py"

        if not main_script.exists():
            print(f"Server script not found: {main_script}")
            return False

        # Start server as subprocess
        self.server_process = subprocess.Popen(
            [sys.executable, str(main_script)],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        # Wait for server to start
        print("Waiting for server to initialize...")
        time.sleep(2)

        # Check it's still running
        if self.server_process.poll() is not None:
            # Server exited
            output = self.server_process.stdout.read()
            print(f"Server failed to start:\n{output}")
            return False

        print("Server started (PID: {})".format(self.server_process.pid))
        return True

    async def run_test_capture(self) -> bool:
        """Run the test client to capture frames."""
        test_client = SERVER_DIR / "test_client.py"

        if not test_client.exists():
            print(f"Test client not found: {test_client}")
            return False

        # Run test client
        cmd = [
            sys.executable, str(test_client),
            "--fps", str(self.fps),
            "--duration", str(self.duration),
        ]

        print(f"Running: {' '.join(cmd)}")
        print()

        process = subprocess.Popen(
            cmd,
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        # Stream output
        for line in process.stdout:
            print(f"  {line}", end='')

        process.wait()

        if process.returncode != 0:
            print(f"Test client exited with code {process.returncode}")
            return False

        return True

    def stop_server(self) -> bool:
        """Stop the WebSocket server."""
        if self.server_process:
            print("Stopping server...")
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
            self.server_process = None
        return True

    def find_session(self) -> bool:
        """Find the most recently created session."""
        from config import list_sessions

        sessions = list_sessions()
        if not sessions:
            print("No sessions found in captures/")
            return False

        self.session_id = sessions[0]  # Most recent
        session_path = CAPTURES_DIR / self.session_id

        # Check it has frames
        rgb_dir = session_path / "rgb"
        if not rgb_dir.exists():
            print(f"No rgb directory in {self.session_id}")
            return False

        frame_count = len(list(rgb_dir.glob("*.jpg")))
        print(f"Found session: {self.session_id} ({frame_count} frames)")

        return frame_count > 0

    def validate_capture(self) -> bool:
        """Validate the captured session."""
        from validate_capture import validate_session, print_result

        session_path = CAPTURES_DIR / self.session_id
        result = validate_session(session_path)

        print_result(result)

        return result.is_valid

    def prepare_monogs(self) -> bool:
        """Prepare MonoGS config for the session."""
        from monogs_bridge import prepare_session, check_monogs_installation

        session_path = CAPTURES_DIR / self.session_id

        # Check MonoGS
        installed, msg = check_monogs_installation()
        if not installed:
            print(f"MonoGS not installed: {msg}")
            print("Skipping MonoGS preparation (session is still valid)")
            return True  # Don't fail the test

        result = prepare_session(session_path, validate=False)

        if result["warnings"]:
            for w in result["warnings"]:
                print(f"Warning: {w}")

        return result["success"]


def main():
    parser = argparse.ArgumentParser(
        description="Test the full PhoneSplat capture pipeline"
    )

    parser.add_argument(
        "--duration", "-d",
        type=int,
        default=10,
        help="Capture duration in seconds (default: 10)"
    )

    parser.add_argument(
        "--fps", "-f",
        type=int,
        default=10,
        help="Target FPS (default: 10)"
    )

    parser.add_argument(
        "--skip-monogs",
        action="store_true",
        help="Skip MonoGS preparation step"
    )

    args = parser.parse_args()

    # Run the test
    test = PipelineTest(
        duration=args.duration,
        fps=args.fps,
        skip_monogs=args.skip_monogs
    )

    try:
        success = asyncio.run(test.run())
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n\nTest interrupted")
        if test.server_process:
            test.stop_server()
        return 1


if __name__ == "__main__":
    sys.exit(main())

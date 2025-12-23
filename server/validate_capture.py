#!/usr/bin/env python3
"""
Capture Validation Script for PhoneSplat

Validates captured sessions and reports quality metrics.

Usage:
    python validate_capture.py captures/session_xxx
    python validate_capture.py --list
    python validate_capture.py --latest
"""

import argparse
import csv
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from PIL import Image

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from config import (
    CAPTURES_DIR, MIN_FRAMES, MAX_FRAME_GAP, MAX_FRAME_GAP_ERROR,
    MIN_DURATION, EXPECTED_IMU_RATIO, list_sessions
)


@dataclass
class ValidationResult:
    """Results of session validation."""
    session_id: str
    is_valid: bool = True
    quality_score: int = 100

    # Frame stats
    frame_count: int = 0
    duration_sec: float = 0.0
    avg_fps: float = 0.0
    min_fps: float = 0.0
    max_fps: float = 0.0

    # Resolution
    width: int = 0
    height: int = 0
    resolution_consistent: bool = True

    # IMU stats
    imu_records: int = 0
    imu_synced: bool = True
    imu_avg_offset_ms: float = 0.0

    # Intrinsics
    has_intrinsics: bool = False
    intrinsics: dict = field(default_factory=dict)

    # Issues
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    info: list = field(default_factory=list)

    def add_error(self, msg: str, penalty: int = 20):
        self.errors.append(msg)
        self.quality_score = max(0, self.quality_score - penalty)
        self.is_valid = False

    def add_warning(self, msg: str, penalty: int = 10):
        self.warnings.append(msg)
        self.quality_score = max(0, self.quality_score - penalty)

    def add_info(self, msg: str):
        self.info.append(msg)


def parse_timestamp(filename: str) -> float:
    """Extract timestamp from filename like '1234567890.123456.jpg'."""
    stem = Path(filename).stem
    try:
        return float(stem)
    except ValueError:
        return 0.0


def validate_session(session_path: Path) -> ValidationResult:
    """
    Validate a capture session.

    Args:
        session_path: Path to the session directory.

    Returns:
        ValidationResult with all metrics and issues.
    """
    result = ValidationResult(session_id=session_path.name)

    # Check session exists
    if not session_path.exists():
        result.add_error(f"Session path does not exist: {session_path}", 100)
        return result

    rgb_dir = session_path / "rgb"
    imu_file = session_path / "imu.csv"
    rgb_txt = session_path / "rgb.txt"
    intrinsics_file = session_path / "intrinsics.json"

    # ==========================================================================
    # Validate RGB frames
    # ==========================================================================

    if not rgb_dir.exists():
        result.add_error("No rgb/ directory found", 100)
        return result

    frames = sorted(rgb_dir.glob("*.jpg"))
    result.frame_count = len(frames)

    if result.frame_count == 0:
        result.add_error("No frames found in rgb/", 100)
        return result

    if result.frame_count < MIN_FRAMES:
        result.add_error(f"Too few frames: {result.frame_count} < {MIN_FRAMES} minimum", 30)

    # Parse timestamps
    timestamps = []
    for frame in frames:
        ts = parse_timestamp(frame.name)
        if ts > 0:
            timestamps.append(ts)

    if len(timestamps) < 2:
        result.add_error("Cannot determine timestamps from filenames", 50)
        return result

    # Duration and FPS
    result.duration_sec = timestamps[-1] - timestamps[0]

    if result.duration_sec < MIN_DURATION:
        result.add_error(f"Capture too short: {result.duration_sec:.1f}s < {MIN_DURATION}s minimum", 20)

    if result.duration_sec > 0:
        result.avg_fps = result.frame_count / result.duration_sec

    # Check for gaps and calculate per-frame FPS
    gaps = []
    fps_values = []
    large_gaps = 0

    for i in range(1, len(timestamps)):
        gap = timestamps[i] - timestamps[i - 1]
        gaps.append(gap)

        if gap > 0:
            fps_values.append(1.0 / gap)

        if gap > MAX_FRAME_GAP_ERROR:
            large_gaps += 1
            result.add_warning(f"Large gap at frame {i}: {gap:.2f}s", 5)
        elif gap > MAX_FRAME_GAP:
            large_gaps += 1

    if fps_values:
        result.min_fps = min(fps_values)
        result.max_fps = max(fps_values)

    if large_gaps > 0:
        result.add_warning(f"{large_gaps} frame gaps > {MAX_FRAME_GAP}s detected", 5)

    # Check timestamps are monotonic
    is_monotonic = all(timestamps[i] <= timestamps[i + 1] for i in range(len(timestamps) - 1))
    if not is_monotonic:
        result.add_error("Timestamps are not monotonic (frames out of order)", 30)

    # ==========================================================================
    # Validate image dimensions
    # ==========================================================================

    try:
        # Check first and last frame
        first_img = Image.open(frames[0])
        result.width, result.height = first_img.size

        if len(frames) > 1:
            last_img = Image.open(frames[-1])
            if last_img.size != first_img.size:
                result.resolution_consistent = False
                result.add_warning(f"Resolution changed: {first_img.size} -> {last_img.size}", 10)

        # Check a sample of frames if many
        if len(frames) > 20:
            sample_indices = [len(frames) // 4, len(frames) // 2, 3 * len(frames) // 4]
            for idx in sample_indices:
                sample_img = Image.open(frames[idx])
                if sample_img.size != first_img.size:
                    result.resolution_consistent = False
                    result.add_warning(f"Resolution inconsistent at frame {idx}", 5)
                    break

    except Exception as e:
        result.add_error(f"Error reading images: {e}", 20)

    # ==========================================================================
    # Validate IMU data
    # ==========================================================================

    if imu_file.exists():
        try:
            with open(imu_file, 'r') as f:
                reader = csv.reader(f)
                header = next(reader, None)
                imu_rows = list(reader)

            result.imu_records = len(imu_rows)

            if result.imu_records == 0:
                result.add_warning("IMU file exists but is empty", 10)
            else:
                # Check IMU/frame ratio
                expected_imu = result.frame_count * EXPECTED_IMU_RATIO
                ratio = result.imu_records / max(1, result.frame_count)

                if ratio < 1:
                    result.add_warning(f"Low IMU rate: {ratio:.1f} samples/frame", 5)

                # Check IMU timestamps are in range
                imu_timestamps = [float(row[0]) for row in imu_rows if row]
                if imu_timestamps:
                    imu_start = min(imu_timestamps)
                    imu_end = max(imu_timestamps)
                    frame_start = timestamps[0]
                    frame_end = timestamps[-1]

                    # IMU should roughly span the frame timestamps
                    if imu_start > frame_start + 1.0:
                        result.add_warning("IMU data starts late", 5)
                    if imu_end < frame_end - 1.0:
                        result.add_warning("IMU data ends early", 5)

                    # Calculate average offset (simplified)
                    result.imu_avg_offset_ms = abs(imu_start - frame_start) * 1000

        except Exception as e:
            result.add_warning(f"Error reading IMU data: {e}", 10)
    else:
        result.add_warning("No IMU data file found", 15)
        result.imu_synced = False

    # ==========================================================================
    # Validate intrinsics
    # ==========================================================================

    if intrinsics_file.exists():
        try:
            with open(intrinsics_file, 'r') as f:
                result.intrinsics = json.load(f)
            result.has_intrinsics = True

            # Validate required fields
            required = ['fx', 'fy', 'cx', 'cy', 'width', 'height']
            missing = [k for k in required if k not in result.intrinsics]
            if missing:
                result.add_warning(f"Missing intrinsic fields: {missing}", 5)

            # Check intrinsics match image dimensions
            if result.has_intrinsics and result.width > 0:
                intr_w = result.intrinsics.get('width', 0)
                intr_h = result.intrinsics.get('height', 0)
                if intr_w != result.width or intr_h != result.height:
                    result.add_warning(
                        f"Intrinsics resolution ({intr_w}x{intr_h}) != "
                        f"actual ({result.width}x{result.height})", 10)

        except Exception as e:
            result.add_warning(f"Error reading intrinsics: {e}", 10)
    else:
        result.add_warning("No intrinsics.json found", 15)

    # ==========================================================================
    # Validate rgb.txt (TUM format)
    # ==========================================================================

    if rgb_txt.exists():
        try:
            with open(rgb_txt, 'r') as f:
                lines = [l.strip() for l in f if l.strip() and not l.startswith('#')]

            if len(lines) != result.frame_count:
                result.add_warning(
                    f"rgb.txt has {len(lines)} entries but {result.frame_count} frames", 5)

        except Exception as e:
            result.add_warning(f"Error reading rgb.txt: {e}", 5)
    else:
        result.add_warning("No rgb.txt (TUM format timestamps) found", 5)

    # ==========================================================================
    # Additional recommendations
    # ==========================================================================

    if result.avg_fps < 8:
        result.add_info("Consider higher FPS for better reconstruction quality")

    if result.avg_fps > 20:
        result.add_info("High FPS captured - good for fast motion")

    if result.frame_count > 500:
        result.add_info("Large capture - reconstruction may take a while")

    if result.duration_sec < 10:
        result.add_info("Short capture - ensure scene coverage is adequate")

    return result


def print_result(result: ValidationResult):
    """Print validation result in a nice format."""
    print()
    print(f"Session: {result.session_id}")
    print("=" * 50)

    # Basic stats
    print(f"Frames:      {result.frame_count}")
    print(f"Duration:    {result.duration_sec:.1f}s")
    print(f"Avg FPS:     {result.avg_fps:.1f}")

    if result.min_fps > 0:
        print(f"FPS Range:   {result.min_fps:.1f} - {result.max_fps:.1f}")

    # Resolution
    res_status = "consistent" if result.resolution_consistent else "INCONSISTENT"
    print(f"Resolution:  {result.width}x{result.height} ({res_status})")

    # IMU
    if result.imu_records > 0:
        sync_status = f"offset: {result.imu_avg_offset_ms:.1f}ms" if result.imu_synced else "NOT SYNCED"
        print(f"IMU Records: {result.imu_records} ({sync_status})")
    else:
        print("IMU Records: None")

    # Intrinsics
    if result.has_intrinsics:
        fx = result.intrinsics.get('fx', 0)
        fy = result.intrinsics.get('fy', 0)
        print(f"Intrinsics:  fx={fx:.0f}, fy={fy:.0f}")
    else:
        print("Intrinsics:  Not found")

    print()
    print(f"Quality Score: {result.quality_score}/100")
    print()

    # Issues
    if result.errors:
        print("ERRORS:")
        for err in result.errors:
            print(f"  [X] {err}")

    if result.warnings:
        print("WARNINGS:")
        for warn in result.warnings:
            print(f"  [!] {warn}")

    if result.info:
        print("INFO:")
        for info in result.info:
            print(f"  [i] {info}")

    print()
    ready = "YES" if result.is_valid else "NO"
    print(f"Ready for reconstruction: {ready}")
    print()

    return result.is_valid


def main():
    parser = argparse.ArgumentParser(
        description="Validate PhoneSplat capture sessions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python validate_capture.py captures/session_20241222_153045
  python validate_capture.py --list
  python validate_capture.py --latest
"""
    )

    parser.add_argument(
        "session_path",
        nargs="?",
        help="Path to session directory"
    )

    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List all sessions"
    )

    parser.add_argument(
        "--latest",
        action="store_true",
        help="Validate the most recent session"
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )

    args = parser.parse_args()

    # List sessions
    if args.list:
        sessions = list_sessions()
        if not sessions:
            print("No sessions found in captures/")
            return 0

        print("Available sessions:")
        for s in sessions:
            print(f"  {s}")
        return 0

    # Determine session path
    session_path = None

    if args.latest:
        sessions = list_sessions()
        if not sessions:
            print("No sessions found")
            return 1
        session_path = CAPTURES_DIR / sessions[0]

    elif args.session_path:
        session_path = Path(args.session_path)
        # Handle relative paths
        if not session_path.is_absolute():
            # Try as-is first
            if not session_path.exists():
                # Try in captures dir
                session_path = CAPTURES_DIR / args.session_path
    else:
        parser.print_help()
        return 1

    # Validate
    result = validate_session(session_path)

    if args.json:
        import json as json_module
        output = {
            "session_id": result.session_id,
            "is_valid": result.is_valid,
            "quality_score": result.quality_score,
            "frame_count": result.frame_count,
            "duration_sec": result.duration_sec,
            "avg_fps": result.avg_fps,
            "resolution": f"{result.width}x{result.height}",
            "imu_records": result.imu_records,
            "errors": result.errors,
            "warnings": result.warnings,
            "info": result.info,
        }
        print(json_module.dumps(output, indent=2))
    else:
        print_result(result)

    return 0 if result.is_valid else 1


if __name__ == "__main__":
    sys.exit(main())

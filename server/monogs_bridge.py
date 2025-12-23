#!/usr/bin/env python3
"""
MonoGS Bridge for PhoneSplat

Prepares capture sessions for MonoGS reconstruction and manages the pipeline.

Usage:
    python monogs_bridge.py prepare captures/session_xxx
    python monogs_bridge.py run captures/session_xxx
    python monogs_bridge.py export captures/session_xxx --output model.ply
    python monogs_bridge.py status
"""

import argparse
import json
import os
import subprocess
import sys
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from config import (
    CAPTURES_DIR, MONOGS_PATH, MONOGS_OUTPUT_DIR,
    MONOGS_TRACKING_CONFIG, MONOGS_MAPPING_CONFIG,
    check_monogs_installation, list_sessions
)
from validate_capture import validate_session


def generate_monogs_config(session_path: Path, output_path: Optional[Path] = None) -> Path:
    """
    Generate a MonoGS-compatible YAML config file for a session.

    Args:
        session_path: Path to the capture session.
        output_path: Where to save the config. Defaults to session_path/monogs_config.yaml

    Returns:
        Path to the generated config file.
    """
    if output_path is None:
        output_path = session_path / "monogs_config.yaml"

    # Load intrinsics
    intrinsics_file = session_path / "intrinsics.json"
    if not intrinsics_file.exists():
        raise FileNotFoundError(f"Intrinsics file not found: {intrinsics_file}")

    with open(intrinsics_file, 'r') as f:
        intrinsics = json.load(f)

    # Build config
    config = {
        "dataset": "tum",
        "data": {
            "basedir": str(session_path.absolute()).replace("\\", "/"),
            "sequence": ".",
            "gradslam_data_cfg": {
                "dataset_name": "tum",
            },
        },
        "camera": {
            "H": intrinsics.get("height", 1280),
            "W": intrinsics.get("width", 720),
            "fx": float(intrinsics.get("fx", 1000)),
            "fy": float(intrinsics.get("fy", 1000)),
            "cx": float(intrinsics.get("cx", 360)),
            "cy": float(intrinsics.get("cy", 640)),
            "png_depth_scale": 5000.0,  # Not used for monocular
            "crop_edge": 0,
        },
        "tracking": {
            "iters": MONOGS_TRACKING_CONFIG.get("iters", 40),
            "w_color_loss": MONOGS_TRACKING_CONFIG.get("w_color_loss", 0.5),
            "use_depth_loss": False,  # Monocular mode
            "use_sil_for_loss": True,
            "sil_thres": 0.5,
            "use_gt_depth": False,
            "ignore_outlier_depth_loss": False,
            "tracking_device": "cuda:0",
        },
        "mapping": {
            "iters": MONOGS_MAPPING_CONFIG.get("iters", 60),
            "new_submap_every": MONOGS_MAPPING_CONFIG.get("new_submap_every", 50),
            "new_gaussians_every": MONOGS_MAPPING_CONFIG.get("new_gaussians_every", 5),
            "use_gt_depth": False,
            "mapping_device": "cuda:0",
        },
        "viz": {
            "use_gui": True,
            "save_imgs": True,
            "save_videos": False,
        },
        "Training": {
            "monocular": True,
            "edge_threshold": 4.0,
            "rgb_boundary_threshold": 0.01,
        },
    }

    # Write config
    with open(output_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    return output_path


def create_associations_file(session_path: Path) -> Path:
    """
    Create associations.txt file that MonoGS may need.
    Format: timestamp rgb/filename depth/filename (depth is dummy for monocular)

    Args:
        session_path: Path to the capture session.

    Returns:
        Path to the associations file.
    """
    rgb_txt = session_path / "rgb.txt"
    associations_file = session_path / "associations.txt"

    if not rgb_txt.exists():
        raise FileNotFoundError(f"rgb.txt not found: {rgb_txt}")

    with open(rgb_txt, 'r') as f:
        lines = [l.strip() for l in f if l.strip() and not l.startswith('#')]

    # Create associations (rgb only for monocular)
    with open(associations_file, 'w') as f:
        for line in lines:
            parts = line.split()
            if len(parts) >= 2:
                timestamp, rgb_path = parts[0], parts[1]
                # For monocular, we just repeat the rgb entry (no depth)
                f.write(f"{timestamp} {rgb_path}\n")

    return associations_file


def prepare_session(session_path: Path, validate: bool = True) -> dict:
    """
    Prepare a capture session for MonoGS reconstruction.

    Args:
        session_path: Path to the capture session.
        validate: Whether to validate the session first.

    Returns:
        Dict with preparation results.
    """
    result = {
        "session": session_path.name,
        "success": False,
        "config_path": None,
        "errors": [],
        "warnings": [],
    }

    print(f"\nPreparing session: {session_path.name}")
    print("=" * 50)

    # Validate if requested
    if validate:
        print("Validating capture...")
        validation = validate_session(session_path)

        if not validation.is_valid:
            result["errors"].extend(validation.errors)
            print(f"Validation failed with {len(validation.errors)} errors")
            return result

        if validation.warnings:
            result["warnings"].extend(validation.warnings)
            print(f"Validation passed with {len(validation.warnings)} warnings")
        else:
            print("Validation passed")

    # Check required files
    required_files = ["rgb.txt", "intrinsics.json"]
    for fname in required_files:
        if not (session_path / fname).exists():
            result["errors"].append(f"Missing required file: {fname}")

    if result["errors"]:
        return result

    # Generate MonoGS config
    print("Generating MonoGS config...")
    try:
        config_path = generate_monogs_config(session_path)
        result["config_path"] = str(config_path)
        print(f"  Config saved to: {config_path.name}")
    except Exception as e:
        result["errors"].append(f"Failed to generate config: {e}")
        return result

    # Create associations file
    print("Creating associations file...")
    try:
        assoc_path = create_associations_file(session_path)
        print(f"  Associations saved to: {assoc_path.name}")
    except Exception as e:
        result["warnings"].append(f"Failed to create associations: {e}")

    # Create output directory
    output_dir = session_path / MONOGS_OUTPUT_DIR
    output_dir.mkdir(exist_ok=True)
    print(f"  Output directory: {output_dir.name}/")

    result["success"] = True

    print()
    print("Preparation complete!")
    print(f"  Config: {result['config_path']}")
    print()
    print("To run MonoGS:")
    print(f"  cd {MONOGS_PATH}")
    print(f"  python slam.py --config {config_path}")

    return result


def run_monogs(session_path: Path, monogs_path: Optional[Path] = None, headless: bool = False) -> dict:
    """
    Run MonoGS on a prepared session.

    Args:
        session_path: Path to the capture session.
        monogs_path: Path to MonoGS installation.
        headless: Run without GUI.

    Returns:
        Dict with run results.
    """
    if monogs_path is None:
        monogs_path = MONOGS_PATH

    result = {
        "session": session_path.name,
        "success": False,
        "output_dir": None,
        "error": None,
    }

    # Check MonoGS installation
    installed, msg = check_monogs_installation()
    if not installed:
        result["error"] = msg
        print(f"Error: {msg}")
        print()
        print("To install MonoGS:")
        print("  git clone --recursive https://github.com/muskie82/MonoGS.git")
        print("  cd MonoGS")
        print("  conda env create -f environment.yml")
        print("  conda activate MonoGS")
        return result

    # Check session is prepared
    config_path = session_path / "monogs_config.yaml"
    if not config_path.exists():
        print("Session not prepared. Running preparation first...")
        prep_result = prepare_session(session_path)
        if not prep_result["success"]:
            result["error"] = "Failed to prepare session"
            return result
        config_path = Path(prep_result["config_path"])

    # Build command
    slam_script = monogs_path / "slam.py"
    cmd = [
        sys.executable,  # Use same Python
        str(slam_script),
        "--config", str(config_path),
    ]

    if headless:
        # Modify config to disable GUI
        pass  # Would need to edit config

    print(f"\nRunning MonoGS on {session_path.name}...")
    print(f"Command: {' '.join(cmd)}")
    print()
    print("This may take a while. Press Ctrl+C to cancel.")
    print("-" * 50)

    try:
        # Change to MonoGS directory and run
        process = subprocess.Popen(
            cmd,
            cwd=str(monogs_path),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        # Stream output
        for line in process.stdout:
            print(line, end='')

        process.wait()

        if process.returncode == 0:
            result["success"] = True
            result["output_dir"] = str(session_path / MONOGS_OUTPUT_DIR)
            print()
            print("MonoGS completed successfully!")
        else:
            result["error"] = f"MonoGS exited with code {process.returncode}"
            print()
            print(f"MonoGS failed with exit code {process.returncode}")

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        result["error"] = "Interrupted"
        process.terminate()

    except Exception as e:
        result["error"] = str(e)
        print(f"\nError running MonoGS: {e}")

    return result


def export_model(session_path: Path, output_path: Optional[Path] = None, format: str = "ply") -> dict:
    """
    Export the reconstructed model.

    Args:
        session_path: Path to the capture session.
        output_path: Where to save the exported model.
        format: Export format (ply, splat).

    Returns:
        Dict with export results.
    """
    result = {
        "session": session_path.name,
        "success": False,
        "output_path": None,
        "error": None,
    }

    monogs_output = session_path / MONOGS_OUTPUT_DIR

    if not monogs_output.exists():
        result["error"] = "No MonoGS output found. Run reconstruction first."
        return result

    # Look for output files
    # MonoGS typically outputs point clouds and gaussian params
    ply_files = list(monogs_output.glob("*.ply"))
    pt_files = list(monogs_output.glob("*.pt"))

    if not ply_files and not pt_files:
        result["error"] = "No model files found in MonoGS output"
        return result

    # Determine output path
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = session_path / f"export_{timestamp}.{format}"

    # For PLY format, just copy the file
    if format == "ply" and ply_files:
        src_ply = ply_files[0]  # Take first/latest
        shutil.copy(src_ply, output_path)
        result["success"] = True
        result["output_path"] = str(output_path)
        print(f"Exported PLY to: {output_path}")

    elif format == "splat" and pt_files:
        # Would need conversion from PyTorch checkpoint to .splat format
        result["error"] = "SPLAT export not yet implemented"

    else:
        result["error"] = f"No suitable files found for {format} export"

    return result


def show_status():
    """Show status of MonoGS installation and sessions."""
    print("PhoneSplat MonoGS Bridge Status")
    print("=" * 50)

    # Check MonoGS
    installed, msg = check_monogs_installation()
    status = "OK" if installed else "NOT FOUND"
    print(f"\nMonoGS Installation: {status}")
    print(f"  Path: {MONOGS_PATH}")
    if not installed:
        print(f"  {msg}")
        print()
        print("  To install MonoGS:")
        print("    git clone --recursive https://github.com/muskie82/MonoGS.git")
        print("    cd MonoGS")
        print("    conda env create -f environment.yml")

    # List sessions
    print(f"\nCaptures Directory: {CAPTURES_DIR}")
    sessions = list_sessions()

    if not sessions:
        print("  No sessions found")
    else:
        print(f"  {len(sessions)} session(s) found:")
        for session_id in sessions[:5]:  # Show latest 5
            session_path = CAPTURES_DIR / session_id
            config_exists = (session_path / "monogs_config.yaml").exists()
            output_exists = (session_path / MONOGS_OUTPUT_DIR).exists()

            status_parts = []
            if config_exists:
                status_parts.append("prepared")
            if output_exists:
                status_parts.append("reconstructed")

            status_str = ", ".join(status_parts) if status_parts else "captured"
            print(f"    {session_id} [{status_str}]")

        if len(sessions) > 5:
            print(f"    ... and {len(sessions) - 5} more")


def main():
    parser = argparse.ArgumentParser(
        description="MonoGS Bridge for PhoneSplat",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  prepare   Generate MonoGS config for a session
  run       Run MonoGS reconstruction
  export    Export reconstructed model
  status    Show installation and session status

Examples:
  python monogs_bridge.py status
  python monogs_bridge.py prepare captures/session_20241222_153045
  python monogs_bridge.py run captures/session_20241222_153045
  python monogs_bridge.py export captures/session_20241222_153045 -o model.ply
"""
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Status command
    status_parser = subparsers.add_parser("status", help="Show status")

    # Prepare command
    prepare_parser = subparsers.add_parser("prepare", help="Prepare session for MonoGS")
    prepare_parser.add_argument("session", help="Session path or ID")
    prepare_parser.add_argument("--no-validate", action="store_true", help="Skip validation")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run MonoGS reconstruction")
    run_parser.add_argument("session", help="Session path or ID")
    run_parser.add_argument("--monogs-path", type=Path, help="Path to MonoGS")
    run_parser.add_argument("--headless", action="store_true", help="Run without GUI")

    # Export command
    export_parser = subparsers.add_parser("export", help="Export reconstructed model")
    export_parser.add_argument("session", help="Session path or ID")
    export_parser.add_argument("-o", "--output", type=Path, help="Output file path")
    export_parser.add_argument("-f", "--format", choices=["ply", "splat"], default="ply")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 0

    # Resolve session path for commands that need it
    if hasattr(args, 'session'):
        session_path = Path(args.session)
        if not session_path.is_absolute():
            # Try as session ID
            if not session_path.exists():
                session_path = CAPTURES_DIR / args.session
        if not session_path.exists():
            print(f"Error: Session not found: {args.session}")
            return 1

    # Execute command
    if args.command == "status":
        show_status()
        return 0

    elif args.command == "prepare":
        result = prepare_session(session_path, validate=not args.no_validate)
        return 0 if result["success"] else 1

    elif args.command == "run":
        result = run_monogs(
            session_path,
            monogs_path=args.monogs_path,
            headless=args.headless
        )
        return 0 if result["success"] else 1

    elif args.command == "export":
        result = export_model(
            session_path,
            output_path=args.output,
            format=args.format
        )
        return 0 if result["success"] else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

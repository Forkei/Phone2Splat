"""
PhoneSplat Configuration

Central configuration for paths, server settings, and MonoGS integration.
"""

import os
from pathlib import Path

# =============================================================================
# Paths
# =============================================================================

# Project root (parent of server/)
PROJECT_ROOT = Path(__file__).parent.parent

# Captures directory (inside server/)
CAPTURES_DIR = Path(__file__).parent / "captures"

# MonoGS installation path (can be overridden via environment variable)
MONOGS_PATH = Path(os.environ.get(
    "MONOGS_PATH",
    "C:/Users/forke/Documents/Video2Model/MonoGS"
))

# MonoGS output directory (inside each session folder)
MONOGS_OUTPUT_DIR = "monogs_output"

# =============================================================================
# Server Settings
# =============================================================================

WEBSOCKET_HOST = "0.0.0.0"
WEBSOCKET_PORT = 8765

# =============================================================================
# Capture Defaults
# =============================================================================

DEFAULT_FPS = 10
DEFAULT_RESOLUTION = "720p"
DEFAULT_JPEG_QUALITY = 0.8

# Resolution dimensions
RESOLUTIONS = {
    "480p": (640, 480),
    "720p": (1280, 720),
    "1080p": (1920, 1080),
}

# =============================================================================
# Validation Thresholds
# =============================================================================

# Minimum frames for a valid capture
MIN_FRAMES = 30

# Maximum gap between frames (seconds) before warning
MAX_FRAME_GAP = 0.5

# Maximum gap before error
MAX_FRAME_GAP_ERROR = 2.0

# Minimum capture duration (seconds)
MIN_DURATION = 3.0

# Expected IMU samples per frame (at 100Hz IMU, 10fps = 10 samples/frame)
EXPECTED_IMU_RATIO = 10

# =============================================================================
# MonoGS Settings
# =============================================================================

# Default MonoGS tracking parameters
MONOGS_TRACKING_CONFIG = {
    "iters": 40,
    "w_color_loss": 0.5,
    "use_depth": False,  # Monocular mode
}

# Default MonoGS mapping parameters
MONOGS_MAPPING_CONFIG = {
    "iters": 60,
    "new_submap_every": 50,
    "new_gaussians_every": 5,
}

# =============================================================================
# Helper Functions
# =============================================================================

def get_session_path(session_id: str) -> Path:
    """Get the full path for a session."""
    return CAPTURES_DIR / session_id


def list_sessions() -> list:
    """List all capture sessions."""
    if not CAPTURES_DIR.exists():
        return []

    sessions = []
    for path in CAPTURES_DIR.iterdir():
        if path.is_dir() and path.name.startswith("session_"):
            sessions.append(path.name)

    return sorted(sessions, reverse=True)


def check_monogs_installation() -> tuple[bool, str]:
    """
    Check if MonoGS is installed and accessible.

    Returns:
        (is_installed, message)
    """
    if not MONOGS_PATH.exists():
        return False, f"MonoGS not found at {MONOGS_PATH}"

    # Check for key files
    main_script = MONOGS_PATH / "slam.py"
    if not main_script.exists():
        return False, f"MonoGS slam.py not found at {main_script}"

    config_dir = MONOGS_PATH / "configs"
    if not config_dir.exists():
        return False, f"MonoGS configs directory not found"

    return True, f"MonoGS found at {MONOGS_PATH}"


def print_config():
    """Print current configuration."""
    print("PhoneSplat Configuration")
    print("=" * 50)
    print(f"Project Root:    {PROJECT_ROOT}")
    print(f"Captures Dir:    {CAPTURES_DIR}")
    print(f"MonoGS Path:     {MONOGS_PATH}")
    print(f"WebSocket Port:  {WEBSOCKET_PORT}")
    print()

    installed, msg = check_monogs_installation()
    print(f"MonoGS Status:   {'OK' if installed else 'NOT FOUND'}")
    print(f"  {msg}")


if __name__ == "__main__":
    print_config()

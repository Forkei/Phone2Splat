#!/usr/bin/env python3
"""
PhoneSplat Server - Main Entry Point

A WebSocket server that receives camera frames from a phone app
and saves them in TUM RGB-D format for 3D reconstruction.

Usage:
    python main.py [--host HOST] [--port PORT] [--captures-dir DIR]

Example:
    python main.py --port 8765 --captures-dir ./captures
"""

import argparse
import asyncio
import signal
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from websocket_server import PhoneSplatServer


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="PhoneSplat Server - Receive camera frames from phone for 3D reconstruction",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                           # Start with defaults (0.0.0.0:8765)
  python main.py --port 9000               # Use custom port
  python main.py --captures-dir ./data     # Save to custom directory
  python main.py --host 192.168.1.100      # Bind to specific IP

The server accepts WebSocket connections and receives JSON packets:
{
  "timestamp": 1234567890.123,
  "frame": "<base64 JPEG>",
  "imu": {"accel": [x,y,z], "gyro": [x,y,z], "orientation": [qw,qx,qy,qz]},
  "camera_intrinsics": {"fx": 1000, "fy": 1000, "cx": 360, "cy": 640, ...}
}

Saved data structure:
  captures/
    session_YYYYMMDD_HHMMSS/
      rgb/
        <timestamp>.jpg
      imu.csv
      rgb.txt (TUM format)
      intrinsics.json
"""
    )

    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0 for all interfaces)"
    )

    parser.add_argument(
        "--port", "-p",
        type=int,
        default=8765,
        help="Port to bind to (default: 8765)"
    )

    parser.add_argument(
        "--captures-dir", "-d",
        default="captures",
        help="Directory for saving captured frames (default: ./captures)"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )

    return parser.parse_args()


def get_local_ip():
    """Get the local IP address for display purposes."""
    import socket
    try:
        # Create a socket to determine the local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


async def main():
    """Main entry point."""
    args = parse_args()

    # Create captures directory
    captures_path = Path(args.captures_dir)
    captures_path.mkdir(parents=True, exist_ok=True)

    # Print banner
    local_ip = get_local_ip()
    print("=" * 60)
    print("  PhoneSplat Server")
    print("  Real-time Phone-to-Laptop 3D Scanner")
    print("=" * 60)
    print()
    print(f"  Local IP:      {local_ip}")
    print(f"  WebSocket:     ws://{local_ip}:{args.port}")
    print(f"  Captures Dir:  {captures_path.absolute()}")
    print()
    print("  Connect your phone app to the WebSocket URL above.")
    print("  Press Ctrl+C to stop the server.")
    print()
    print("-" * 60)

    # Create and start server
    server = PhoneSplatServer(
        host=args.host,
        port=args.port,
        captures_dir=args.captures_dir
    )

    # Setup signal handlers for graceful shutdown
    stop_event = asyncio.Event()

    def handle_signal():
        print("\n\nShutdown signal received...")
        stop_event.set()

    # Windows doesn't support add_signal_handler well, so we rely on KeyboardInterrupt
    if sys.platform != "win32":
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, handle_signal)

    try:
        await server.start()

        # Wait for stop signal
        await stop_event.wait()

    except KeyboardInterrupt:
        print("\n\nKeyboard interrupt received...")

    finally:
        await server.stop()

    print("\nGoodbye!")


def run():
    """Entry point for the server."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    run()

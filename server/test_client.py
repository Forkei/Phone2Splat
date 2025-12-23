#!/usr/bin/env python3
"""
Test Client for PhoneSplat Server

Simulates a phone app sending camera frames to the server.
Useful for testing the server without a phone.

Usage:
    python test_client.py [--host HOST] [--port PORT] [--fps FPS] [--duration SECONDS]

Example:
    python test_client.py --fps 10 --duration 30
"""

import argparse
import asyncio
import base64
import json
import random
import time
import io
import sys
from pathlib import Path

try:
    import websockets
except ImportError:
    print("Please install websockets: pip install websockets")
    sys.exit(1)

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("Warning: PIL not installed. Using placeholder image data.")


def generate_test_frame(width: int = 720, height: int = 1280, frame_num: int = 0) -> bytes:
    """
    Generate a test JPEG frame.

    Args:
        width: Frame width.
        height: Frame height.
        frame_num: Frame number for visual identification.

    Returns:
        JPEG bytes.
    """
    if HAS_PIL:
        # Create a colored gradient image with frame number
        img = Image.new('RGB', (width, height))
        pixels = img.load()

        # Create gradient based on frame number
        hue_offset = (frame_num * 10) % 360

        for y in range(height):
            for x in range(width):
                # Create a gradient pattern
                r = int((x / width) * 255)
                g = int((y / height) * 255)
                b = int(((frame_num * 5) % 256))
                pixels[x, y] = (r, g, b)

        # Save to JPEG
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=80)
        return buffer.getvalue()
    else:
        # Return a minimal valid JPEG (1x1 red pixel)
        # This is a valid minimal JPEG file
        return bytes([
            0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
            0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
            0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08, 0x07, 0x07, 0x07, 0x09,
            0x09, 0x08, 0x0A, 0x0C, 0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
            0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20,
            0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
            0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27, 0x39, 0x3D, 0x38, 0x32,
            0x3C, 0x2E, 0x33, 0x34, 0x32, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01,
            0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4, 0x00, 0x1F, 0x00, 0x00,
            0x01, 0x05, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
            0x09, 0x0A, 0x0B, 0xFF, 0xC4, 0x00, 0xB5, 0x10, 0x00, 0x02, 0x01, 0x03,
            0x03, 0x02, 0x04, 0x03, 0x05, 0x05, 0x04, 0x04, 0x00, 0x00, 0x01, 0x7D,
            0x01, 0x02, 0x03, 0x00, 0x04, 0x11, 0x05, 0x12, 0x21, 0x31, 0x41, 0x06,
            0x13, 0x51, 0x61, 0x07, 0x22, 0x71, 0x14, 0x32, 0x81, 0x91, 0xA1, 0x08,
            0x23, 0x42, 0xB1, 0xC1, 0x15, 0x52, 0xD1, 0xF0, 0x24, 0x33, 0x62, 0x72,
            0x82, 0x09, 0x0A, 0x16, 0x17, 0x18, 0x19, 0x1A, 0x25, 0x26, 0x27, 0x28,
            0x29, 0x2A, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3A, 0x43, 0x44, 0x45,
            0x46, 0x47, 0x48, 0x49, 0x4A, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59,
            0x5A, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69, 0x6A, 0x73, 0x74, 0x75,
            0x76, 0x77, 0x78, 0x79, 0x7A, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89,
            0x8A, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98, 0x99, 0x9A, 0xA2, 0xA3,
            0xA4, 0xA5, 0xA6, 0xA7, 0xA8, 0xA9, 0xAA, 0xB2, 0xB3, 0xB4, 0xB5, 0xB6,
            0xB7, 0xB8, 0xB9, 0xBA, 0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7, 0xC8, 0xC9,
            0xCA, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9, 0xDA, 0xE1, 0xE2,
            0xE3, 0xE4, 0xE5, 0xE6, 0xE7, 0xE8, 0xE9, 0xEA, 0xF1, 0xF2, 0xF3, 0xF4,
            0xF5, 0xF6, 0xF7, 0xF8, 0xF9, 0xFA, 0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01,
            0x00, 0x00, 0x3F, 0x00, 0xFB, 0xD5, 0xDB, 0x20, 0xA8, 0xD8, 0x38, 0x28,
            0x00, 0x6A, 0x07, 0x7F, 0xFF, 0xD9
        ])


def generate_imu_data() -> dict:
    """Generate simulated IMU data."""
    return {
        "accel": [
            random.gauss(0, 0.1),
            random.gauss(0, 0.1),
            random.gauss(-9.8, 0.1)  # Gravity on Z axis
        ],
        "gyro": [
            random.gauss(0, 0.01),
            random.gauss(0, 0.01),
            random.gauss(0, 0.01)
        ],
        "orientation": [
            1.0,  # qw
            random.gauss(0, 0.01),  # qx
            random.gauss(0, 0.01),  # qy
            random.gauss(0, 0.01)   # qz
        ]
    }


def generate_camera_intrinsics(width: int = 720, height: int = 1280) -> dict:
    """Generate camera intrinsics (simulated phone camera)."""
    focal_length = 1000  # Typical phone camera
    return {
        "fx": focal_length,
        "fy": focal_length,
        "cx": width / 2,
        "cy": height / 2,
        "width": width,
        "height": height
    }


async def run_test_client(
    host: str = "localhost",
    port: int = 8765,
    fps: int = 10,
    duration: float = 10.0,
    width: int = 720,
    height: int = 1280
):
    """
    Run the test client.

    Args:
        host: Server host.
        port: Server port.
        fps: Frames per second to send.
        duration: How long to send frames (seconds).
        width: Frame width.
        height: Frame height.
    """
    uri = f"ws://{host}:{port}"
    frame_interval = 1.0 / fps

    print(f"Connecting to {uri}...")

    try:
        async with websockets.connect(uri, max_size=10 * 1024 * 1024) as ws:
            print("Connected!")

            # Receive welcome message
            response = await ws.recv()
            data = json.loads(response)
            print(f"Server: {data.get('message', data)}")

            # Send start session command
            await ws.send(json.dumps({
                "type": "control",
                "command": "start_session"
            }))

            response = await ws.recv()
            data = json.loads(response)
            print(f"Session started: {data.get('session_id', 'unknown')}")

            # Send frames
            start_time = time.time()
            frame_count = 0
            intrinsics = generate_camera_intrinsics(width, height)

            print(f"\nSending frames at {fps} FPS for {duration} seconds...")
            print("Press Ctrl+C to stop\n")

            while time.time() - start_time < duration:
                frame_start = time.time()

                # Generate frame
                frame_data = generate_test_frame(width, height, frame_count)
                frame_b64 = base64.b64encode(frame_data).decode('utf-8')

                # Create packet
                packet = {
                    "timestamp": time.time(),
                    "frame": frame_b64,
                    "imu": generate_imu_data(),
                    "camera_intrinsics": intrinsics
                }

                # Send frame
                await ws.send(json.dumps(packet))
                frame_count += 1

                # Print progress
                elapsed = time.time() - start_time
                actual_fps = frame_count / elapsed if elapsed > 0 else 0
                print(f"\rFrames: {frame_count} | "
                      f"Elapsed: {elapsed:.1f}s | "
                      f"Actual FPS: {actual_fps:.1f} | "
                      f"Size: {len(frame_data)/1024:.1f}KB", end="")

                # Check for ACK messages (non-blocking)
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=0.001)
                    ack_data = json.loads(response)
                    if ack_data.get("type") == "ack":
                        stats = ack_data.get("stats", {})
                        # Print stats on new line
                        print(f"\n  Server stats: FPS={stats.get('fps', 0):.1f}, "
                              f"Latency={stats.get('avg_latency_ms', 0):.0f}ms")
                except asyncio.TimeoutError:
                    pass

                # Wait for next frame
                frame_elapsed = time.time() - frame_start
                sleep_time = max(0, frame_interval - frame_elapsed)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)

            # Send end session command
            print("\n\nEnding session...")
            await ws.send(json.dumps({
                "type": "control",
                "command": "end_session"
            }))

            response = await ws.recv()
            data = json.loads(response)
            stats = data.get("stats", {})

            print("\n" + "=" * 50)
            print("Session Complete!")
            print("=" * 50)
            print(f"  Frames sent:     {frame_count}")
            print(f"  Duration:        {stats.get('duration_sec', 0):.1f}s")
            print(f"  Average FPS:     {stats.get('fps', 0):.1f}")
            print(f"  Average Latency: {stats.get('avg_latency_ms', 0):.1f}ms")
            print(f"  Total Size:      {stats.get('total_mb', 0):.1f}MB")
            print("=" * 50)

    except ConnectionRefusedError:
        print(f"Error: Could not connect to server at {uri}")
        print("Make sure the server is running: python main.py")
        return 1

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        return 0

    except Exception as e:
        print(f"\nError: {e}")
        return 1

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Test client for PhoneSplat server"
    )

    parser.add_argument(
        "--host",
        default="localhost",
        help="Server host (default: localhost)"
    )

    parser.add_argument(
        "--port", "-p",
        type=int,
        default=8765,
        help="Server port (default: 8765)"
    )

    parser.add_argument(
        "--fps", "-f",
        type=int,
        default=10,
        help="Frames per second (default: 10)"
    )

    parser.add_argument(
        "--duration", "-d",
        type=float,
        default=10.0,
        help="Duration in seconds (default: 10)"
    )

    parser.add_argument(
        "--width", "-W",
        type=int,
        default=720,
        help="Frame width (default: 720)"
    )

    parser.add_argument(
        "--height", "-H",
        type=int,
        default=1280,
        help="Frame height (default: 1280)"
    )

    args = parser.parse_args()

    print("=" * 50)
    print("  PhoneSplat Test Client")
    print("=" * 50)
    print(f"  Target:     ws://{args.host}:{args.port}")
    print(f"  FPS:        {args.fps}")
    print(f"  Duration:   {args.duration}s")
    print(f"  Resolution: {args.width}x{args.height}")
    print("=" * 50)
    print()

    return asyncio.run(run_test_client(
        host=args.host,
        port=args.port,
        fps=args.fps,
        duration=args.duration,
        width=args.width,
        height=args.height
    ))


if __name__ == "__main__":
    sys.exit(main() or 0)

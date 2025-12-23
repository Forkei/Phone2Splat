"""
Frame Processor Module for PhoneSplat

Handles saving frames and IMU data to disk in TUM RGB-D compatible format.
"""

import asyncio
import base64
import csv
import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
import threading
from queue import Queue, Empty


@dataclass
class FramePacket:
    """Represents a single frame packet from the phone."""
    timestamp: float
    frame_data: bytes  # Raw JPEG bytes
    imu: dict
    camera_intrinsics: dict
    received_at: float = field(default_factory=time.time)

    @property
    def latency_ms(self) -> float:
        """Calculate network latency in milliseconds."""
        return (self.received_at - self.timestamp) * 1000


@dataclass
class SessionStats:
    """Statistics for a capture session."""
    session_id: str
    start_time: float = field(default_factory=time.time)
    frame_count: int = 0
    total_bytes: int = 0
    last_frame_time: float = 0
    latencies: list = field(default_factory=list)

    @property
    def duration(self) -> float:
        return time.time() - self.start_time

    @property
    def fps(self) -> float:
        if self.duration > 0:
            return self.frame_count / self.duration
        return 0.0

    @property
    def avg_latency_ms(self) -> float:
        if self.latencies:
            # Keep only last 100 latencies for rolling average
            recent = self.latencies[-100:]
            return sum(recent) / len(recent)
        return 0.0

    @property
    def bandwidth_mbps(self) -> float:
        if self.duration > 0:
            return (self.total_bytes * 8) / (self.duration * 1_000_000)
        return 0.0


class FrameProcessor:
    """
    Processes and saves frames from the phone app.

    Saves frames in TUM RGB-D format:
    - rgb/<timestamp>.jpg - JPEG frames
    - imu.csv - IMU data
    - rgb.txt - TUM format timestamps
    - intrinsics.json - Camera intrinsics
    """

    def __init__(self, base_dir: str = "captures"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.current_session: Optional[str] = None
        self.session_path: Optional[Path] = None
        self.stats: Optional[SessionStats] = None

        # Async save queue for non-blocking disk writes
        self._save_queue: Queue = Queue()
        self._save_thread: Optional[threading.Thread] = None
        self._running = False

        # File handles for streaming writes
        self._imu_file = None
        self._imu_writer = None
        self._rgb_txt_file = None
        self._intrinsics_saved = False

    def start(self):
        """Start the background save thread."""
        self._running = True
        self._save_thread = threading.Thread(target=self._save_worker, daemon=True)
        self._save_thread.start()

    def stop(self):
        """Stop the background save thread."""
        self._running = False
        if self._save_thread:
            self._save_thread.join(timeout=5.0)
        self._close_files()

    def _save_worker(self):
        """Background worker that saves frames to disk."""
        while self._running:
            try:
                item = self._save_queue.get(timeout=0.1)
                if item is None:
                    continue

                frame_path, frame_data = item
                with open(frame_path, 'wb') as f:
                    f.write(frame_data)

            except Empty:
                continue
            except Exception as e:
                print(f"Error saving frame: {e}")

    def create_session(self, session_id: Optional[str] = None) -> str:
        """
        Create a new capture session.

        Args:
            session_id: Optional custom session ID. If None, generates timestamp-based ID.

        Returns:
            The session ID.
        """
        # Close any existing session
        self._close_files()

        # Generate session ID if not provided
        if session_id is None:
            session_id = datetime.now().strftime("session_%Y%m%d_%H%M%S")

        self.current_session = session_id
        self.session_path = self.base_dir / session_id

        # Create directory structure
        (self.session_path / "rgb").mkdir(parents=True, exist_ok=True)

        # Initialize stats
        self.stats = SessionStats(session_id=session_id)

        # Open files for streaming writes
        self._open_files()

        self._intrinsics_saved = False

        print(f"Created new session: {session_id}")
        print(f"  Path: {self.session_path}")

        return session_id

    def _open_files(self):
        """Open file handles for streaming writes."""
        if self.session_path is None:
            return

        # IMU CSV file
        imu_path = self.session_path / "imu.csv"
        self._imu_file = open(imu_path, 'w', newline='')
        self._imu_writer = csv.writer(self._imu_file)
        self._imu_writer.writerow([
            'timestamp',
            'accel_x', 'accel_y', 'accel_z',
            'gyro_x', 'gyro_y', 'gyro_z',
            'qw', 'qx', 'qy', 'qz'
        ])

        # RGB timestamps file (TUM format)
        rgb_txt_path = self.session_path / "rgb.txt"
        self._rgb_txt_file = open(rgb_txt_path, 'w')
        self._rgb_txt_file.write("# timestamp filename\n")

    def _close_files(self):
        """Close open file handles."""
        if self._imu_file:
            self._imu_file.close()
            self._imu_file = None
            self._imu_writer = None

        if self._rgb_txt_file:
            self._rgb_txt_file.close()
            self._rgb_txt_file = None

    async def process_frame(self, packet: FramePacket) -> bool:
        """
        Process and save a frame packet.

        Args:
            packet: The frame packet to process.

        Returns:
            True if successful, False otherwise.
        """
        if self.session_path is None:
            print("No active session. Creating new session...")
            self.create_session()

        try:
            # Update stats
            self.stats.frame_count += 1
            self.stats.total_bytes += len(packet.frame_data)
            self.stats.last_frame_time = packet.timestamp
            self.stats.latencies.append(packet.latency_ms)

            # Save frame (async via queue)
            timestamp_str = f"{packet.timestamp:.6f}"
            frame_filename = f"{timestamp_str}.jpg"
            frame_path = self.session_path / "rgb" / frame_filename

            # Queue for background save
            self._save_queue.put((str(frame_path), packet.frame_data))

            # Write IMU data
            if self._imu_writer and packet.imu:
                imu = packet.imu
                accel = imu.get('accel', [0, 0, 0])
                gyro = imu.get('gyro', [0, 0, 0])
                orient = imu.get('orientation', [1, 0, 0, 0])

                self._imu_writer.writerow([
                    timestamp_str,
                    accel[0], accel[1], accel[2],
                    gyro[0], gyro[1], gyro[2],
                    orient[0], orient[1], orient[2], orient[3]
                ])
                self._imu_file.flush()

            # Write TUM format timestamp
            if self._rgb_txt_file:
                self._rgb_txt_file.write(f"{timestamp_str} rgb/{frame_filename}\n")
                self._rgb_txt_file.flush()

            # Save intrinsics once per session
            if not self._intrinsics_saved and packet.camera_intrinsics:
                intrinsics_path = self.session_path / "intrinsics.json"
                with open(intrinsics_path, 'w') as f:
                    json.dump(packet.camera_intrinsics, f, indent=2)
                self._intrinsics_saved = True

            return True

        except Exception as e:
            print(f"Error processing frame: {e}")
            return False

    def get_stats(self) -> dict:
        """Get current session statistics."""
        if self.stats is None:
            return {}

        return {
            "session_id": self.stats.session_id,
            "frame_count": self.stats.frame_count,
            "duration_sec": round(self.stats.duration, 2),
            "fps": round(self.stats.fps, 2),
            "avg_latency_ms": round(self.stats.avg_latency_ms, 2),
            "bandwidth_mbps": round(self.stats.bandwidth_mbps, 2),
            "total_mb": round(self.stats.total_bytes / (1024 * 1024), 2),
            "queue_size": self._save_queue.qsize()
        }

    def end_session(self) -> dict:
        """
        End the current session and return final stats.

        Returns:
            Final session statistics.
        """
        stats = self.get_stats()

        # Wait for save queue to empty
        while not self._save_queue.empty():
            time.sleep(0.1)

        self._close_files()

        # Save final stats
        if self.session_path:
            stats_path = self.session_path / "session_stats.json"
            with open(stats_path, 'w') as f:
                json.dump(stats, f, indent=2)

        print(f"\nSession ended: {self.current_session}")
        print(f"  Frames: {stats.get('frame_count', 0)}")
        print(f"  Duration: {stats.get('duration_sec', 0):.1f}s")
        print(f"  Average FPS: {stats.get('fps', 0):.1f}")
        print(f"  Average Latency: {stats.get('avg_latency_ms', 0):.1f}ms")

        self.current_session = None
        self.session_path = None
        self.stats = None

        return stats

    def list_sessions(self) -> list:
        """List all capture sessions."""
        sessions = []
        for path in self.base_dir.iterdir():
            if path.is_dir() and path.name.startswith("session_"):
                stats_file = path / "session_stats.json"
                if stats_file.exists():
                    with open(stats_file) as f:
                        stats = json.load(f)
                else:
                    # Count frames manually
                    rgb_dir = path / "rgb"
                    frame_count = len(list(rgb_dir.glob("*.jpg"))) if rgb_dir.exists() else 0
                    stats = {"frame_count": frame_count}

                sessions.append({
                    "session_id": path.name,
                    "path": str(path),
                    **stats
                })

        return sorted(sessions, key=lambda x: x["session_id"], reverse=True)


def parse_frame_packet(data: dict, received_at: float) -> FramePacket:
    """
    Parse a JSON frame packet from the phone app.

    Args:
        data: The JSON data dictionary.
        received_at: Timestamp when the packet was received.

    Returns:
        Parsed FramePacket object.
    """
    # Decode base64 frame data
    frame_b64 = data.get("frame", "")
    frame_data = base64.b64decode(frame_b64)

    return FramePacket(
        timestamp=data.get("timestamp", received_at),
        frame_data=frame_data,
        imu=data.get("imu", {}),
        camera_intrinsics=data.get("camera_intrinsics", {}),
        received_at=received_at
    )

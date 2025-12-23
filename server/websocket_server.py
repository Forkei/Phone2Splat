"""
WebSocket Server Module for PhoneSplat

Handles WebSocket connections from the phone app and manages frame streaming.
"""

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Optional, Set, Callable, Any
from enum import Enum

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
except ImportError:
    print("Please install websockets: pip install websockets")
    raise

from frame_processor import FrameProcessor, FramePacket, parse_frame_packet


class MessageType(str, Enum):
    """Message types for client-server communication."""
    FRAME = "frame"
    CONTROL = "control"
    STATUS = "status"
    ERROR = "error"
    ACK = "ack"


class ControlCommand(str, Enum):
    """Control commands from the client."""
    START_SESSION = "start_session"
    END_SESSION = "end_session"
    PAUSE = "pause"
    RESUME = "resume"
    GET_STATUS = "get_status"
    PING = "ping"


@dataclass
class ClientConnection:
    """Represents a connected client."""
    websocket: WebSocketServerProtocol
    client_id: str
    connected_at: float = field(default_factory=time.time)
    is_streaming: bool = False
    is_paused: bool = False
    frames_received: int = 0
    last_frame_time: float = 0

    @property
    def connection_duration(self) -> float:
        return time.time() - self.connected_at


class PhoneSplatServer:
    """
    WebSocket server for receiving camera frames from the phone app.

    Features:
    - Accepts multiple client connections
    - Receives and processes frame packets
    - Manages capture sessions
    - Broadcasts status updates
    - Handles graceful shutdown
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8765,
        captures_dir: str = "captures"
    ):
        self.host = host
        self.port = port

        # Connected clients
        self.clients: dict[str, ClientConnection] = {}

        # Frame processor
        self.processor = FrameProcessor(base_dir=captures_dir)

        # Server state
        self._server = None
        self._running = False
        self._stats_task = None

        # Callbacks
        self._on_frame_callbacks: list[Callable[[FramePacket], Any]] = []
        self._on_status_callbacks: list[Callable[[dict], Any]] = []

    def on_frame(self, callback: Callable[[FramePacket], Any]):
        """Register a callback for when a frame is received."""
        self._on_frame_callbacks.append(callback)

    def on_status(self, callback: Callable[[dict], Any]):
        """Register a callback for status updates."""
        self._on_status_callbacks.append(callback)

    async def start(self):
        """Start the WebSocket server."""
        self.processor.start()
        self._running = True

        self._server = await websockets.serve(
            self._handle_client,
            self.host,
            self.port,
            ping_interval=20,
            ping_timeout=30,
            max_size=10 * 1024 * 1024,  # 10MB max message size
            compression=None  # Disable compression for lower latency
        )

        # Start stats reporting task
        self._stats_task = asyncio.create_task(self._stats_reporter())

        print(f"PhoneSplat Server started on ws://{self.host}:{self.port}")
        print(f"Captures directory: {self.processor.base_dir.absolute()}")
        print("Waiting for connections...")

    async def stop(self):
        """Stop the WebSocket server gracefully."""
        print("\nShutting down server...")
        self._running = False

        # Cancel stats task
        if self._stats_task:
            self._stats_task.cancel()
            try:
                await self._stats_task
            except asyncio.CancelledError:
                pass

        # Close all client connections
        for client in list(self.clients.values()):
            await self._send_message(client.websocket, {
                "type": MessageType.STATUS,
                "message": "Server shutting down"
            })
            await client.websocket.close()

        # Close server
        if self._server:
            self._server.close()
            await self._server.wait_closed()

        # Stop frame processor
        self.processor.stop()

        # End any active session
        if self.processor.current_session:
            self.processor.end_session()

        print("Server stopped.")

    async def _handle_client(self, websocket: WebSocketServerProtocol):
        """Handle a new client connection."""
        # Generate client ID
        client_id = f"client_{int(time.time() * 1000) % 100000}"
        client = ClientConnection(
            websocket=websocket,
            client_id=client_id
        )
        self.clients[client_id] = client

        remote = websocket.remote_address
        print(f"\nClient connected: {client_id} from {remote}")

        try:
            # Send welcome message
            await self._send_message(websocket, {
                "type": MessageType.STATUS,
                "client_id": client_id,
                "message": "Connected to PhoneSplat Server",
                "server_time": time.time()
            })

            # Process messages
            async for message in websocket:
                await self._process_message(client, message)

        except websockets.exceptions.ConnectionClosed as e:
            print(f"Client {client_id} disconnected: {e.reason if e.reason else 'Connection closed'}")

        except Exception as e:
            print(f"Error handling client {client_id}: {e}")
            await self._send_error(websocket, str(e))

        finally:
            # Cleanup
            del self.clients[client_id]
            print(f"Client {client_id} removed. Active clients: {len(self.clients)}")

    async def _process_message(self, client: ClientConnection, message: str | bytes):
        """Process an incoming message from a client."""
        received_at = time.time()

        try:
            # Parse JSON message
            if isinstance(message, bytes):
                message = message.decode('utf-8')

            data = json.loads(message)
            msg_type = data.get("type", MessageType.FRAME)

            if msg_type == MessageType.FRAME or "frame" in data:
                await self._handle_frame(client, data, received_at)

            elif msg_type == MessageType.CONTROL:
                await self._handle_control(client, data)

            else:
                print(f"Unknown message type: {msg_type}")

        except json.JSONDecodeError as e:
            await self._send_error(client.websocket, f"Invalid JSON: {e}")

        except Exception as e:
            print(f"Error processing message: {e}")
            await self._send_error(client.websocket, str(e))

    async def _handle_frame(self, client: ClientConnection, data: dict, received_at: float):
        """Handle an incoming frame packet."""
        if client.is_paused:
            return

        # Start session if needed
        if not client.is_streaming:
            client.is_streaming = True
            if not self.processor.current_session:
                self.processor.create_session()

        # Parse and process frame
        try:
            packet = parse_frame_packet(data, received_at)
            success = await self.processor.process_frame(packet)

            client.frames_received += 1
            client.last_frame_time = received_at

            # Call frame callbacks
            for callback in self._on_frame_callbacks:
                try:
                    result = callback(packet)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as e:
                    print(f"Frame callback error: {e}")

            # Send acknowledgment every 10 frames
            if client.frames_received % 10 == 0:
                stats = self.processor.get_stats()
                await self._send_message(client.websocket, {
                    "type": MessageType.ACK,
                    "frame_count": client.frames_received,
                    "stats": stats
                })

        except Exception as e:
            print(f"Error handling frame: {e}")

    async def _handle_control(self, client: ClientConnection, data: dict):
        """Handle a control command."""
        command = data.get("command")

        if command == ControlCommand.START_SESSION:
            session_id = data.get("session_id")
            self.processor.create_session(session_id)
            client.is_streaming = True
            client.is_paused = False

            await self._send_message(client.websocket, {
                "type": MessageType.STATUS,
                "command": command,
                "session_id": self.processor.current_session,
                "message": "Session started"
            })

        elif command == ControlCommand.END_SESSION:
            stats = self.processor.end_session()
            client.is_streaming = False

            await self._send_message(client.websocket, {
                "type": MessageType.STATUS,
                "command": command,
                "stats": stats,
                "message": "Session ended"
            })

        elif command == ControlCommand.PAUSE:
            client.is_paused = True
            await self._send_message(client.websocket, {
                "type": MessageType.STATUS,
                "command": command,
                "message": "Streaming paused"
            })

        elif command == ControlCommand.RESUME:
            client.is_paused = False
            await self._send_message(client.websocket, {
                "type": MessageType.STATUS,
                "command": command,
                "message": "Streaming resumed"
            })

        elif command == ControlCommand.GET_STATUS:
            stats = self.processor.get_stats()
            await self._send_message(client.websocket, {
                "type": MessageType.STATUS,
                "command": command,
                "stats": stats,
                "clients": len(self.clients),
                "session": self.processor.current_session
            })

        elif command == ControlCommand.PING:
            await self._send_message(client.websocket, {
                "type": MessageType.ACK,
                "command": "pong",
                "server_time": time.time(),
                "client_time": data.get("client_time", 0)
            })

        else:
            await self._send_error(client.websocket, f"Unknown command: {command}")

    async def _send_message(self, websocket: WebSocketServerProtocol, data: dict):
        """Send a JSON message to a client."""
        try:
            await websocket.send(json.dumps(data))
        except Exception as e:
            print(f"Error sending message: {e}")

    async def _send_error(self, websocket: WebSocketServerProtocol, error: str):
        """Send an error message to a client."""
        await self._send_message(websocket, {
            "type": MessageType.ERROR,
            "error": error
        })

    async def _stats_reporter(self):
        """Periodically report stats to console and callbacks."""
        last_frame_count = 0

        while self._running:
            await asyncio.sleep(5.0)

            if not self._running:
                break

            stats = self.processor.get_stats()
            if stats and stats.get("frame_count", 0) > 0:
                frame_count = stats["frame_count"]
                new_frames = frame_count - last_frame_count
                last_frame_count = frame_count

                print(f"\r[Stats] Frames: {frame_count} | "
                      f"FPS: {stats['fps']:.1f} | "
                      f"Latency: {stats['avg_latency_ms']:.0f}ms | "
                      f"Queue: {stats['queue_size']} | "
                      f"Size: {stats['total_mb']:.1f}MB", end="")

                # Call status callbacks
                for callback in self._on_status_callbacks:
                    try:
                        result = callback(stats)
                        if asyncio.iscoroutine(result):
                            await result
                    except Exception as e:
                        print(f"Status callback error: {e}")

    async def broadcast(self, message: dict):
        """Broadcast a message to all connected clients."""
        for client in self.clients.values():
            await self._send_message(client.websocket, message)

    def get_server_info(self) -> dict:
        """Get server information."""
        return {
            "host": self.host,
            "port": self.port,
            "running": self._running,
            "clients": len(self.clients),
            "session": self.processor.current_session,
            "stats": self.processor.get_stats()
        }


async def run_server(host: str = "0.0.0.0", port: int = 8765, captures_dir: str = "captures"):
    """
    Run the PhoneSplat server.

    Args:
        host: Host to bind to.
        port: Port to bind to.
        captures_dir: Directory for saving captures.
    """
    server = PhoneSplatServer(host=host, port=port, captures_dir=captures_dir)

    # Handle graceful shutdown
    loop = asyncio.get_event_loop()
    stop_event = asyncio.Event()

    def signal_handler():
        stop_event.set()

    # Note: Signal handlers don't work well on Windows, so we use keyboard interrupt
    try:
        await server.start()
        await stop_event.wait()
    except KeyboardInterrupt:
        print("\nReceived keyboard interrupt")
    finally:
        await server.stop()


if __name__ == "__main__":
    asyncio.run(run_server())

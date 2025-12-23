/**
 * PhoneSplat Type Definitions
 */

// IMU Data from device sensors
export interface IMUData {
  accel: [number, number, number];
  gyro: [number, number, number];
  orientation: [number, number, number, number]; // quaternion [qw, qx, qy, qz]
  timestamp: number;
}

// Camera intrinsics
export interface CameraIntrinsics {
  fx: number;
  fy: number;
  cx: number;
  cy: number;
  width: number;
  height: number;
}

// Frame packet sent to server
export interface FramePacket {
  type: 'frame';
  timestamp: number;
  frame: string; // base64 JPEG
  imu: Omit<IMUData, 'timestamp'>;
  camera_intrinsics: CameraIntrinsics;
}

// Control message types
export type ControlCommand =
  | 'start_session'
  | 'end_session'
  | 'pause'
  | 'resume'
  | 'get_status'
  | 'ping';

export interface ControlMessage {
  type: 'control';
  command: ControlCommand;
  session_id?: string;
  client_time?: number;
}

// Server response types
export interface ServerMessage {
  type: 'status' | 'ack' | 'error';
  message?: string;
  client_id?: string;
  server_time?: number;
  session_id?: string;
  stats?: SessionStats;
  error?: string;
  frame_count?: number;
}

export interface SessionStats {
  session_id: string;
  frame_count: number;
  duration_sec: number;
  fps: number;
  avg_latency_ms: number;
  bandwidth_mbps: number;
  total_mb: number;
  queue_size: number;
}

// Connection state
export type ConnectionState =
  | 'disconnected'
  | 'connecting'
  | 'connected'
  | 'reconnecting'
  | 'error';

// Capture state
export type CaptureState =
  | 'idle'
  | 'capturing'
  | 'paused';

// App settings
export interface AppSettings {
  serverHost: string;
  serverPort: number;
  targetFPS: 5 | 10 | 15 | 30;
  resolution: '480p' | '720p' | '1080p';
  jpegQuality: 0.6 | 0.8 | 0.85 | 0.95;
}

// Resolution dimensions - optimized for SLAM
export const RESOLUTIONS = {
  '480p': { width: 640, height: 480 },   // Best for SLAM - fast & sufficient detail
  '720p': { width: 1280, height: 720 },  // Higher detail but slower
  '1080p': { width: 1920, height: 1080 }, // Too slow for real-time
} as const;

// Default settings - optimized for MonoGS SLAM
export const DEFAULT_SETTINGS: AppSettings = {
  serverHost: '192.168.1.100',
  serverPort: 8765,
  targetFPS: 10,        // 10 FPS target for smooth tracking
  resolution: '480p',   // 640x480 - optimal for SLAM
  jpegQuality: 0.85,    // 85% quality - good balance
};

// Navigation types
export type RootStackParamList = {
  Connect: undefined;
  Scan: undefined;
};

/**
 * Camera capture hook for PhoneSplat
 */

import { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import { CameraView, CameraType, useCameraPermissions } from 'expo-camera';
import { CameraIntrinsics, RESOLUTIONS, FramePacket } from '../types';
import { createIMUReader } from './useIMU';

interface UseCameraOptions {
  targetFPS: number;
  resolution: '480p' | '720p' | '1080p';
  jpegQuality: number;
  onFrame?: (packet: FramePacket) => void;
}

interface UseCameraReturn {
  cameraRef: React.RefObject<CameraView>;
  hasPermission: boolean | null;
  requestPermission: () => Promise<void>;
  isCapturing: boolean;
  startCapture: () => void;
  stopCapture: () => void;
  frameCount: number;
  actualFPS: number;
  lastFrameSize: number;
  facing: CameraType;
  toggleFacing: () => void;
  onCameraReady: () => void;
  pictureSize: string;
}

export function useCamera(options: UseCameraOptions): UseCameraReturn {
  const { targetFPS, resolution, jpegQuality, onFrame } = options;

  const [permission, requestPermission] = useCameraPermissions();
  const [isCapturing, setIsCapturing] = useState(false);
  const [frameCount, setFrameCount] = useState(0);
  const [actualFPS, setActualFPS] = useState(0);
  const [lastFrameSize, setLastFrameSize] = useState(0);
  const [facing, setFacing] = useState<CameraType>('back');
  const [cameraReady, setCameraReady] = useState(false);

  const cameraRef = useRef<CameraView>(null);
  const captureIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const imuReaderRef = useRef<ReturnType<typeof createIMUReader> | null>(null);
  const frameCountRef = useRef(0);
  const startTimeRef = useRef(0);
  const fpsUpdateIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const captureLockRef = useRef(false); // Prevent overlapping captures
  const isCapturingStateRef = useRef(false); // Track capturing state without closure issues
  const onFrameRef = useRef(onFrame); // Ref to avoid stale closure

  // Initialize IMU reader
  useEffect(() => {
    imuReaderRef.current = createIMUReader();
    return () => {
      imuReaderRef.current?.stop();
    };
  }, []);

  // Keep onFrameRef updated to avoid stale closures
  useEffect(() => {
    onFrameRef.current = onFrame;
  }, [onFrame]);

  // Calculate camera intrinsics based on resolution
  const getIntrinsics = useCallback((): CameraIntrinsics => {
    const res = RESOLUTIONS[resolution];
    // Approximate focal length for typical phone camera
    // Assuming ~60-70 degree FOV
    const focalLength = res.width * 0.8;

    return {
      fx: focalLength,
      fy: focalLength,
      cx: res.width / 2,
      cy: res.height / 2,
      width: res.width,
      height: res.height,
    };
  }, [resolution]);

  // Get picture size string for camera (e.g., "1280x720")
  const pictureSize = useMemo(() => {
    const res = RESOLUTIONS[resolution];
    return `${res.width}x${res.height}`;
  }, [resolution]);

  const captureFrame = useCallback(async () => {
    // Use refs to avoid stale closure issues
    // Prevent overlapping captures and check camera is ready
    if (!cameraRef.current || !isCapturingStateRef.current || !cameraReady || captureLockRef.current) {
      return;
    }

    captureLockRef.current = true;
    const timestamp = Date.now() / 1000;

    try {
      // Capture at the configured pictureSize resolution
      const photo = await cameraRef.current.takePictureAsync({
        quality: jpegQuality,
        base64: true,
        shutterSound: false,
      });

      // Check if still capturing (user might have stopped during takePictureAsync)
      if (!isCapturingStateRef.current) {
        return;
      }

      if (!photo?.base64) {
        console.warn('No base64 in photo');
        return;
      }

      const imuData = imuReaderRef.current?.read() || {
        accel: [0, 0, 0] as [number, number, number],
        gyro: [0, 0, 0] as [number, number, number],
        orientation: [1, 0, 0, 0] as [number, number, number, number],
      };

      // Use actual captured dimensions for intrinsics
      const actualWidth = photo.width || RESOLUTIONS[resolution].width;
      const actualHeight = photo.height || RESOLUTIONS[resolution].height;
      const focalLength = Math.max(actualWidth, actualHeight) * 0.8;

      const packet: FramePacket = {
        type: 'frame',
        timestamp,
        frame: photo.base64,
        imu: imuData,
        camera_intrinsics: {
          fx: focalLength,
          fy: focalLength,
          cx: actualWidth / 2,
          cy: actualHeight / 2,
          width: actualWidth,
          height: actualHeight,
        },
      };

      frameCountRef.current += 1;
      setFrameCount(frameCountRef.current);
      setLastFrameSize(Math.round((photo.base64.length * 3) / 4 / 1024)); // KB

      // Use ref to get latest onFrame callback
      onFrameRef.current?.(packet);
    } catch (error) {
      console.error('Error capturing frame:', error);
    } finally {
      captureLockRef.current = false;
    }
  }, [cameraReady, jpegQuality, resolution]);

  const startCapture = useCallback(() => {
    if (isCapturing) return;

    console.log(`Starting capture at ${targetFPS} FPS`);

    // Start IMU
    imuReaderRef.current?.start(10);

    // Reset counters
    frameCountRef.current = 0;
    startTimeRef.current = Date.now();
    setFrameCount(0);
    setActualFPS(0);
    captureLockRef.current = false; // Reset lock

    // Set ref BEFORE state to ensure capture loop works immediately
    isCapturingStateRef.current = true;
    setIsCapturing(true);

    // Start capture interval
    const intervalMs = 1000 / targetFPS;
    captureIntervalRef.current = setInterval(captureFrame, intervalMs);

    // Start FPS calculation interval
    fpsUpdateIntervalRef.current = setInterval(() => {
      const elapsed = (Date.now() - startTimeRef.current) / 1000;
      if (elapsed > 0) {
        setActualFPS(Math.round((frameCountRef.current / elapsed) * 10) / 10);
      }
    }, 500);
  }, [isCapturing, targetFPS, captureFrame]);

  const stopCapture = useCallback(() => {
    if (!isCapturing) return;

    console.log('Stopping capture');

    // Clear ref FIRST to stop any in-flight captures
    isCapturingStateRef.current = false;
    setIsCapturing(false);

    if (captureIntervalRef.current) {
      clearInterval(captureIntervalRef.current);
      captureIntervalRef.current = null;
    }

    if (fpsUpdateIntervalRef.current) {
      clearInterval(fpsUpdateIntervalRef.current);
      fpsUpdateIntervalRef.current = null;
    }

    imuReaderRef.current?.stop();
  }, [isCapturing]);

  const toggleFacing = useCallback(() => {
    setFacing((prev) => (prev === 'back' ? 'front' : 'back'));
    setCameraReady(false); // Reset camera ready when switching
  }, []);

  const onCameraReady = useCallback(() => {
    console.log('Camera is ready');
    setCameraReady(true);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (captureIntervalRef.current) {
        clearInterval(captureIntervalRef.current);
      }
      if (fpsUpdateIntervalRef.current) {
        clearInterval(fpsUpdateIntervalRef.current);
      }
      imuReaderRef.current?.stop();
    };
  }, []);

  // Restart capture if settings change while capturing
  useEffect(() => {
    if (isCapturing && captureIntervalRef.current) {
      clearInterval(captureIntervalRef.current);
      const intervalMs = 1000 / targetFPS;
      captureIntervalRef.current = setInterval(captureFrame, intervalMs);
    }
  }, [targetFPS, isCapturing, captureFrame]);

  return {
    cameraRef,
    hasPermission: permission?.granted ?? null,
    requestPermission: async () => {
      await requestPermission();
    },
    isCapturing,
    startCapture,
    stopCapture,
    frameCount,
    actualFPS,
    lastFrameSize,
    facing,
    toggleFacing,
    onCameraReady,
    pictureSize,
  };
}

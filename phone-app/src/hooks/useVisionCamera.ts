/**
 * VisionCamera hook for fast frame capture
 * Uses takeSnapshot() - faster than expo-camera's takePictureAsync
 */

import { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import {
  Camera,
  useCameraDevice,
  useCameraPermission,
  CameraPosition,
} from 'react-native-vision-camera';
import * as FileSystem from 'expo-file-system/legacy';
import { CameraIntrinsics, RESOLUTIONS, FramePacket } from '../types';
import { createIMUReader } from './useIMU';

interface UseVisionCameraOptions {
  targetFPS: number;
  resolution: '480p' | '720p' | '1080p';
  jpegQuality: number;
  onFrame?: (packet: FramePacket) => void;
}

interface UseVisionCameraReturn {
  cameraRef: React.RefObject<Camera>;
  hasPermission: boolean;
  requestPermission: () => Promise<boolean>;
  isCapturing: boolean;
  startCapture: () => void;
  stopCapture: () => void;
  frameCount: number;
  actualFPS: number;
  lastFrameSize: number;
  facing: CameraPosition;
  toggleFacing: () => void;
  device: ReturnType<typeof useCameraDevice>;
  format: any;
}

export function useVisionCamera(options: UseVisionCameraOptions): UseVisionCameraReturn {
  const { targetFPS, resolution, jpegQuality, onFrame } = options;

  const { hasPermission, requestPermission } = useCameraPermission();
  const [isCapturing, setIsCapturing] = useState(false);
  const [frameCount, setFrameCount] = useState(0);
  const [actualFPS, setActualFPS] = useState(0);
  const [lastFrameSize, setLastFrameSize] = useState(0);
  const [facing, setFacing] = useState<CameraPosition>('back');

  const device = useCameraDevice(facing);

  const cameraRef = useRef<Camera>(null);
  const imuReaderRef = useRef<ReturnType<typeof createIMUReader> | null>(null);
  const frameCountRef = useRef(0);
  const startTimeRef = useRef(0);
  const fpsUpdateIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const captureLoopRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isCapturingStateRef = useRef(false);
  const onFrameRef = useRef(onFrame);

  // Get target resolution
  const targetRes = RESOLUTIONS[resolution];

  // Find best matching format
  const format = useMemo(() => {
    if (!device?.formats) return undefined;

    const sorted = [...device.formats].sort((a, b) => {
      const aDiff = Math.abs(a.videoWidth - targetRes.width) + Math.abs(a.videoHeight - targetRes.height);
      const bDiff = Math.abs(b.videoWidth - targetRes.width) + Math.abs(b.videoHeight - targetRes.height);
      return aDiff - bDiff;
    });

    const highFPSFormats = sorted.filter(f => f.maxFps >= 30);
    return highFPSFormats[0] || sorted[0];
  }, [device?.formats, targetRes]);

  // Initialize IMU reader
  useEffect(() => {
    imuReaderRef.current = createIMUReader();
    return () => {
      imuReaderRef.current?.stop();
    };
  }, []);

  // Keep onFrameRef updated
  useEffect(() => {
    onFrameRef.current = onFrame;
  }, [onFrame]);

  const captureFrame = useCallback(async () => {
    if (!cameraRef.current || !isCapturingStateRef.current) {
      return;
    }

    const captureStart = Date.now();
    const timestamp = Date.now() / 1000;

    try {
      // takeSnapshot grabs from preview buffer - much faster than takePhoto
      const snapshot = await cameraRef.current.takeSnapshot({
        quality: Math.round(jpegQuality * 100),
        skipMetadata: true,
      });

      if (!isCapturingStateRef.current || !snapshot?.path) {
        return;
      }

      // Read as base64
      const base64 = await FileSystem.readAsStringAsync(`file://${snapshot.path}`, {
        encoding: FileSystem.EncodingType.Base64,
      });

      // Delete without waiting
      FileSystem.deleteAsync(`file://${snapshot.path}`, { idempotent: true }).catch(() => {});

      const imuData = imuReaderRef.current?.read() || {
        accel: [0, 0, 0] as [number, number, number],
        gyro: [0, 0, 0] as [number, number, number],
        orientation: [1, 0, 0, 0] as [number, number, number, number],
      };

      const actualWidth = snapshot.width;
      const actualHeight = snapshot.height;
      const focalLength = Math.min(actualWidth, actualHeight) * 0.9;

      const packet: FramePacket = {
        type: 'frame',
        timestamp,
        frame: base64,
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
      setLastFrameSize(Math.round((base64.length * 3) / 4 / 1024));

      onFrameRef.current?.(packet);

      // Schedule next capture - adjust for capture time to maintain FPS
      if (isCapturingStateRef.current) {
        const captureTime = Date.now() - captureStart;
        const targetInterval = 1000 / targetFPS;
        const nextDelay = Math.max(10, targetInterval - captureTime);
        captureLoopRef.current = setTimeout(captureFrame, nextDelay);
      }
    } catch (error) {
      console.error('Error capturing frame:', error);
      // Retry on error
      if (isCapturingStateRef.current) {
        captureLoopRef.current = setTimeout(captureFrame, 100);
      }
    }
  }, [jpegQuality, targetFPS]);

  const startCapture = useCallback(() => {
    if (isCapturing) return;

    console.log(`Starting VisionCamera capture at ${targetFPS} FPS target`);

    imuReaderRef.current?.start(10);

    frameCountRef.current = 0;
    startTimeRef.current = Date.now();
    setFrameCount(0);
    setActualFPS(0);

    isCapturingStateRef.current = true;
    setIsCapturing(true);

    // Start capture loop
    captureFrame();

    // FPS counter
    fpsUpdateIntervalRef.current = setInterval(() => {
      const elapsed = (Date.now() - startTimeRef.current) / 1000;
      if (elapsed > 0) {
        setActualFPS(Math.round((frameCountRef.current / elapsed) * 10) / 10);
      }
    }, 500);
  }, [isCapturing, targetFPS, captureFrame]);

  const stopCapture = useCallback(() => {
    if (!isCapturing) return;

    console.log('Stopping VisionCamera capture');

    isCapturingStateRef.current = false;
    setIsCapturing(false);

    if (captureLoopRef.current) {
      clearTimeout(captureLoopRef.current);
      captureLoopRef.current = null;
    }

    if (fpsUpdateIntervalRef.current) {
      clearInterval(fpsUpdateIntervalRef.current);
      fpsUpdateIntervalRef.current = null;
    }

    imuReaderRef.current?.stop();
  }, [isCapturing]);

  const toggleFacing = useCallback(() => {
    setFacing((prev) => (prev === 'back' ? 'front' : 'back'));
  }, []);

  useEffect(() => {
    return () => {
      if (captureLoopRef.current) {
        clearTimeout(captureLoopRef.current);
      }
      if (fpsUpdateIntervalRef.current) {
        clearInterval(fpsUpdateIntervalRef.current);
      }
      imuReaderRef.current?.stop();
    };
  }, []);

  return {
    cameraRef,
    hasPermission,
    requestPermission,
    isCapturing,
    startCapture,
    stopCapture,
    frameCount,
    actualFPS,
    lastFrameSize,
    facing,
    toggleFacing,
    device,
    format,
  };
}

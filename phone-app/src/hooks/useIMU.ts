/**
 * IMU (Accelerometer, Gyroscope) hook for PhoneSplat
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  Accelerometer,
  Gyroscope,
  DeviceMotion,
  AccelerometerMeasurement,
  GyroscopeMeasurement,
  DeviceMotionMeasurement,
} from 'expo-sensors';
import { IMUData } from '../types';

interface UseIMUOptions {
  updateInterval?: number; // ms, default 10 (100Hz)
  enabled?: boolean;
}

interface UseIMUReturn {
  imuData: IMUData | null;
  isAvailable: boolean;
  error: string | null;
  start: () => void;
  stop: () => void;
}

export function useIMU(options: UseIMUOptions = {}): UseIMUReturn {
  const { updateInterval = 10, enabled = true } = options;

  const [isAvailable, setIsAvailable] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Use refs for sensor data to avoid re-renders on every update
  const accelRef = useRef<AccelerometerMeasurement>({ x: 0, y: 0, z: 0 });
  const gyroRef = useRef<GyroscopeMeasurement>({ x: 0, y: 0, z: 0 });
  const orientationRef = useRef<[number, number, number, number]>([1, 0, 0, 0]);
  const timestampRef = useRef<number>(Date.now() / 1000);

  // State for external access (updated less frequently)
  const [imuData, setImuData] = useState<IMUData | null>(null);

  // Subscription refs
  const accelSubRef = useRef<ReturnType<typeof Accelerometer.addListener> | null>(null);
  const gyroSubRef = useRef<ReturnType<typeof Gyroscope.addListener> | null>(null);
  const motionSubRef = useRef<ReturnType<typeof DeviceMotion.addListener> | null>(null);
  const updateIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Check sensor availability
  useEffect(() => {
    const checkAvailability = async () => {
      try {
        const [accelAvailable, gyroAvailable] = await Promise.all([
          Accelerometer.isAvailableAsync(),
          Gyroscope.isAvailableAsync(),
        ]);

        if (accelAvailable && gyroAvailable) {
          setIsAvailable(true);
        } else {
          setError('Accelerometer or Gyroscope not available');
          setIsAvailable(false);
        }
      } catch (err) {
        setError(String(err));
        setIsAvailable(false);
      }
    };

    checkAvailability();
  }, []);

  const start = useCallback(() => {
    if (!isAvailable) {
      console.warn('IMU sensors not available');
      return;
    }

    // Set update intervals
    Accelerometer.setUpdateInterval(updateInterval);
    Gyroscope.setUpdateInterval(updateInterval);

    // Subscribe to accelerometer
    accelSubRef.current = Accelerometer.addListener((data) => {
      accelRef.current = data;
      timestampRef.current = Date.now() / 1000;
    });

    // Subscribe to gyroscope
    gyroSubRef.current = Gyroscope.addListener((data) => {
      gyroRef.current = data;
    });

    // Try to subscribe to DeviceMotion for orientation
    DeviceMotion.isAvailableAsync().then((available) => {
      if (available) {
        DeviceMotion.setUpdateInterval(updateInterval);
        motionSubRef.current = DeviceMotion.addListener((data) => {
          if (data.rotation) {
            // Convert to quaternion [qw, qx, qy, qz]
            // DeviceMotion gives rotation in terms of alpha, beta, gamma
            // For simplicity, we'll use a basic conversion
            const { alpha, beta, gamma } = data.rotation;

            // Convert Euler angles to quaternion
            const cy = Math.cos((alpha || 0) * 0.5);
            const sy = Math.sin((alpha || 0) * 0.5);
            const cp = Math.cos((beta || 0) * 0.5);
            const sp = Math.sin((beta || 0) * 0.5);
            const cr = Math.cos((gamma || 0) * 0.5);
            const sr = Math.sin((gamma || 0) * 0.5);

            orientationRef.current = [
              cr * cp * cy + sr * sp * sy, // qw
              sr * cp * cy - cr * sp * sy, // qx
              cr * sp * cy + sr * cp * sy, // qy
              cr * cp * sy - sr * sp * cy, // qz
            ];
          }
        });
      }
    });

    // Update state periodically (less frequently than sensor updates)
    updateIntervalRef.current = setInterval(() => {
      setImuData({
        accel: [accelRef.current.x, accelRef.current.y, accelRef.current.z],
        gyro: [gyroRef.current.x, gyroRef.current.y, gyroRef.current.z],
        orientation: orientationRef.current,
        timestamp: timestampRef.current,
      });
    }, 50); // Update state at 20Hz for UI

    console.log('IMU sensors started');
  }, [isAvailable, updateInterval]);

  const stop = useCallback(() => {
    if (accelSubRef.current) {
      accelSubRef.current.remove();
      accelSubRef.current = null;
    }
    if (gyroSubRef.current) {
      gyroSubRef.current.remove();
      gyroSubRef.current = null;
    }
    if (motionSubRef.current) {
      motionSubRef.current.remove();
      motionSubRef.current = null;
    }
    if (updateIntervalRef.current) {
      clearInterval(updateIntervalRef.current);
      updateIntervalRef.current = null;
    }

    console.log('IMU sensors stopped');
  }, []);

  // Get current IMU reading (for frame capture)
  const getCurrentReading = useCallback((): IMUData => {
    return {
      accel: [accelRef.current.x, accelRef.current.y, accelRef.current.z],
      gyro: [gyroRef.current.x, gyroRef.current.y, gyroRef.current.z],
      orientation: orientationRef.current,
      timestamp: timestampRef.current,
    };
  }, []);

  // Auto-start/stop based on enabled prop
  useEffect(() => {
    if (enabled && isAvailable) {
      start();
    } else {
      stop();
    }

    return () => {
      stop();
    };
  }, [enabled, isAvailable, start, stop]);

  return {
    imuData,
    isAvailable,
    error,
    start,
    stop,
  };
}

/**
 * Get current IMU reading synchronously (uses refs)
 * This is a separate export for use in frame capture
 */
export function createIMUReader() {
  const accelRef = { current: { x: 0, y: 0, z: 0 } };
  const gyroRef = { current: { x: 0, y: 0, z: 0 } };
  const orientationRef = { current: [1, 0, 0, 0] as [number, number, number, number] };

  let accelSub: ReturnType<typeof Accelerometer.addListener> | null = null;
  let gyroSub: ReturnType<typeof Gyroscope.addListener> | null = null;
  let motionSub: ReturnType<typeof DeviceMotion.addListener> | null = null;

  return {
    start: async (updateInterval = 10) => {
      Accelerometer.setUpdateInterval(updateInterval);
      Gyroscope.setUpdateInterval(updateInterval);

      accelSub = Accelerometer.addListener((data) => {
        accelRef.current = data;
      });

      gyroSub = Gyroscope.addListener((data) => {
        gyroRef.current = data;
      });

      const motionAvailable = await DeviceMotion.isAvailableAsync();
      if (motionAvailable) {
        DeviceMotion.setUpdateInterval(updateInterval);
        motionSub = DeviceMotion.addListener((data) => {
          if (data.rotation) {
            const { alpha, beta, gamma } = data.rotation;
            const cy = Math.cos((alpha || 0) * 0.5);
            const sy = Math.sin((alpha || 0) * 0.5);
            const cp = Math.cos((beta || 0) * 0.5);
            const sp = Math.sin((beta || 0) * 0.5);
            const cr = Math.cos((gamma || 0) * 0.5);
            const sr = Math.sin((gamma || 0) * 0.5);

            orientationRef.current = [
              cr * cp * cy + sr * sp * sy,
              sr * cp * cy - cr * sp * sy,
              cr * sp * cy + sr * cp * sy,
              cr * cp * sy - sr * sp * cy,
            ];
          }
        });
      }
    },

    stop: () => {
      accelSub?.remove();
      gyroSub?.remove();
      motionSub?.remove();
    },

    read: (): Omit<IMUData, 'timestamp'> => ({
      accel: [accelRef.current.x, accelRef.current.y, accelRef.current.z],
      gyro: [gyroRef.current.x, gyroRef.current.y, gyroRef.current.z],
      orientation: orientationRef.current,
    }),
  };
}

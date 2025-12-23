/**
 * Scan Screen
 * Main scanning interface with camera and controls
 */

import React, { useState, useCallback, useEffect, useRef } from 'react';
import { View, StyleSheet, Alert, BackHandler } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import {
  RootStackParamList,
  AppSettings,
  CaptureState,
  ConnectionState,
  FramePacket,
  SessionStats,
  DEFAULT_SETTINGS,
} from '../types';
import { VisionCameraPreview } from '../components/VisionCameraView';
import { StatusOverlay } from '../components/StatusOverlay';
import { ControlBar } from '../components/ControlBar';
import { SettingsModal } from '../components/SettingsModal';
import { useVisionCamera } from '../hooks/useVisionCamera';

type Props = NativeStackScreenProps<RootStackParamList, 'Scan'>;

interface ScanScreenProps extends Props {
  connectionState: ConnectionState;
  serverStats: SessionStats | null;
  onSendFrame: (packet: FramePacket) => boolean;
  onSendControl: (command: string) => void;
  onDisconnect: () => void;
  framesSent: number;
}

export function ScanScreen({
  navigation,
  connectionState,
  serverStats,
  onSendFrame,
  onSendControl,
  onDisconnect,
  framesSent,
}: ScanScreenProps) {
  const [settings, setSettings] = useState<AppSettings>(DEFAULT_SETTINGS);
  const [captureState, setCaptureState] = useState<CaptureState>('idle');
  const [settingsVisible, setSettingsVisible] = useState(false);
  const [sessionDuration, setSessionDuration] = useState(0);

  const sessionStartRef = useRef<number>(0);
  const durationIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Use refs to avoid stale closure issues in callbacks
  const captureStateRef = useRef<CaptureState>('idle');
  const connectionStateRef = useRef<ConnectionState>(connectionState);

  // Keep refs in sync with state
  useEffect(() => {
    captureStateRef.current = captureState;
  }, [captureState]);

  useEffect(() => {
    connectionStateRef.current = connectionState;
  }, [connectionState]);

  // Handle frame from camera - use refs to avoid stale closures
  const handleFrame = useCallback(
    (packet: FramePacket) => {
      if (connectionStateRef.current === 'connected' && captureStateRef.current === 'capturing') {
        onSendFrame(packet);
      }
    },
    [onSendFrame]
  );

  // VisionCamera hook - faster than expo-camera
  const {
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
  } = useVisionCamera({
    targetFPS: settings.targetFPS,
    resolution: settings.resolution,
    jpegQuality: settings.jpegQuality,
    onFrame: handleFrame,
  });

  // Handle disconnect
  useEffect(() => {
    if (connectionState === 'disconnected' || connectionState === 'error') {
      Alert.alert(
        'Disconnected',
        'Lost connection to server. Returning to connection screen.',
        [{ text: 'OK', onPress: () => navigation.replace('Connect') }]
      );
    }
  }, [connectionState, navigation]);

  // Back button handling
  useEffect(() => {
    const handleBack = () => {
      if (captureState !== 'idle') {
        Alert.alert(
          'Stop Scanning?',
          'You are currently scanning. Do you want to stop and go back?',
          [
            { text: 'Cancel', style: 'cancel' },
            {
              text: 'Stop & Go Back',
              style: 'destructive',
              onPress: () => {
                handleStop();
                onDisconnect();
                navigation.replace('Connect');
              },
            },
          ]
        );
        return true;
      }
      onDisconnect();
      navigation.replace('Connect');
      return true;
    };

    const subscription = BackHandler.addEventListener('hardwareBackPress', handleBack);
    return () => subscription.remove();
  }, [captureState, navigation, onDisconnect]);

  // Duration timer
  useEffect(() => {
    if (captureState === 'capturing') {
      durationIntervalRef.current = setInterval(() => {
        setSessionDuration((Date.now() - sessionStartRef.current) / 1000);
      }, 100);
    } else if (captureState === 'idle') {
      if (durationIntervalRef.current) {
        clearInterval(durationIntervalRef.current);
        durationIntervalRef.current = null;
      }
      setSessionDuration(0);
    }

    return () => {
      if (durationIntervalRef.current) {
        clearInterval(durationIntervalRef.current);
      }
    };
  }, [captureState]);

  const handleStart = useCallback(() => {
    sessionStartRef.current = Date.now();
    // Set ref BEFORE state to avoid stale closure issues
    captureStateRef.current = 'capturing';
    setCaptureState('capturing');
    onSendControl('start_session');
    startCapture();
  }, [onSendControl, startCapture]);

  const handlePause = useCallback(() => {
    captureStateRef.current = 'paused';
    setCaptureState('paused');
    onSendControl('pause');
    stopCapture();
  }, [onSendControl, stopCapture]);

  const handleResume = useCallback(() => {
    captureStateRef.current = 'capturing';
    setCaptureState('capturing');
    onSendControl('resume');
    startCapture();
  }, [onSendControl, startCapture]);

  const handleStop = useCallback(() => {
    captureStateRef.current = 'idle';
    setCaptureState('idle');
    onSendControl('end_session');
    stopCapture();

    // Show summary
    if (serverStats) {
      Alert.alert(
        'Session Complete',
        `Captured ${serverStats.frame_count} frames\n` +
          `Duration: ${serverStats.duration_sec.toFixed(1)}s\n` +
          `Average FPS: ${serverStats.fps.toFixed(1)}\n` +
          `Total size: ${serverStats.total_mb.toFixed(1)} MB`,
        [{ text: 'OK' }]
      );
    }
  }, [onSendControl, stopCapture, serverStats]);

  const handleSettings = useCallback(() => {
    if (captureState === 'idle') {
      setSettingsVisible(true);
    } else {
      Alert.alert(
        'Cannot Change Settings',
        'Stop the current session to change settings.',
        [{ text: 'OK' }]
      );
    }
  }, [captureState]);

  return (
    <View style={styles.container}>
      {/* Camera preview - VisionCamera */}
      <VisionCameraPreview
        ref={cameraRef}
        device={device}
        format={format}
        facing={facing}
        hasPermission={hasPermission}
        onRequestPermission={requestPermission}
        isActive={true}
      />

      {/* Status overlay */}
      <StatusOverlay
        connectionState={connectionState}
        isCapturing={captureState === 'capturing'}
        frameCount={framesSent}
        actualFPS={actualFPS}
        targetFPS={settings.targetFPS}
        lastFrameSize={lastFrameSize}
        serverStats={serverStats}
        sessionDuration={sessionDuration}
      />

      {/* Control bar */}
      <ControlBar
        connectionState={connectionState}
        captureState={captureState}
        onStart={handleStart}
        onPause={handlePause}
        onResume={handleResume}
        onStop={handleStop}
        onSettings={handleSettings}
      />

      {/* Settings modal */}
      <SettingsModal
        visible={settingsVisible}
        settings={settings}
        onClose={() => setSettingsVisible(false)}
        onSettingsChange={setSettings}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000000',
  },
});

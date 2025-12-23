/**
 * Control Bar Component
 * Start/Stop/Pause controls for scanning
 */

import React from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
} from 'react-native';
import * as Haptics from 'expo-haptics';
import { CaptureState, ConnectionState } from '../types';

interface ControlBarProps {
  connectionState: ConnectionState;
  captureState: CaptureState;
  onStart: () => void;
  onPause: () => void;
  onResume: () => void;
  onStop: () => void;
  onSettings: () => void;
}

export function ControlBar({
  connectionState,
  captureState,
  onStart,
  onPause,
  onResume,
  onStop,
  onSettings,
}: ControlBarProps) {
  const isConnected = connectionState === 'connected';
  const isIdle = captureState === 'idle';
  const isCapturing = captureState === 'capturing';
  const isPaused = captureState === 'paused';

  const handlePress = async (action: () => void) => {
    try {
      await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    } catch {
      // Haptics not available
    }
    action();
  };

  return (
    <View style={styles.container}>
      {/* Settings button */}
      <TouchableOpacity
        style={styles.settingsButton}
        onPress={() => handlePress(onSettings)}
      >
        <Text style={styles.settingsIcon}>...</Text>
      </TouchableOpacity>

      {/* Main controls */}
      <View style={styles.mainControls}>
        {isIdle ? (
          // Start button
          <TouchableOpacity
            style={[
              styles.button,
              styles.startButton,
              !isConnected && styles.buttonDisabled,
            ]}
            onPress={() => handlePress(onStart)}
            disabled={!isConnected}
          >
            <View style={styles.startButtonInner} />
          </TouchableOpacity>
        ) : (
          // Pause/Resume and Stop buttons
          <View style={styles.activeControls}>
            {/* Pause/Resume */}
            <TouchableOpacity
              style={[styles.button, styles.pauseButton]}
              onPress={() => handlePress(isPaused ? onResume : onPause)}
            >
              {isPaused ? (
                <View style={styles.playIcon} />
              ) : (
                <View style={styles.pauseIcon}>
                  <View style={styles.pauseBar} />
                  <View style={styles.pauseBar} />
                </View>
              )}
            </TouchableOpacity>

            {/* Stop */}
            <TouchableOpacity
              style={[styles.button, styles.stopButton]}
              onPress={() => handlePress(onStop)}
            >
              <View style={styles.stopIcon} />
            </TouchableOpacity>
          </View>
        )}
      </View>

      {/* Status text */}
      <View style={styles.statusContainer}>
        {!isConnected ? (
          <Text style={styles.statusText}>Not connected</Text>
        ) : isIdle ? (
          <Text style={styles.statusText}>Ready to scan</Text>
        ) : isCapturing ? (
          <Text style={[styles.statusText, styles.activeText]}>Scanning...</Text>
        ) : (
          <Text style={[styles.statusText, styles.pausedText]}>Paused</Text>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    paddingBottom: 40,
    paddingHorizontal: 20,
    paddingTop: 20,
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
  },
  settingsButton: {
    position: 'absolute',
    top: 20,
    right: 20,
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  settingsIcon: {
    color: '#ffffff',
    fontSize: 20,
    fontWeight: 'bold',
  },
  mainControls: {
    alignItems: 'center',
    marginBottom: 16,
  },
  button: {
    width: 72,
    height: 72,
    borderRadius: 36,
    justifyContent: 'center',
    alignItems: 'center',
  },
  startButton: {
    backgroundColor: 'transparent',
    borderWidth: 4,
    borderColor: '#ffffff',
  },
  startButtonInner: {
    width: 52,
    height: 52,
    borderRadius: 26,
    backgroundColor: '#4ade80',
  },
  buttonDisabled: {
    opacity: 0.4,
  },
  activeControls: {
    flexDirection: 'row',
    gap: 32,
  },
  pauseButton: {
    backgroundColor: '#fbbf24',
  },
  pauseIcon: {
    flexDirection: 'row',
    gap: 8,
  },
  pauseBar: {
    width: 8,
    height: 24,
    backgroundColor: '#000000',
    borderRadius: 2,
  },
  playIcon: {
    width: 0,
    height: 0,
    marginLeft: 4,
    borderLeftWidth: 20,
    borderTopWidth: 12,
    borderBottomWidth: 12,
    borderLeftColor: '#000000',
    borderTopColor: 'transparent',
    borderBottomColor: 'transparent',
  },
  stopButton: {
    backgroundColor: '#ef4444',
  },
  stopIcon: {
    width: 24,
    height: 24,
    backgroundColor: '#000000',
    borderRadius: 4,
  },
  statusContainer: {
    alignItems: 'center',
  },
  statusText: {
    color: '#9ca3af',
    fontSize: 16,
  },
  activeText: {
    color: '#4ade80',
  },
  pausedText: {
    color: '#fbbf24',
  },
});

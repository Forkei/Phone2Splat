/**
 * Status Overlay Component
 * Displays connection status, FPS, frame count, and other stats
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { ConnectionState, SessionStats } from '../types';

interface StatusOverlayProps {
  connectionState: ConnectionState;
  isCapturing: boolean;
  frameCount: number;
  actualFPS: number;
  targetFPS: number;
  lastFrameSize: number;
  serverStats: SessionStats | null;
  sessionDuration: number;
}

export function StatusOverlay({
  connectionState,
  isCapturing,
  frameCount,
  actualFPS,
  targetFPS,
  lastFrameSize,
  serverStats,
  sessionDuration,
}: StatusOverlayProps) {
  const getConnectionColor = () => {
    switch (connectionState) {
      case 'connected':
        return '#4ade80'; // green
      case 'connecting':
      case 'reconnecting':
        return '#fbbf24'; // yellow
      case 'error':
        return '#ef4444'; // red
      default:
        return '#6b7280'; // gray
    }
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <View style={styles.container}>
      {/* Top status bar */}
      <View style={styles.topBar}>
        {/* Connection indicator */}
        <View style={styles.statusItem}>
          <View style={[styles.statusDot, { backgroundColor: getConnectionColor() }]} />
          <Text style={styles.statusText}>
            {connectionState === 'connected' ? 'Connected' : connectionState}
          </Text>
        </View>

        {/* Session duration */}
        {isCapturing && (
          <View style={styles.statusItem}>
            <Text style={styles.recordingDot}>REC</Text>
            <Text style={styles.statusText}>{formatDuration(sessionDuration)}</Text>
          </View>
        )}
      </View>

      {/* Stats panel */}
      <View style={styles.statsPanel}>
        <View style={styles.statRow}>
          <Text style={styles.statLabel}>FPS</Text>
          <Text style={styles.statValue}>
            {actualFPS.toFixed(1)}
            <Text style={styles.statUnit}> / {targetFPS}</Text>
          </Text>
        </View>

        <View style={styles.statRow}>
          <Text style={styles.statLabel}>Frames</Text>
          <Text style={styles.statValue}>{frameCount}</Text>
        </View>

        <View style={styles.statRow}>
          <Text style={styles.statLabel}>Size</Text>
          <Text style={styles.statValue}>
            {lastFrameSize}
            <Text style={styles.statUnit}> KB</Text>
          </Text>
        </View>

        {serverStats && (
          <>
            <View style={styles.divider} />
            <View style={styles.statRow}>
              <Text style={styles.statLabel}>Latency</Text>
              <Text style={styles.statValue}>
                {serverStats.avg_latency_ms.toFixed(0)}
                <Text style={styles.statUnit}> ms</Text>
              </Text>
            </View>
            <View style={styles.statRow}>
              <Text style={styles.statLabel}>Saved</Text>
              <Text style={styles.statValue}>
                {serverStats.total_mb.toFixed(1)}
                <Text style={styles.statUnit}> MB</Text>
              </Text>
            </View>
          </>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    padding: 16,
    paddingTop: 50, // Account for status bar
  },
  topBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  statusItem: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
  },
  statusDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    marginRight: 8,
  },
  statusText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '500',
  },
  recordingDot: {
    color: '#ef4444',
    fontSize: 12,
    fontWeight: 'bold',
    marginRight: 8,
  },
  statsPanel: {
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    borderRadius: 12,
    padding: 12,
    alignSelf: 'flex-start',
    minWidth: 120,
  },
  statRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 4,
  },
  statLabel: {
    color: '#9ca3af',
    fontSize: 12,
    marginRight: 16,
  },
  statValue: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '600',
    fontVariant: ['tabular-nums'],
  },
  statUnit: {
    color: '#9ca3af',
    fontSize: 12,
    fontWeight: '400',
  },
  divider: {
    height: 1,
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    marginVertical: 8,
  },
});

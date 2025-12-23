/**
 * Camera View Component
 * Full-screen camera preview with frame capture
 */

import React, { forwardRef } from 'react';
import { View, StyleSheet, Text } from 'react-native';
import { CameraView as ExpoCameraView, CameraType } from 'expo-camera';

interface CameraViewProps {
  facing: CameraType;
  hasPermission: boolean | null;
  onRequestPermission: () => void;
  onCameraReady?: () => void;
  pictureSize?: string;
}

export const CameraPreview = forwardRef<ExpoCameraView, CameraViewProps>(
  ({ facing, hasPermission, onRequestPermission, onCameraReady, pictureSize }, ref) => {
    if (hasPermission === null) {
      return (
        <View style={styles.container}>
          <View style={styles.messageContainer}>
            <Text style={styles.messageText}>Checking camera permission...</Text>
          </View>
        </View>
      );
    }

    if (hasPermission === false) {
      return (
        <View style={styles.container}>
          <View style={styles.messageContainer}>
            <Text style={styles.messageTitle}>Camera Access Required</Text>
            <Text style={styles.messageText}>
              PhoneSplat needs camera access to capture frames for 3D reconstruction.
            </Text>
            <Text style={styles.permissionButton} onPress={onRequestPermission}>
              Grant Permission
            </Text>
          </View>
        </View>
      );
    }

    return (
      <View style={styles.container}>
        <ExpoCameraView
          ref={ref}
          style={styles.camera}
          facing={facing}
          animateShutter={false}
          onCameraReady={onCameraReady}
          pictureSize={pictureSize}
        />
      </View>
    );
  }
);

CameraPreview.displayName = 'CameraPreview';

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000000',
  },
  camera: {
    flex: 1,
  },
  messageContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
  },
  messageTitle: {
    color: '#ffffff',
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: 16,
    textAlign: 'center',
  },
  messageText: {
    color: '#9ca3af',
    fontSize: 16,
    textAlign: 'center',
    marginBottom: 24,
  },
  permissionButton: {
    color: '#4ade80',
    fontSize: 18,
    fontWeight: '600',
  },
});

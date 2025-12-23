/**
 * VisionCamera View Component
 * Full-screen camera preview using react-native-vision-camera
 */

import React, { forwardRef } from 'react';
import { View, StyleSheet, Text, TouchableOpacity } from 'react-native';
import { Camera, CameraPosition } from 'react-native-vision-camera';

interface VisionCameraViewProps {
  device: any;
  format: any;
  facing: CameraPosition;
  hasPermission: boolean;
  onRequestPermission: () => void;
  isActive?: boolean;
}

export const VisionCameraPreview = forwardRef<Camera, VisionCameraViewProps>(
  ({ device, format, facing, hasPermission, onRequestPermission, isActive = true }, ref) => {
    if (!hasPermission) {
      return (
        <View style={styles.container}>
          <View style={styles.messageContainer}>
            <Text style={styles.messageTitle}>Camera Access Required</Text>
            <Text style={styles.messageText}>
              PhoneSplat needs camera access to capture frames for 3D reconstruction.
            </Text>
            <TouchableOpacity onPress={onRequestPermission}>
              <Text style={styles.permissionButton}>Grant Permission</Text>
            </TouchableOpacity>
          </View>
        </View>
      );
    }

    if (!device) {
      return (
        <View style={styles.container}>
          <View style={styles.messageContainer}>
            <Text style={styles.messageText}>No camera device found</Text>
          </View>
        </View>
      );
    }

    return (
      <View style={styles.container}>
        <Camera
          ref={ref}
          style={styles.camera}
          device={device}
          format={format}
          isActive={isActive}
          photo={true}
          enableZoomGesture={false}
        />
      </View>
    );
  }
);

VisionCameraPreview.displayName = 'VisionCameraPreview';

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

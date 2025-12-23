/**
 * Settings Modal Component
 * Configure FPS, resolution, and quality
 */

import React from 'react';
import {
  View,
  Text,
  Modal,
  TouchableOpacity,
  StyleSheet,
  Pressable,
} from 'react-native';
import { AppSettings } from '../types';

interface SettingsModalProps {
  visible: boolean;
  settings: AppSettings;
  onClose: () => void;
  onSettingsChange: (settings: AppSettings) => void;
}

type FPSOption = 5 | 10 | 15 | 30;
type ResolutionOption = '480p' | '720p' | '1080p';
type QualityOption = 0.6 | 0.8 | 0.95;

const FPS_OPTIONS: FPSOption[] = [5, 10, 15, 30];
const RESOLUTION_OPTIONS: ResolutionOption[] = ['480p', '720p', '1080p'];
const QUALITY_OPTIONS: { value: QualityOption; label: string }[] = [
  { value: 0.6, label: 'Low (60%)' },
  { value: 0.8, label: 'Medium (80%)' },
  { value: 0.95, label: 'High (95%)' },
];

export function SettingsModal({
  visible,
  settings,
  onClose,
  onSettingsChange,
}: SettingsModalProps) {
  const updateSetting = <K extends keyof AppSettings>(
    key: K,
    value: AppSettings[K]
  ) => {
    onSettingsChange({ ...settings, [key]: value });
  };

  return (
    <Modal
      visible={visible}
      animationType="slide"
      transparent
      onRequestClose={onClose}
    >
      <Pressable style={styles.overlay} onPress={onClose}>
        <Pressable style={styles.container} onPress={(e) => e.stopPropagation()}>
          <View style={styles.header}>
            <Text style={styles.title}>Settings</Text>
            <TouchableOpacity onPress={onClose}>
              <Text style={styles.closeButton}>Done</Text>
            </TouchableOpacity>
          </View>

          {/* Target FPS */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Target FPS</Text>
            <View style={styles.optionRow}>
              {FPS_OPTIONS.map((fps) => (
                <TouchableOpacity
                  key={fps}
                  style={[
                    styles.option,
                    settings.targetFPS === fps && styles.optionSelected,
                  ]}
                  onPress={() => updateSetting('targetFPS', fps)}
                >
                  <Text
                    style={[
                      styles.optionText,
                      settings.targetFPS === fps && styles.optionTextSelected,
                    ]}
                  >
                    {fps}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
            <Text style={styles.hint}>
              Higher FPS = more data but smoother reconstruction
            </Text>
          </View>

          {/* Resolution */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Resolution</Text>
            <View style={styles.optionRow}>
              {RESOLUTION_OPTIONS.map((res) => (
                <TouchableOpacity
                  key={res}
                  style={[
                    styles.option,
                    settings.resolution === res && styles.optionSelected,
                  ]}
                  onPress={() => updateSetting('resolution', res)}
                >
                  <Text
                    style={[
                      styles.optionText,
                      settings.resolution === res && styles.optionTextSelected,
                    ]}
                  >
                    {res}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
            <Text style={styles.hint}>
              Higher resolution = better detail but more bandwidth
            </Text>
          </View>

          {/* JPEG Quality */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>JPEG Quality</Text>
            <View style={styles.optionRow}>
              {QUALITY_OPTIONS.map(({ value, label }) => (
                <TouchableOpacity
                  key={value}
                  style={[
                    styles.option,
                    styles.optionWide,
                    settings.jpegQuality === value && styles.optionSelected,
                  ]}
                  onPress={() => updateSetting('jpegQuality', value)}
                >
                  <Text
                    style={[
                      styles.optionText,
                      settings.jpegQuality === value && styles.optionTextSelected,
                    ]}
                  >
                    {label}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>

          {/* Bandwidth estimate */}
          <View style={styles.estimateContainer}>
            <Text style={styles.estimateLabel}>Estimated bandwidth:</Text>
            <Text style={styles.estimateValue}>
              {estimateBandwidth(settings)} Mbps
            </Text>
          </View>
        </Pressable>
      </Pressable>
    </Modal>
  );
}

function estimateBandwidth(settings: AppSettings): string {
  // Rough estimates for JPEG frame sizes
  const baseSizes: Record<string, number> = {
    '480p': 30,
    '720p': 80,
    '1080p': 200,
  };

  const qualityMultipliers: Record<number, number> = {
    0.6: 0.6,
    0.8: 1.0,
    0.95: 1.5,
  };

  const frameSize = baseSizes[settings.resolution] * qualityMultipliers[settings.jpegQuality];
  const bandwidth = (frameSize * settings.targetFPS * 8) / 1000;

  return bandwidth.toFixed(1);
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'flex-end',
  },
  container: {
    backgroundColor: '#1f2937',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    padding: 20,
    paddingBottom: 40,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 24,
  },
  title: {
    color: '#ffffff',
    fontSize: 20,
    fontWeight: 'bold',
  },
  closeButton: {
    color: '#4ade80',
    fontSize: 16,
    fontWeight: '600',
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 12,
  },
  optionRow: {
    flexDirection: 'row',
    gap: 8,
  },
  option: {
    flex: 1,
    backgroundColor: '#374151',
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderRadius: 8,
    alignItems: 'center',
  },
  optionWide: {
    flex: 1,
  },
  optionSelected: {
    backgroundColor: '#4ade80',
  },
  optionText: {
    color: '#9ca3af',
    fontSize: 14,
    fontWeight: '500',
  },
  optionTextSelected: {
    color: '#000000',
  },
  hint: {
    color: '#6b7280',
    fontSize: 12,
    marginTop: 8,
  },
  estimateContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#374151',
    padding: 16,
    borderRadius: 8,
    marginTop: 8,
  },
  estimateLabel: {
    color: '#9ca3af',
    fontSize: 14,
  },
  estimateValue: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
  },
});

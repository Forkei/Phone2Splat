/**
 * Connect Screen
 * Server connection setup
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList, ConnectionState, DEFAULT_SETTINGS } from '../types';

type Props = NativeStackScreenProps<RootStackParamList, 'Connect'>;

interface ConnectScreenProps extends Props {
  connectionState: ConnectionState;
  lastError: string | null;
  onConnect: (host: string, port: number) => void;
}

const STORAGE_KEY = '@phonesplat_server';

export function ConnectScreen({
  navigation,
  connectionState,
  lastError,
  onConnect,
}: ConnectScreenProps) {
  const [host, setHost] = useState(DEFAULT_SETTINGS.serverHost);
  const [port, setPort] = useState(String(DEFAULT_SETTINGS.serverPort));

  // Load saved server settings
  useEffect(() => {
    const loadSettings = async () => {
      try {
        const saved = await AsyncStorage.getItem(STORAGE_KEY);
        if (saved) {
          const { host: savedHost, port: savedPort } = JSON.parse(saved);
          if (savedHost) setHost(savedHost);
          if (savedPort) setPort(String(savedPort));
        }
      } catch (error) {
        console.error('Error loading settings:', error);
      }
    };

    loadSettings();
  }, []);

  // Save settings and navigate when connected
  useEffect(() => {
    if (connectionState === 'connected') {
      const saveAndNavigate = async () => {
        try {
          await AsyncStorage.setItem(
            STORAGE_KEY,
            JSON.stringify({ host, port: parseInt(port, 10) })
          );
        } catch (error) {
          console.error('Error saving settings:', error);
        }
        navigation.replace('Scan');
      };

      saveAndNavigate();
    }
  }, [connectionState, host, port, navigation]);

  const handleConnect = () => {
    const portNum = parseInt(port, 10) || 8765;
    onConnect(host.trim(), portNum);
  };

  const isConnecting = connectionState === 'connecting' || connectionState === 'reconnecting';

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <View style={styles.content}>
        {/* Logo/Title */}
        <View style={styles.header}>
          <Text style={styles.logo}>PhoneSplat</Text>
          <Text style={styles.subtitle}>Real-time 3D Scanner</Text>
        </View>

        {/* Connection form */}
        <View style={styles.form}>
          <Text style={styles.label}>Server Address</Text>
          <TextInput
            style={styles.input}
            value={host}
            onChangeText={setHost}
            placeholder="192.168.1.100"
            placeholderTextColor="#6b7280"
            autoCapitalize="none"
            autoCorrect={false}
            keyboardType="default"
            editable={!isConnecting}
          />

          <Text style={styles.label}>Port</Text>
          <TextInput
            style={[styles.input, styles.portInput]}
            value={port}
            onChangeText={setPort}
            placeholder="8765"
            placeholderTextColor="#6b7280"
            keyboardType="number-pad"
            editable={!isConnecting}
          />

          {/* Error message */}
          {lastError && (
            <View style={styles.errorContainer}>
              <Text style={styles.errorText}>{lastError}</Text>
            </View>
          )}

          {/* Connect button */}
          <TouchableOpacity
            style={[styles.connectButton, isConnecting && styles.connectButtonDisabled]}
            onPress={handleConnect}
            disabled={isConnecting}
          >
            {isConnecting ? (
              <View style={styles.connectingRow}>
                <ActivityIndicator color="#000000" size="small" />
                <Text style={styles.connectButtonText}>Connecting...</Text>
              </View>
            ) : (
              <Text style={styles.connectButtonText}>Connect</Text>
            )}
          </TouchableOpacity>
        </View>

        {/* Instructions */}
        <View style={styles.instructions}>
          <Text style={styles.instructionsTitle}>Setup Instructions</Text>
          <Text style={styles.instructionsText}>
            1. Start the PhoneSplat server on your laptop
          </Text>
          <Text style={styles.instructionsText}>
            2. Make sure your phone is on the same WiFi network
          </Text>
          <Text style={styles.instructionsText}>
            3. Enter the server IP address shown in the terminal
          </Text>
        </View>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#1a1a2e',
  },
  content: {
    flex: 1,
    padding: 24,
    justifyContent: 'center',
  },
  header: {
    alignItems: 'center',
    marginBottom: 48,
  },
  logo: {
    fontSize: 36,
    fontWeight: 'bold',
    color: '#4ade80',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: '#9ca3af',
  },
  form: {
    marginBottom: 32,
  },
  label: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '500',
    marginBottom: 8,
  },
  input: {
    backgroundColor: '#374151',
    borderRadius: 12,
    padding: 16,
    fontSize: 16,
    color: '#ffffff',
    marginBottom: 16,
  },
  portInput: {
    width: 120,
  },
  errorContainer: {
    backgroundColor: 'rgba(239, 68, 68, 0.2)',
    borderRadius: 8,
    padding: 12,
    marginBottom: 16,
  },
  errorText: {
    color: '#ef4444',
    fontSize: 14,
  },
  connectButton: {
    backgroundColor: '#4ade80',
    borderRadius: 12,
    padding: 18,
    alignItems: 'center',
    marginTop: 8,
  },
  connectButtonDisabled: {
    opacity: 0.7,
  },
  connectingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  connectButtonText: {
    color: '#000000',
    fontSize: 18,
    fontWeight: '600',
  },
  instructions: {
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    borderRadius: 12,
    padding: 16,
  },
  instructionsTitle: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 12,
  },
  instructionsText: {
    color: '#9ca3af',
    fontSize: 14,
    lineHeight: 22,
  },
});

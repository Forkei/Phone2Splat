/**
 * PhoneSplat - Real-time Phone-to-Laptop 3D Scanner
 *
 * Main application entry point with navigation and WebSocket management
 */

import React, { useCallback } from 'react';
import { StatusBar } from 'expo-status-bar';
import { NavigationContainer, DefaultTheme } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { RootStackParamList, FramePacket } from './src/types';
import { useWebSocket } from './src/hooks/useWebSocket';
import { ConnectScreen } from './src/screens/ConnectScreen';
import { ScanScreen } from './src/screens/ScanScreen';

const Stack = createNativeStackNavigator<RootStackParamList>();

// Dark theme for navigation
const DarkTheme = {
  ...DefaultTheme,
  colors: {
    ...DefaultTheme.colors,
    background: '#1a1a2e',
    card: '#1a1a2e',
    text: '#ffffff',
    border: '#374151',
    primary: '#4ade80',
  },
};

export default function App() {
  // WebSocket connection (global state)
  const {
    connectionState,
    clientId,
    lastError,
    serverStats,
    connect,
    disconnect,
    sendFrame,
    sendControl,
    framesSent,
    framesAcked,
  } = useWebSocket({
    onMessage: (message) => {
      // Handle incoming messages if needed
      console.log('Server message:', message.type);
    },
    onStatsUpdate: (stats) => {
      // Stats updates handled via serverStats state
    },
  });

  // Handlers that we'll pass to screens
  const handleConnect = useCallback(
    (host: string, port: number) => {
      connect(host, port);
    },
    [connect]
  );

  const handleDisconnect = useCallback(() => {
    disconnect();
  }, [disconnect]);

  const handleSendFrame = useCallback(
    (packet: FramePacket) => {
      return sendFrame(packet);
    },
    [sendFrame]
  );

  const handleSendControl = useCallback(
    (command: string) => {
      sendControl(command as any);
    },
    [sendControl]
  );

  return (
    <SafeAreaProvider>
      <NavigationContainer theme={DarkTheme}>
        <StatusBar style="light" />
        <Stack.Navigator
          initialRouteName="Connect"
          screenOptions={{
            headerShown: false,
            animation: 'fade',
          }}
        >
          <Stack.Screen name="Connect">
            {(props) => (
              <ConnectScreen
                {...props}
                connectionState={connectionState}
                lastError={lastError}
                onConnect={handleConnect}
              />
            )}
          </Stack.Screen>

          <Stack.Screen name="Scan">
            {(props) => (
              <ScanScreen
                {...props}
                connectionState={connectionState}
                serverStats={serverStats}
                onSendFrame={handleSendFrame}
                onSendControl={handleSendControl}
                onDisconnect={handleDisconnect}
                framesSent={framesSent}
              />
            )}
          </Stack.Screen>
        </Stack.Navigator>
      </NavigationContainer>
    </SafeAreaProvider>
  );
}

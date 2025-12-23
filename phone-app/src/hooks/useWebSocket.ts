/**
 * WebSocket connection hook for PhoneSplat
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import {
  ConnectionState,
  FramePacket,
  ControlMessage,
  ServerMessage,
  SessionStats,
} from '../types';

interface UseWebSocketOptions {
  onMessage?: (message: ServerMessage) => void;
  onStatsUpdate?: (stats: SessionStats) => void;
  maxReconnectAttempts?: number;
  reconnectDelay?: number;
}

interface UseWebSocketReturn {
  connectionState: ConnectionState;
  clientId: string | null;
  lastError: string | null;
  serverStats: SessionStats | null;
  connect: (host: string, port: number) => void;
  disconnect: () => void;
  sendFrame: (packet: FramePacket) => boolean;
  sendControl: (command: ControlMessage['command']) => void;
  framesSent: number;
  framesAcked: number;
}

export function useWebSocket(options: UseWebSocketOptions = {}): UseWebSocketReturn {
  const {
    onMessage,
    onStatsUpdate,
    maxReconnectAttempts = 5,
    reconnectDelay = 1000,
  } = options;

  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected');
  const [clientId, setClientId] = useState<string | null>(null);
  const [lastError, setLastError] = useState<string | null>(null);
  const [serverStats, setServerStats] = useState<SessionStats | null>(null);
  const [framesSent, setFramesSent] = useState(0);
  const [framesAcked, setFramesAcked] = useState(0);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const hostRef = useRef<string>('');
  const portRef = useRef<number>(8765);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const handleMessage = useCallback(
    (event: MessageEvent) => {
      try {
        const message: ServerMessage = JSON.parse(event.data);

        // Handle different message types
        switch (message.type) {
          case 'status':
            if (message.client_id) {
              setClientId(message.client_id);
            }
            if (message.stats) {
              setServerStats(message.stats);
              onStatsUpdate?.(message.stats);
            }
            break;

          case 'ack':
            if (message.frame_count) {
              setFramesAcked(message.frame_count);
            }
            if (message.stats) {
              setServerStats(message.stats);
              onStatsUpdate?.(message.stats);
            }
            break;

          case 'error':
            setLastError(message.error || 'Unknown error');
            break;
        }

        onMessage?.(message);
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    },
    [onMessage, onStatsUpdate]
  );

  const attemptReconnect = useCallback(() => {
    if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
      setConnectionState('error');
      setLastError('Max reconnection attempts reached');
      return;
    }

    reconnectAttemptsRef.current += 1;
    setConnectionState('reconnecting');

    const delay = reconnectDelay * Math.pow(2, reconnectAttemptsRef.current - 1);
    console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current})`);

    reconnectTimeoutRef.current = setTimeout(() => {
      connect(hostRef.current, portRef.current);
    }, delay);
  }, [maxReconnectAttempts, reconnectDelay]);

  const connect = useCallback(
    (host: string, port: number) => {
      // Store for reconnection
      hostRef.current = host;
      portRef.current = port;

      // Clean up existing connection
      if (wsRef.current) {
        wsRef.current.close();
      }

      setConnectionState('connecting');
      setLastError(null);

      const url = `ws://${host}:${port}`;
      console.log(`Connecting to ${url}...`);

      try {
        const ws = new WebSocket(url);

        ws.onopen = () => {
          console.log('WebSocket connected');
          setConnectionState('connected');
          reconnectAttemptsRef.current = 0;
          setFramesSent(0);
          setFramesAcked(0);
        };

        ws.onmessage = handleMessage;

        ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          setLastError('Connection error');
        };

        ws.onclose = (event) => {
          console.log(`WebSocket closed: ${event.code} ${event.reason}`);

          if (connectionState === 'connected' && !event.wasClean) {
            attemptReconnect();
          } else {
            setConnectionState('disconnected');
          }
        };

        wsRef.current = ws;
      } catch (error) {
        console.error('Failed to create WebSocket:', error);
        setConnectionState('error');
        setLastError(String(error));
      }
    },
    [handleMessage, attemptReconnect, connectionState]
  );

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    reconnectAttemptsRef.current = maxReconnectAttempts; // Prevent reconnection

    if (wsRef.current) {
      wsRef.current.close(1000, 'User disconnected');
      wsRef.current = null;
    }

    setConnectionState('disconnected');
    setClientId(null);
    setServerStats(null);
  }, [maxReconnectAttempts]);

  const sendFrame = useCallback((packet: FramePacket): boolean => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) {
      return false;
    }

    try {
      wsRef.current.send(JSON.stringify(packet));
      setFramesSent((prev) => prev + 1);
      return true;
    } catch (error) {
      console.error('Error sending frame:', error);
      return false;
    }
  }, []);

  const sendControl = useCallback((command: ControlMessage['command']) => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) {
      console.warn('Cannot send control: not connected');
      return;
    }

    const message: ControlMessage = {
      type: 'control',
      command,
      client_time: Date.now() / 1000,
    };

    try {
      wsRef.current.send(JSON.stringify(message));
    } catch (error) {
      console.error('Error sending control message:', error);
    }
  }, []);

  return {
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
  };
}

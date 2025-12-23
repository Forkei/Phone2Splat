/**
 * Frame encoding utilities for PhoneSplat
 */

import * as ImageManipulator from 'expo-image-manipulator';
import { RESOLUTIONS } from '../types';

export interface EncodedFrame {
  base64: string;
  width: number;
  height: number;
  timestamp: number;
}

/**
 * Resize and encode a frame as JPEG
 */
export async function encodeFrame(
  uri: string,
  resolution: '480p' | '720p' | '1080p',
  quality: number
): Promise<EncodedFrame> {
  const timestamp = Date.now() / 1000;
  const targetSize = RESOLUTIONS[resolution];

  try {
    const result = await ImageManipulator.manipulateAsync(
      uri,
      [{ resize: { width: targetSize.width, height: targetSize.height } }],
      {
        compress: quality,
        format: ImageManipulator.SaveFormat.JPEG,
        base64: true,
      }
    );

    return {
      base64: result.base64 || '',
      width: result.width,
      height: result.height,
      timestamp,
    };
  } catch (error) {
    console.error('Error encoding frame:', error);
    throw error;
  }
}

/**
 * Calculate approximate size of base64 string in KB
 */
export function getBase64SizeKB(base64: string): number {
  // Base64 encoding increases size by ~33%
  const bytes = (base64.length * 3) / 4;
  return bytes / 1024;
}

/**
 * Estimate bandwidth from frame size and FPS
 */
export function estimateBandwidthMbps(frameSizeKB: number, fps: number): number {
  return (frameSizeKB * fps * 8) / 1000;
}

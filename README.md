# Phone2Splat

Real-time phone-to-laptop 3D scanner using Gaussian Splatting.

Turn your phone into a wireless 3D scanner that streams video frames to your laptop for reconstruction using MonoGS (Monocular Gaussian SLAM).

## Features

- **Wireless Capture**: Stream camera frames from phone to laptop over WiFi
- **Real-time Stats**: Monitor FPS, latency, and capture progress
- **IMU Integration**: Capture accelerometer/gyroscope data synchronized with frames
- **TUM RGB-D Format**: Saves data compatible with MonoGS and other SLAM pipelines
- **Landscape Mode**: Optimized for SLAM with forced landscape orientation
- **MonoGS Integration**: Seamless integration with MonoGS for 3D reconstruction

## System Requirements

### Laptop
- Windows 11 (tested) / Linux / macOS
- Python 3.10+
- NVIDIA GPU with CUDA (for MonoGS reconstruction)
- Same WiFi network as phone

### Phone
- Android (tested) or iOS
- Camera and motion sensor access

## Quick Start

### 1. Install Server Dependencies

```bash
cd server
pip install -r requirements.txt
```

### 2. Start the Server

```bash
python main.py
```

The server will display your local IP address. Note this for the phone app.

### 3. Install Phone App

The app requires a development build (not Expo Go) due to native camera modules.

```bash
cd phone-app
npm install

# Build for Android (requires Expo account)
npx eas build --profile development --platform android
```

Download and install the APK from the build URL or QR code.

### 4. Connect and Scan

1. Open the Phone2Splat app (hold phone in **landscape mode**)
2. Enter your laptop's IP address and port 8765
3. Press "Connect"
4. Press the record button to start scanning
5. **Move slowly** around your subject
6. Press stop when done (60+ seconds recommended)

### 5. Run 3D Reconstruction

```bash
# Clone MonoGS (first time only)
git clone --recursive https://github.com/muskie82/MonoGS.git
cd MonoGS
pip install -r requirements.txt
pip install -e submodules/diff-gaussian-rasterization
pip install -e submodules/simple-knn

# Run reconstruction on latest capture
python slam.py --config ../server/captures/<session_folder>/monogs_config.yaml
```

## Project Structure

```
Phone2Splat/
├── phone-app/                # React Native Expo app
│   ├── App.tsx
│   ├── src/
│   │   ├── screens/          # Connect & Scan screens
│   │   ├── components/       # UI components (VisionCameraView)
│   │   ├── hooks/            # useWebSocket, useVisionCamera, useIMU
│   │   └── types/            # TypeScript definitions
│   └── package.json
│
├── server/                   # Python backend
│   ├── main.py               # Server entry point
│   ├── websocket_server.py   # WebSocket handling
│   ├── frame_processor.py    # Frame saving in TUM format
│   ├── validate_capture.py   # Capture validation
│   ├── monogs_bridge.py      # MonoGS integration
│   ├── config.py             # Configuration
│   └── captures/             # Captured sessions
│       └── session_YYYYMMDD_HHMMSS/
│           ├── rgb/              # JPEG frames
│           ├── rgb.txt           # TUM format timestamps
│           ├── depth.txt         # Depth timestamps (dummy for monocular)
│           ├── groundtruth.txt   # Pose data
│           ├── imu.csv           # IMU data
│           ├── intrinsics.json   # Camera parameters
│           └── monogs_config.yaml # MonoGS config
│
└── README.md
```

## Capture Tips

For best reconstruction results:

1. **Hold phone in LANDSCAPE mode** - SLAM works much better
2. **Move VERY slowly** - Like you're moving through honey
3. **Overlap 80%+** - Small movements between frames
4. **Walk around subject** - Don't just rotate in place
5. **Good lighting** - Avoid dark areas and harsh shadows
6. **60+ seconds** - Longer captures give better results
7. **Textured surfaces** - Featureless surfaces are hard to track

## Configuration

Edit `server/config.py` to customize:

```python
WEBSOCKET_PORT = 8765
CAPTURES_DIR = Path(__file__).parent / "captures"
```

Phone app settings (in-app):
- **Resolution**: 480p recommended for SLAM
- **FPS**: 10 FPS is good balance
- **JPEG Quality**: 85% recommended

## Troubleshooting

### Phone can't connect
- Ensure phone and laptop are on the same WiFi network
- Check firewall isn't blocking port 8765
- Try using the laptop's IP address (not localhost)

### Low FPS during capture
- Reduce resolution in app settings
- Lower JPEG quality
- Close other apps on phone

### MonoGS errors
- Ensure CUDA is properly installed
- Check PyTorch CUDA version matches system CUDA
- Verify session has enough frames (>50)
- For NumPy 2.0: patch `np.unicode_` to `np.str_` in dataset.py

### Poor reconstruction quality
- Move slower during capture
- Ensure good lighting
- Check camera intrinsics in intrinsics.json
- Capture in landscape mode

## License

MIT

## Credits

- [MonoGS](https://github.com/muskie82/MonoGS) - Monocular Gaussian SLAM (CVPR 2024)
- [react-native-vision-camera](https://github.com/mrousavy/react-native-vision-camera) - Fast camera capture
- [Expo](https://expo.dev/) - React Native framework
- [3D Gaussian Splatting](https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting/) - Original GS paper

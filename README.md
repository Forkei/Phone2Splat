# PhoneSplat

Real-time phone-to-laptop 3D scanner using Gaussian Splatting.

Turn your phone into a wireless 3D scanner that streams video frames to your laptop for reconstruction using MonoGS (Monocular Gaussian SLAM).

## Features

- **Wireless Capture**: Stream camera frames from phone to laptop over WiFi
- **Real-time Stats**: Monitor FPS, latency, and capture progress
- **IMU Integration**: Capture accelerometer/gyroscope data synchronized with frames
- **TUM RGB-D Format**: Saves data compatible with MonoGS and other SLAM pipelines
- **Validation Tools**: Verify capture quality before reconstruction
- **MonoGS Bridge**: Seamless integration with MonoGS for 3D reconstruction

## System Requirements

### Laptop
- Windows 11 (tested) / Linux / macOS
- Python 3.10+
- NVIDIA GPU with CUDA (for MonoGS reconstruction)
- Same WiFi network as phone

### Phone
- iOS or Android
- Expo Go app installed (for development)
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

### 3. Test Without Phone (Optional)

```bash
# In another terminal
python test_full_pipeline.py
```

This runs an automated test using a simulated client.

### 4. Set Up Phone App

```bash
cd phone-app
npm install
npx expo start
```

Scan the QR code with Expo Go on your phone.

### 5. Connect and Scan

1. Enter your laptop's IP address in the phone app
2. Press "Connect"
3. Press the green record button to start scanning
4. Move around your subject slowly
5. Press stop when done

### 6. Validate and Reconstruct

```bash
# Validate capture quality
python server/validate_capture.py --latest

# Prepare for MonoGS
python server/monogs_bridge.py prepare --latest

# Run reconstruction (requires MonoGS)
python server/monogs_bridge.py run --latest
```

## Project Structure

```
phonesplat/
├── phone-app/                # React Native Expo app
│   ├── App.tsx
│   ├── src/
│   │   ├── screens/          # Connect & Scan screens
│   │   ├── components/       # UI components
│   │   ├── hooks/            # useWebSocket, useCamera, useIMU
│   │   └── types/            # TypeScript definitions
│   └── package.json
│
├── server/                   # Python backend
│   ├── main.py               # Server entry point
│   ├── websocket_server.py   # WebSocket handling
│   ├── frame_processor.py    # Frame saving
│   ├── validate_capture.py   # Capture validation
│   ├── monogs_bridge.py      # MonoGS integration
│   ├── config.py             # Configuration
│   ├── test_client.py        # Test client
│   └── requirements.txt
│
├── captures/                 # Captured sessions (created at runtime)
│   └── session_YYYYMMDD_HHMMSS/
│       ├── rgb/              # JPEG frames
│       ├── rgb.txt           # TUM format timestamps
│       ├── imu.csv           # IMU data
│       ├── intrinsics.json   # Camera parameters
│       └── monogs_config.yaml # Generated config
│
├── test_full_pipeline.py     # End-to-end test
└── README.md
```

## Configuration

Edit `server/config.py` to customize:

```python
# Server port
WEBSOCKET_PORT = 8765

# MonoGS installation path
MONOGS_PATH = Path("C:/path/to/MonoGS")

# Capture defaults
DEFAULT_FPS = 10
DEFAULT_RESOLUTION = "720p"
DEFAULT_JPEG_QUALITY = 0.8
```

## Capture Data Format

### TUM RGB-D Format

Frames are saved in TUM RGB-D format for compatibility with SLAM pipelines:

- `rgb/` - JPEG images named by timestamp
- `rgb.txt` - Timestamp-to-filename mapping
- `imu.csv` - IMU data with columns: timestamp, accel_x/y/z, gyro_x/y/z, qw/qx/qy/qz

### Frame Packet Format

The phone sends JSON packets over WebSocket:

```json
{
  "type": "frame",
  "timestamp": 1234567890.123,
  "frame": "<base64 JPEG>",
  "imu": {
    "accel": [0.1, 0.2, -9.8],
    "gyro": [0.01, 0.02, 0.03],
    "orientation": [1.0, 0.0, 0.0, 0.0]
  },
  "camera_intrinsics": {
    "fx": 1000, "fy": 1000,
    "cx": 360, "cy": 640,
    "width": 720, "height": 1280
  }
}
```

## MonoGS Integration

### Installing MonoGS

```bash
git clone --recursive https://github.com/muskie82/MonoGS.git
cd MonoGS
conda env create -f environment.yml
conda activate MonoGS
```

Set the environment variable or edit `config.py`:
```bash
export MONOGS_PATH=/path/to/MonoGS
```

### Running Reconstruction

```bash
# Check status
python server/monogs_bridge.py status

# Prepare session
python server/monogs_bridge.py prepare session_20241222_153045

# Run MonoGS
python server/monogs_bridge.py run session_20241222_153045

# Export model
python server/monogs_bridge.py export session_20241222_153045 -o model.ply
```

## Capture Tips

For best reconstruction results:

1. **Move slowly** - Fast motion causes blur and tracking loss
2. **Overlap frames** - Ensure 60-70% overlap between views
3. **Cover all angles** - Walk around the subject
4. **Good lighting** - Avoid dark areas and harsh shadows
5. **Textured surfaces** - Featureless surfaces are hard to track
6. **10 FPS is usually enough** - Higher FPS helps with fast motion

## Troubleshooting

### Phone can't connect
- Ensure phone and laptop are on the same WiFi network
- Check firewall isn't blocking port 8765
- Try using the laptop's IP address (not localhost)

### Low FPS during capture
- Reduce resolution in app settings
- Lower JPEG quality
- Close other apps on phone

### Validation failures
- Check for frame gaps (network issues)
- Ensure IMU data is being captured
- Verify intrinsics.json was created

### MonoGS errors
- Ensure CUDA is properly installed
- Check MonoGS conda environment is activated
- Verify session has enough frames (>30)

## License

MIT

## Credits

- [MonoGS](https://github.com/muskie82/MonoGS) - Monocular Gaussian SLAM
- [Expo](https://expo.dev/) - React Native framework
- [3D Gaussian Splatting](https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting/) - Original GS paper

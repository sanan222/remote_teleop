# Python WebRTC Client for Robot Teleoperation

This is a Python implementation of the JavaScript WebRTC client using the `aiortc` library.

## Features

- **Robot Mode**: Streams video from your camera and receives control commands
- **Operator Mode**: Receives video stream and sends control commands
- Full WebRTC support with ICE candidate exchange
- WebSocket signaling with the existing server
- Data channel for sending/receiving control commands

## Installation

1. Install Python 3.8 or higher

2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Run the client:

```bash
python client.py
```

Then select your role:

- Press `1` for Robot mode (streamer)
- Press `2` for Operator mode (controller)

## How It Works

### Robot Mode

1. Accesses your camera using OpenCV
2. Creates a WebRTC peer connection
3. Adds video track to the connection
4. Connects to the signaling server
5. Waits for operator to connect
6. Streams video and receives control commands via data channel

### Operator Mode

1. Creates a WebRTC peer connection
2. Sets up to receive video
3. Creates a data channel for sending commands
4. Connects to the signaling server
5. Initiates the call by sending an offer
6. Receives video stream and displays it
7. Sends test control commands periodically

## Configuration

Edit the following in `client.py`:

- `SIGNALING_SERVER_URL`: WebSocket URL of your signaling server
- `ICE_SERVERS`: STUN/TURN servers for NAT traversal

## Code Structure

The code mirrors the JavaScript implementation:

1. **Configuration**: STUN servers and signaling URL
2. **CameraVideoTrack**: Custom video track class for camera access
3. **Startup Functions**: `start_as_robot()` and `start_as_operator()`
4. **WebRTC Setup**: Peer connection, data channel, and event handlers
5. **Signaling**: WebSocket connection and message handling
6. **Utilities**: Logging and helper functions

## Key Mappings from JavaScript to Python

| JavaScript              | Python (aiortc)                      |
| ----------------------- | ------------------------------------ |
| `RTCPeerConnection`     | `aiortc.RTCPeerConnection`           |
| `RTCSessionDescription` | `aiortc.RTCSessionDescription`       |
| `RTCIceCandidate`       | `aiortc.RTCIceCandidate`             |
| `getUserMedia()`        | `CameraVideoTrack` class with OpenCV |
| `WebSocket`             | `websockets` library                 |
| `pc.onicecandidate`     | `@pc.on("icecandidate")` decorator   |
| `pc.ondatachannel`      | `@pc.on("datachannel")` decorator    |
| `pc.ontrack`            | `@pc.on("track")` decorator          |

## Stopping the Client

Press `Ctrl+C` to gracefully shut down the client.

## Notes

- The operator mode displays the received video in an OpenCV window
- Press 'q' while the video window is focused to close the video display
- The data channel currently sends random test commands every second
- Customize the command sending logic in `send_test_actions()` function

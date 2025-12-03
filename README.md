# WebRTC-Based Remote Teleoperation System

This repository contains a WebRTC-based remote teleoperation system with both JavaScript and Python client implementations.

---

## Trial 1: JavaScript-Based WebRTC Client

### Step 1: Start the Signaling Server

Activate the Node.js WebSocket and Nginx server on your Google Cloud VM:

```bash
cd /home/sananqarayev123/remote_teleop/webrtc-signaling
node server.js
```

### Step 2: Open the Follower (Robot) Interface

Navigate to https://readytoserve.online/follower/ on any modern browser (Edge, Chrome) from your robot location.

### Step 3: Open the Leader (Operator) Interface

Navigate to https://readytoserve.online/leader/ on any modern browser (Edge, Chrome) from your operator location.

### Step 4: Establish Connection

1. Click the **"I am Robot"** button in the follower browser
2. Wait 5 seconds
3. Click the **"I am Operator"** button in the leader browser
4. Allow camera access when prompted in the follower browser
5. Start streaming

### Expected Result

- **Leader browser**: Live video stream from the robot
- **Follower browser**: Live control actions from the operator

---

## Trial 2: Python-Based WebRTC Client

### Step 1: Clone the Repository

```bash
git clone https://github.com/sanan222/remote_teleop.git
cd remote_teleop
```

### Step 2: Setup Python Environment

Create a new Conda environment and install dependencies:

```bash
conda create -n stream python=3.14
conda activate stream
cd python_app/
pip install -r requirements.txt
```

### Step 3: Run the Robot Client

On the robot machine (with camera connected):

```bash
python client.py
```

**Select Mode:** Choose `1` for Robot (Streamer)

**Select Camera:** Choose one of the following:

- `1` - RGB Camera (SO101 wrist camera)
- `2` - RealSense RGB (Intel RealSense color view)
- `3` - RealSense Depth (Intel RealSense depth visualization)

### Step 4: Run the Operator Client

On the operator machine:

```bash
python client.py
```

**Select Mode:** Choose `2` for Operator (Controller)

### Expected Result

- **Operator terminal**: Live video stream from the robot camera
- **Robot terminal**: Real-time control commands from the operator

---

## Command-Line Usage (Alternative)

You can also run the Python client with command-line arguments:

```bash
# Robot mode with RGB camera
python client.py --role robot --camera rgb

# Robot mode with RealSense color
python client.py --role robot --camera realsense_rgb

# Robot mode with RealSense depth
python client.py --role robot --camera realsense_depth

# Operator mode
python client.py --role operator
```

---

## Requirements

- Python 3.10+
- Intel RealSense camera (for RealSense modes)
- RGB camera compatible with OpenCV
- Active internet connection
- Access to the signaling server at `wss://readytoserve.online/ws`

---

## Architecture

- **Signaling Server**: Node.js WebSocket server hosted on Google Cloud VM
- **WebRTC**: Peer-to-peer video streaming with STUN/TURN support
- **Camera Support**: RGB cameras and Intel RealSense (color + depth)
- **Streaming**: Single camera stream selection to optimize bandwidth and latency

---

## License

[Add your license information here]

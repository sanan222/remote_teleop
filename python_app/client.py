"""WebRTC Client for Robot Teleoperation

Dual-mode client supporting:
- Robot Mode: Streams video and receives control commands
- Operator Mode: Receives video and sends control commands
"""

import argparse
import asyncio
import json
import logging
from datetime import datetime

import cv2
import numpy as np
import websockets
from aiortc import (
    RTCPeerConnection,
    RTCSessionDescription,
    RTCIceCandidate,
    RTCConfiguration,
    RTCIceServer,
    VideoStreamTrack
)
from av import VideoFrame
from camera import CameraVideoTrack

# Configuration
SIGNALING_SERVER_URL = "wss://readytoserve.online/ws"
ICE_SERVERS = [
    {"urls": "stun:stun.l.google.com:19302"},
    {"urls": "stun:stun.l.google.com:5349"},
    {"urls": "stun:stun1.l.google.com:3478"},
    {"urls": "stun:stun1.l.google.com:5349"},
    {"urls": "stun:stun2.l.google.com:19302"},
    {"urls": "stun:stun2.l.google.com:5349"},
    {"urls": "stun:stun3.l.google.com:3478"},
    {"urls": "stun:stun3.l.google.com:5349"},
    {"urls": "stun:stun4.l.google.com:19302"},
    {"urls": "stun:stun4.l.google.com:5349"}
]

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class WebRTCClient:
    """WebRTC client for robot teleoperation"""
    
    def __init__(self, role, camera_type="rgb"):
        self.role = role  # 'robot' or 'operator'
        self.camera_type = camera_type  # Camera type to stream
        self.pc = None
        self.ws = None
        self.data_channel = None
        self.camera_tracks = []  # Support multiple camera tracks
        self.video_windows = {}  # Track window names for operator mode
        
    def _log(self, message):
        """Internal logging method"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{timestamp} - {message}")
        logger.info(message)
    
    def _setup_peer_connection(self):
        """Initialize RTCPeerConnection with ICE servers and event handlers"""
        ice_servers = [RTCIceServer(urls=server["urls"]) for server in ICE_SERVERS]
        config = RTCConfiguration(iceServers=ice_servers)
        self.pc = RTCPeerConnection(configuration=config)
        
        @self.pc.on("icecandidate")
        async def on_icecandidate(candidate):
            if candidate:
                await self._send_signal({
                    "type": "candidate",
                    "candidate": {
                        "candidate": candidate.candidate,
                        "sdpMid": candidate.sdpMid,
                        "sdpMLineIndex": candidate.sdpMLineIndex
                    }
                })
        
        @self.pc.on("connectionstatechange")
        async def on_connectionstatechange():
            self._log(f"Connection state: {self.pc.connectionState}")
        
        if self.role == 'robot':
            self._setup_robot_handlers()
        else:
            self._setup_operator_handlers()
    
    def _setup_robot_handlers(self):
        """Setup event handlers for robot mode"""
        @self.pc.on("datachannel")
        def on_datachannel(channel):
            self._log("Data channel opened (Robot)")
            
            @channel.on("message")
            def on_message(message):
                try:
                    action = json.loads(message)
                    self._handle_robot_action(action)
                except json.JSONDecodeError:
                    self._log(f"Received non-JSON message: {message}")
    
    def _handle_robot_action(self, action):
        """Process received robot control actions"""
        self._log(f"Action received: {json.dumps(action)}")
        # Implement robot control logic here
    
    def _setup_operator_handlers(self):
        """Setup event handlers for operator mode"""
        self.track_counter = 0
        
        @self.pc.on("track")
        def on_track(track):
            self._log(f"Video stream received: {track.kind}")
            if track.kind == "video":
                self.track_counter += 1
                asyncio.create_task(self._receive_video_frames(track, self.track_counter))
    
    async def _receive_video_frames(self, track, track_id):
        """Receive and display video frames in operator mode
        
        Args:
            track: Video track to receive frames from
            track_id: Unique identifier for this track (used for window naming)
        """
        window_name = f"Camera {track_id}"
        self.video_windows[track_id] = window_name
        
        frame_count = 0
        display_enabled = True
        display_error_shown = False
        
        try:
            while True:
                frame = await track.recv()
                frame_count += 1
                img = frame.to_ndarray(format="bgr24")
                
                if display_enabled:
                    try:
                        cv2.imshow(window_name, img)
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            self._log(f"{window_name} display closed by user")
                            break
                    except cv2.error:
                        if not display_error_shown:
                            self._log(f"Video display not available on this system for {window_name}")
                            display_error_shown = True
                        display_enabled = False
                
                if frame_count % 30 == 0:
                    self._log(f"{window_name}: Received {frame_count} frames")
        
        except Exception as e:
            self._log(f"Error receiving video on {window_name}: {str(e)}")
        finally:
            if display_enabled:
                try:
                    cv2.destroyWindow(window_name)
                except:
                    pass
    
    def _setup_data_channel(self):
        """Setup data channel for operator mode"""
        self.data_channel = self.pc.createDataChannel("robot-control")
        
        @self.data_channel.on("open")
        def on_open():
            self._log("Data channel opened (Operator)")
        
        @self.data_channel.on("close")
        def on_close():
            self._log("Data channel closed")
    
    def send_action(self, action):
        """Send control action to robot"""

        if self.data_channel and self.data_channel.readyState == "open":
            # TODO: Implement action sending logic
            try:
                self.data_channel.send(json.dumps(action))
            except Exception as e:
                self._log(f"Error sending action: {str(e)}")
        else:
            self._log("Data channel not ready")
    
    async def _connect_to_signaling(self):
        """Connect to WebSocket signaling server"""
        self._log("Connecting to signaling server...")
        
        try:
            async with websockets.connect(SIGNALING_SERVER_URL) as websocket:
                self.ws = websocket
                self._log("Connected to signaling server")
                
                if self.role == 'operator':
                    await self._create_and_send_offer()
                
                async for message in websocket:
                    await self._handle_signaling_message(message)
        
        except Exception as e:
            self._log(f"WebSocket error: {str(e)}")
            raise
    
    async def _handle_signaling_message(self, message):
        """Handle incoming signaling messages"""
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            
            if msg_type == "offer" and self.role == 'robot':
                await self._handle_offer(data["offer"])
            elif msg_type == "answer" and self.role == 'operator':
                await self._handle_answer(data["answer"])
            elif msg_type == "candidate":
                await self._handle_candidate(data["candidate"])
        
        except Exception as e:
            self._log(f"Error handling signaling message: {str(e)}")
    
    async def _handle_offer(self, offer):
        """Handle received offer (robot mode)"""
        self._log("Received offer")
        await self.pc.setRemoteDescription(
            RTCSessionDescription(sdp=offer["sdp"], type=offer["type"])
        )
        answer = await self.pc.createAnswer()
        await self.pc.setLocalDescription(answer)
        await self._send_signal({
            "type": "answer",
            "answer": {
                "sdp": self.pc.localDescription.sdp,
                "type": self.pc.localDescription.type
            }
        })
        self._log("Sent answer")
    
    async def _handle_answer(self, answer):
        """Handle received answer (operator mode)"""
        self._log("Received answer")
        await self.pc.setRemoteDescription(
            RTCSessionDescription(sdp=answer["sdp"], type=answer["type"])
        )
    
    async def _handle_candidate(self, candidate):
        """Handle ICE candidate"""
        await self.pc.addIceCandidate(
            RTCIceCandidate(
                candidate=candidate["candidate"],
                sdpMid=candidate["sdpMid"],
                sdpMLineIndex=candidate["sdpMLineIndex"]
            )
        )
    
    async def _create_and_send_offer(self):
        """Create and send offer (operator mode)"""
        offer = await self.pc.createOffer()
        await self.pc.setLocalDescription(offer)
        await self._send_signal({
            "type": "offer",
            "offer": {
                "sdp": self.pc.localDescription.sdp,
                "type": self.pc.localDescription.type
            }
        })
        self._log("Sent offer")
    
    async def _send_signal(self, data):
        """Send signaling data via WebSocket"""
        if self.ws:
            try:
                await self.ws.send(json.dumps(data))
            except Exception as e:
                self._log(f"Error sending signal: {str(e)}")
    
    async def start_as_robot(self):
        """Start client in robot mode"""
        self._log(f"Starting as ROBOT (Streamer) - Camera: {self.camera_type}")
        
        self._setup_peer_connection()
        
        # Create camera track based on selected type
        try:
            if self.camera_type == "rgb":
                track = CameraVideoTrack(
                    camera_type="rgb",
                    camera_index=0,
                    width=640,
                    height=480,
                    fps=30
                )
                self._log("RGB camera track added (index 0)")
                
            elif self.camera_type == "realsense_rgb":
                track = CameraVideoTrack(
                    camera_type="realsense",
                    stream_type="color",
                    width=640,
                    height=480,
                    fps=30
                )
                self._log("RealSense color track added")
                
            elif self.camera_type == "realsense_depth":
                track = CameraVideoTrack(
                    camera_type="realsense",
                    stream_type="depth",
                    width=640,
                    height=480,
                    fps=30
                )
                self._log("RealSense depth track added")
            else:
                raise ValueError(f"Invalid camera type: {self.camera_type}")
            
            self.camera_tracks.append(track)
            self.pc.addTrack(track)
            
        except Exception as e:
            self._log(f"Error: Failed to initialize camera: {e}")
            raise
        
        if not self.camera_tracks:
            raise RuntimeError("No cameras could be initialized")
        
        self._log(f"Total {len(self.camera_tracks)} camera track(s) ready")
        await self._connect_to_signaling()
    
    async def start_as_operator(self):
        """Start client in operator mode"""
        self._log("Starting as OPERATOR (Controller)")
        
        self._setup_peer_connection()
        
        # Add transceiver to receive single video track
        self.pc.addTransceiver('video', direction='recvonly')
        self._log("Set up to receive 1 video track")
        
        self._setup_data_channel()
        
        await self._connect_to_signaling()
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.pc:
            await self.pc.close()
        
        # Stop all camera tracks
        for track in self.camera_tracks:
            try:
                track.stop()
            except Exception as e:
                self._log(f"Error stopping camera track: {e}")
        
        # Close all video windows
        try:
            cv2.destroyAllWindows()
        except:
            pass


async def main():
    """Main entry point"""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='WebRTC Robot Teleoperation Client')
    parser.add_argument(
        '--role',
        type=str,
        choices=['robot', 'operator'],
        help='Client role: robot (streamer) or operator (controller)'
    )
    parser.add_argument(
        '--camera',
        type=str,
        choices=['rgb', 'realsense_rgb', 'realsense_depth'],
        default='rgb',
        help='Camera type to stream (only for robot mode): rgb, realsense_rgb, or realsense_depth'
    )
    
    args = parser.parse_args()
    
    # Interactive mode if role not specified
    if args.role is None:
        print("=" * 60)
        print("WebRTC Robot Teleoperation Client")
        print("=" * 60)
        print("\nSelect Role:")
        print("1. Robot (Streamer)")
        print("2. Operator (Controller)")
        print("=" * 60)
        
        choice = input("\nEnter choice (1 or 2): ").strip()
        
        if choice not in ['1', '2']:
            print("Invalid choice. Exiting.")
            return
        
        role = 'robot' if choice == '1' else 'operator'
        
        # Ask for camera type if robot mode
        if role == 'robot':
            print("\nSelect Camera:")
            print("1. RGB Camera")
            print("2. RealSense RGB")
            print("3. RealSense Depth")
            print("=" * 60)
            
            cam_choice = input("\nEnter choice (1, 2, or 3): ").strip()
            
            if cam_choice == '1':
                camera_type = 'rgb'
            elif cam_choice == '2':
                camera_type = 'realsense_rgb'
            elif cam_choice == '3':
                camera_type = 'realsense_depth'
            else:
                print("Invalid choice. Using RGB camera.")
                camera_type = 'rgb'
        else:
            camera_type = 'rgb'  # Not used in operator mode
    else:
        role = args.role
        camera_type = args.camera
    
    client = WebRTCClient(role, camera_type=camera_type)
    
    try:
        if role == 'robot':
            await client.start_as_robot()
        else:
            await client.start_as_operator()
        
        print("\nClient running. Press Ctrl+C to stop.\n")
        await asyncio.Event().wait()
    
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {str(e)}")
        logger.exception("Fatal error")
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import time
import fractions

import cv2
import numpy as np
import pyrealsense2 as rs
from aiortc import VideoStreamTrack
from av import VideoFrame


class MediaStreamError(Exception):
    """Exception raised when media stream is not in live state"""
    pass


class CameraVideoTrack(VideoStreamTrack):
    """Video track capturing frames from RGB or RealSense camera
    
    Supports:
    - Multiple RGB cameras (identified by camera_index)
    - Intel RealSense cameras with separate color and depth streams
    """
    
    def __init__(
        self,
        camera_type="rgb",
        camera_index=0,
        stream_type="color",
        width=640,
        height=480,
        fps=30
    ):
        """Initialize camera video track
        
        Args:
            camera_type: Type of camera - "rgb" or "realsense"
            camera_index: Camera index for RGB cameras (0, 1, 2, etc.)
            stream_type: For RealSense cameras - "color" or "depth"
            width: Frame width
            height: Frame height
            fps: Frames per second
        """
        super().__init__()
        
        self.camera_type = camera_type.lower()
        self.camera_index = camera_index
        self.stream_type = stream_type.lower()
        self.width = width
        self.height = height
        self.fps = fps
        
        # Video timing configuration
        self.VIDEO_CLOCK_RATE = 90000
        self.VIDEO_PTIME = 1 / fps
        self.VIDEO_TIME_BASE = fractions.Fraction(1, self.VIDEO_CLOCK_RATE)
        
        # Initialize camera based on type
        self.cap = None
        self.pipe = None
        
        if self.camera_type == "rgb":
            self._init_rgb_camera()
        elif self.camera_type == "realsense":
            self._init_realsense_camera()
        else:
            raise ValueError(f"Invalid camera type: {camera_type}. Must be 'rgb' or 'realsense'")
    
    def _init_rgb_camera(self):
        """Initialize RGB camera (webcam, wrist camera, etc.)"""
        self.cap = cv2.VideoCapture(self.camera_index)
        
        if not self.cap.isOpened():
            raise RuntimeError(f"RGB camera {self.camera_index} not found or cannot be opened")
        
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
    
    def _init_realsense_camera(self):
        """Initialize Intel RealSense camera with depth stream"""
        self.pipe = rs.pipeline()
        cfg = rs.config()
        
        cfg.enable_stream(rs.stream.depth, self.width, self.height, rs.format.z16, self.fps)
        cfg.enable_stream(rs.stream.color, self.width, self.height, rs.format.bgr8, self.fps)
        
        try:
            self.pipe.start(cfg)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to start RealSense camera: {e}")
    
    async def next_timestamp(self) -> tuple[int, fractions.Fraction]:
        """Generate next timestamp for video frame
        
        Returns:
            Tuple of (timestamp, time_base)
        
        Raises:
            MediaStreamError: If stream is not in live state
        """
        if self.readyState != "live":
            raise MediaStreamError("Live stream is stopped or not started")
        
        if hasattr(self, "_timestamp"):
            self._timestamp += int(self.VIDEO_PTIME * self.VIDEO_CLOCK_RATE)
            wait = self._start + (self._timestamp / self.VIDEO_CLOCK_RATE) - time.time()
            
            if wait > 0:
                await asyncio.sleep(wait)
        else:
            self._start = time.time()
            self._timestamp = 0
        
        return self._timestamp, self.VIDEO_TIME_BASE
    
    async def recv(self):
        """Receive next video frame
        
        This is the main method called by aiortc. It dispatches to the appropriate
        frame capture method based on camera type.
        
        Returns:
            VideoFrame object
        """
        if self.camera_type == "rgb":
            return await self._recv_rgb()
        elif self.camera_type == "realsense":
            return await self._recv_realsense()
    
    async def _recv_rgb(self):
        """Capture frame from RGB camera
        
        Returns:
            VideoFrame with RGB data
        """
        pts, time_base = await self.next_timestamp()
        
        ret, frame = self.cap.read()
        if not ret:
            raise RuntimeError(f"Failed to read frame from RGB camera {self.camera_index}")
        
        # Convert BGR (OpenCV format) to RGB
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        video_frame = VideoFrame.from_ndarray(frame, format="rgb24")
        video_frame.pts = pts
        video_frame.time_base = time_base
        
        return video_frame
    
    async def _recv_realsense(self):
        """Capture frame from RealSense camera
        
        Returns:
            VideoFrame with either color or depth stream based on stream_type
        """
        pts, time_base = await self.next_timestamp()
        
        frames = self.pipe.wait_for_frames()
        color_frame = frames.get_color_frame()
        depth_frame = frames.get_depth_frame()
        
        if not color_frame or not depth_frame:
            raise RuntimeError("Failed to read frames from RealSense camera")
        
        if self.stream_type == "color":
            # Return RGB color stream
            color_image = np.asanyarray(color_frame.get_data())
            color_image = cv2.cvtColor(color_image, cv2.COLOR_BGR2RGB)
            
            video_frame = VideoFrame.from_ndarray(color_image, format="rgb24")
            video_frame.pts = pts
            video_frame.time_base = time_base
            return video_frame
            
        elif self.stream_type == "depth":
            # Return depth stream as colormap
            depth_image = np.asanyarray(depth_frame.get_data())
            
            # Apply colormap to depth image for visualization
            depth_colormap = cv2.applyColorMap(
                cv2.convertScaleAbs(depth_image, alpha=0.03),
                cv2.COLORMAP_JET
            )
            depth_colormap = cv2.cvtColor(depth_colormap, cv2.COLOR_BGR2RGB)
            
            video_frame = VideoFrame.from_ndarray(depth_colormap, format="rgb24")
            video_frame.pts = pts
            video_frame.time_base = time_base
            return video_frame
        
        else:
            raise ValueError(f"Invalid stream_type for RealSense: {self.stream_type}. Must be 'color' or 'depth'")
    
    def stop(self):
        """Stop the camera and release resources"""
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        
        if self.pipe is not None:
            self.pipe.stop()
            self.pipe = None
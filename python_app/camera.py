import cv2 as cv
from aiortc.contrib.media import VideoStreamTrack
from aiortc import VideoFrame


class CameraVideoTrack(VideoStreamTrack):
    """Video track capturing frames from camera"""
    
    def __init__(self, width=640, height=480):
        super().__init__()

        # TODO: Implement camera initialization: 0 -> webcam, 1 -> wrist camera, realsense
        self.cap = cv.VideoCapture(1)
        if not self.cap.isOpened():
            raise RuntimeError("Failed to open camera")
        
        self.cap.set(cv.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv.CAP_PROP_FRAME_HEIGHT, height)
        
    async def recv(self):
        pts, time_base = await self.next_timestamp()
        
        ret, frame = self.cap.read()
        if not ret:
            raise RuntimeError("Failed to read frame from camera")
        
        frame = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
        video_frame = VideoFrame.from_ndarray(frame, format="rgb24")
        video_frame.pts = pts
        video_frame.time_base = time_base
        
        return video_frame
    
    def stop(self):
        if self.cap:
            self.cap.release()
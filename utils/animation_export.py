"""Export rhythmograms as animated GIF, video, or time-lapse sequences."""

import os
import numpy as np
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtGui import QImage


class FrameCapture:
    """Captures frames from a canvas for animation export."""

    def __init__(self):
        self._frames = []

    def add_frame(self, image: QImage):
        """Add a QImage frame."""
        self._frames.append(image.copy())

    def clear(self):
        self._frames.clear()

    @property
    def frame_count(self) -> int:
        return len(self._frames)

    @property
    def frames(self):
        return self._frames


def qimage_to_pil(image: QImage):
    """Convert QImage to PIL Image."""
    from PIL import Image
    image = image.convertToFormat(QImage.Format.Format_RGBA8888)
    w, h = image.width(), image.height()
    ptr = image.bits()
    ptr.setsize(h * w * 4)
    arr = np.frombuffer(ptr, dtype=np.uint8).reshape((h, w, 4)).copy()
    return Image.fromarray(arr, 'RGBA')


def export_gif(path: str, frames: list, fps: int = 30,
               loop: int = 0) -> bool:
    """Export frames as animated GIF.

    Args:
        path: Output file path
        frames: List of QImage frames
        fps: Frames per second
        loop: 0 = infinite loop, N = loop N times

    Returns True on success, False if Pillow not available.
    """
    try:
        from PIL import Image
    except ImportError:
        return False

    if not frames:
        return False

    pil_frames = [qimage_to_pil(f).convert('RGBA') for f in frames]
    # Convert to palette mode for GIF
    rgb_frames = [f.convert('RGB') for f in pil_frames]

    duration = int(1000 / fps)
    rgb_frames[0].save(
        path,
        save_all=True,
        append_images=rgb_frames[1:],
        duration=duration,
        loop=loop,
        optimize=True,
    )
    return True


def export_video(path: str, frames: list, fps: int = 30) -> bool:
    """Export frames as MP4 video using ffmpeg.

    Returns True on success, False if ffmpeg not available.
    """
    import subprocess
    import tempfile

    if not frames:
        return False

    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False

    try:
        from PIL import Image
    except ImportError:
        return False

    with tempfile.TemporaryDirectory() as tmpdir:
        for i, frame in enumerate(frames):
            pil = qimage_to_pil(frame).convert('RGB')
            pil.save(os.path.join(tmpdir, f"frame_{i:06d}.png"))

        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(fps),
            "-i", os.path.join(tmpdir, "frame_%06d.png"),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-crf", "18",
            path,
        ]
        result = subprocess.run(cmd, capture_output=True)
        return result.returncode == 0


def export_timelapse(path: str, frames: list, skip: int = 5,
                     fps: int = 30) -> bool:
    """Export time-lapse by taking every Nth frame.

    Args:
        skip: Take every Nth frame
        fps: Output framerate

    Returns True on success.
    """
    sampled = frames[::max(1, skip)]
    return export_gif(path, sampled, fps=fps)


def check_pillow_available() -> bool:
    try:
        import PIL
        return True
    except ImportError:
        return False


def check_ffmpeg_available() -> bool:
    import subprocess
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False

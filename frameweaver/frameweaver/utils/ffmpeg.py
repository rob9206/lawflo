"""FFmpeg subprocess wrapper for frame extraction and video processing."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Generator

import numpy as np


@dataclass
class VideoInfo:
    """Basic video stream information."""
    width: int
    height: int
    fps_num: int
    fps_den: int
    total_frames: int
    duration_seconds: float
    codec: str
    pix_fmt: str
    field_order: str  # 'tff', 'bff', 'progressive', 'unknown'
    scan_type: str    # 'interlaced', 'progressive', 'unknown'

    @property
    def fps(self) -> float:
        return self.fps_num / self.fps_den if self.fps_den else 0.0

    @property
    def is_likely_telecined(self) -> bool:
        """Heuristic: 29.97fps interlaced MPEG-2 is often telecined film."""
        return (
            abs(self.fps - 29.97) < 0.1
            and self.scan_type == "interlaced"
            and self.codec in ("mpeg2video", "mpeg2")
        )


def probe_video(path: str | Path) -> VideoInfo:
    """Extract video stream information using ffprobe."""
    path = str(path)
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_streams", "-show_format",
        "-select_streams", "v:0",
        path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)

    if not data.get("streams"):
        raise ValueError(f"No video stream found in {path}")

    stream = data["streams"][0]
    fmt = data.get("format", {})

    # Parse frame rate
    fps_str = stream.get("r_frame_rate", "30000/1001")
    fps_num, fps_den = (int(x) for x in fps_str.split("/"))

    # Parse field order
    field_order_raw = stream.get("field_order", "unknown")
    field_order_map = {
        "tt": "tff", "tb": "tff", "top first": "tff", "top": "tff",
        "bb": "bff", "bt": "bff", "bottom first": "bff", "bottom": "bff",
        "progressive": "progressive",
    }
    field_order = field_order_map.get(field_order_raw.lower(), "unknown")

    # Determine scan type
    scan_type = "progressive" if field_order == "progressive" else (
        "interlaced" if field_order in ("tff", "bff") else "unknown"
    )

    # Total frames — try nb_frames first, fall back to duration * fps
    try:
        total_frames = int(stream.get("nb_frames", 0))
    except (ValueError, TypeError):
        total_frames = 0
    duration = float(fmt.get("duration", stream.get("duration", 0)))
    if total_frames == 0 and duration > 0:
        total_frames = int(duration * fps_num / fps_den)

    return VideoInfo(
        width=int(stream["width"]),
        height=int(stream["height"]),
        fps_num=fps_num,
        fps_den=fps_den,
        total_frames=total_frames,
        duration_seconds=duration,
        codec=stream.get("codec_name", "unknown"),
        pix_fmt=stream.get("pix_fmt", "unknown"),
        field_order=field_order,
        scan_type=scan_type,
    )


class FrameReader:
    """Streams raw Y (luma) frames from video via FFmpeg pipe.

    Outputs grayscale uint8 numpy arrays for fast metric computation.
    Only decodes luma plane — we don't need chroma for detection.
    """

    def __init__(self, path: str | Path, info: VideoInfo | None = None):
        self.path = str(path)
        self.info = info or probe_video(self.path)
        self._frame_size = self.info.width * self.info.height
        self._process: subprocess.Popen | None = None

    def _start_process(self, start_frame: int = 0) -> subprocess.Popen:
        """Start FFmpeg decode process."""
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error"]

        # Seek if needed (fast seek to nearest keyframe)
        if start_frame > 0 and self.info.fps > 0:
            seek_time = start_frame / self.info.fps
            cmd.extend(["-ss", f"{seek_time:.6f}"])

        cmd.extend([
            "-i", self.path,
            "-f", "rawvideo",
            "-pix_fmt", "gray",     # Luma only — 1 byte per pixel
            "-v", "error",
            "-"
        ])

        return subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=self._frame_size * 4,  # Buffer a few frames
        )

    def read_frames(
        self,
        start: int = 0,
        count: int | None = None,
    ) -> Generator[np.ndarray, None, None]:
        """Yield luma frames as (height, width) uint8 numpy arrays.

        Args:
            start: First frame number to read.
            count: Number of frames to read. None = all remaining.

        Yields:
            np.ndarray of shape (height, width), dtype uint8.
        """
        proc = self._start_process(start)
        frames_read = 0

        try:
            while True:
                if count is not None and frames_read >= count:
                    break

                raw = proc.stdout.read(self._frame_size)
                if len(raw) < self._frame_size:
                    break  # End of stream

                frame = np.frombuffer(raw, dtype=np.uint8).reshape(
                    self.info.height, self.info.width
                )
                yield frame
                frames_read += 1
        finally:
            proc.stdout.close()
            proc.stderr.close()
            proc.terminate()
            proc.wait()

    def read_frame_pairs(
        self,
        start: int = 0,
        count: int | None = None,
    ) -> Generator[tuple[np.ndarray, np.ndarray], None, None]:
        """Yield consecutive frame pairs (prev, curr) for comparison metrics.

        Yields:
            Tuple of (previous_frame, current_frame).
        """
        prev = None
        for frame in self.read_frames(start, count):
            if prev is not None:
                yield prev, frame
            prev = frame


class FieldReader:
    """Extracts individual fields (even/odd scanlines) from frames.

    In interlaced video, even lines are one field, odd lines are the other.
    For TFF: even lines = top field (first), odd lines = bottom field (second).
    For BFF: odd lines = top field, even lines = bottom field (first).
    """

    @staticmethod
    def split_fields(frame: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Split frame into top field (even lines) and bottom field (odd lines).

        Returns:
            (top_field, bottom_field) — each is half height.
        """
        return frame[0::2], frame[1::2]

    @staticmethod
    def weave_fields(top: np.ndarray, bottom: np.ndarray) -> np.ndarray:
        """Recombine two fields into a single frame."""
        height = top.shape[0] + bottom.shape[0]
        width = top.shape[1]
        frame = np.empty((height, width), dtype=top.dtype)
        frame[0::2] = top
        frame[1::2] = bottom
        return frame

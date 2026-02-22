"""Frame-level metric extraction for telecine/interlace detection.

Computes per-frame metrics that form the basis for segment classification:
- Comb score (field-line discontinuity)
- Field similarity (repeated field detection)
- Frame similarity (duplicate frame detection)
- Motion energy (static vs. dynamic content)
- Scene change detection

All metrics operate on luma-only frames for speed.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from typing import Generator

import numpy as np

from frameweaver.utils.ffmpeg import FrameReader, FieldReader, VideoInfo


@dataclass
class FrameMetrics:
    """Per-frame analysis metrics."""
    frame_number: int
    comb_score: float = 0.0          # Higher = more combing artifacts
    comb_score_top: float = 0.0      # Combing in top region
    comb_score_mid: float = 0.0      # Combing in middle region
    comb_score_bot: float = 0.0      # Combing in bottom region
    field_similarity: float = 0.0    # Similarity between same-parity fields across frames
    frame_similarity: float = 0.0    # Full-frame similarity to previous frame
    motion_energy: float = 0.0       # Overall motion between frames
    is_scene_change: bool = False    # Sudden content discontinuity
    top_field_diff: float = 0.0      # Difference between current and prev top fields
    bot_field_diff: float = 0.0      # Difference between current and prev bottom fields

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ExtractionResult:
    """Complete analysis result for a video."""
    video_path: str
    video_info: VideoInfo
    metrics: list[FrameMetrics]
    extraction_time_seconds: float
    frames_per_second: float

    @property
    def total_frames(self) -> int:
        return len(self.metrics)


class FrameMetricExtractor:
    """Extracts per-frame metrics for telecine/interlace classification.

    This is the core analysis engine. It streams frames through FFmpeg,
    computes all detection metrics, and outputs a complete metric timeline
    that the classifier uses for segment detection.

    Performance target: ≥60 fps on 480i, ≥30 fps on 1080i.
    """

    # --- Tunable thresholds ---
    COMB_THRESHOLD = 15.0        # Above this = likely combed
    SCENE_CHANGE_THRESHOLD = 40.0  # Frame diff above this = scene change
    DUPLICATE_THRESHOLD = 0.98    # Frame similarity above this = duplicate

    def __init__(self, video_path: str, info: VideoInfo | None = None):
        self.reader = FrameReader(video_path, info)
        self.info = self.reader.info
        self.field_reader = FieldReader()

    def compute_comb_score(self, frame: np.ndarray) -> tuple[float, float, float, float]:
        """Compute combing score — measures field-line discontinuity.

        Combing appears as alternating-line artifacts when two temporally
        different fields are woven together. We detect this by measuring
        the energy of the difference between each line and its neighbors
        two lines away (same-field neighbor vs cross-field neighbor).

        High comb score = interlaced or telecined combed frame.
        Low comb score = progressive or clean telecine frame.

        Returns:
            (overall_score, top_third, middle_third, bottom_third)
        """
        h = frame.shape[0]
        if h < 6:
            return 0.0, 0.0, 0.0, 0.0

        # Core combing metric: for each line, compare it to the lines
        # immediately above and below (cross-field) vs two lines away (same-field).
        # Combed frames show large cross-field differences with small same-field differences.

        # Convert to float32 for precision
        f = frame.astype(np.float32)

        # Cross-field difference: line[n] vs line[n+1] (different fields)
        cross_diff = np.abs(f[:-1] - f[1:])

        # Same-field difference: line[n] vs line[n+2] (same field)
        same_diff = np.abs(f[:-2] - f[2:])

        # Combing energy: where cross-field diff is high AND same-field diff is low,
        # that's classic interlace combing. We use the ratio/difference.
        min_len = min(cross_diff.shape[0], same_diff.shape[0])
        cross_trimmed = cross_diff[:min_len]
        same_trimmed = same_diff[:min_len]

        # Combing = cross_field - same_field, clamped to 0
        # High values mean the line is very different from its immediate neighbor
        # but similar to its same-field neighbor — textbook combing
        comb_energy = np.maximum(cross_trimmed - same_trimmed, 0)

        # Compute per-row mean, then split into thirds for spatial analysis
        row_scores = np.mean(comb_energy, axis=1)
        third = len(row_scores) // 3

        overall = float(np.mean(row_scores))
        top = float(np.mean(row_scores[:third])) if third > 0 else overall
        mid = float(np.mean(row_scores[third:2*third])) if third > 0 else overall
        bot = float(np.mean(row_scores[2*third:])) if third > 0 else overall

        return overall, top, mid, bot

    def compute_field_similarity(
        self,
        curr_frame: np.ndarray,
        prev_frame: np.ndarray,
    ) -> tuple[float, float, float]:
        """Compare same-parity fields between consecutive frames.

        In telecine, repeated fields produce high similarity between the
        top field of frame N and top field of frame N+1 (or bottom fields).
        This is key to detecting the 3:2 pulldown pattern.

        Returns:
            (top_field_diff, bot_field_diff, overall_field_similarity)
            Similarity is 0-1 (1 = identical fields).
        """
        curr_top, curr_bot = self.field_reader.split_fields(curr_frame)
        prev_top, prev_bot = self.field_reader.split_fields(prev_frame)

        # SAD (Sum of Absolute Differences) normalized by pixel count
        top_diff = float(np.mean(np.abs(
            curr_top.astype(np.float32) - prev_top.astype(np.float32)
        )))
        bot_diff = float(np.mean(np.abs(
            curr_bot.astype(np.float32) - prev_bot.astype(np.float32)
        )))

        # Convert to similarity (0-1 range)
        # Max possible diff for uint8 is 255
        similarity = 1.0 - (min(top_diff, bot_diff) / 255.0)

        return top_diff, bot_diff, similarity

    def compute_frame_diff(
        self,
        curr_frame: np.ndarray,
        prev_frame: np.ndarray,
    ) -> tuple[float, float]:
        """Compute frame similarity and motion energy from a single diff pass.

        Returns:
            (frame_similarity, motion_energy)
        """
        mean_abs_diff = float(np.mean(np.abs(
            curr_frame.astype(np.float32) - prev_frame.astype(np.float32)
        )))
        return 1.0 - (mean_abs_diff / 255.0), mean_abs_diff

    def compute_frame_similarity(
        self,
        curr_frame: np.ndarray,
        prev_frame: np.ndarray,
    ) -> float:
        """Full-frame similarity for duplicate detection.

        Returns:
            Similarity 0-1 (1 = identical frames).
        """
        sim, _ = self.compute_frame_diff(curr_frame, prev_frame)
        return sim

    def compute_motion_energy(
        self,
        curr_frame: np.ndarray,
        prev_frame: np.ndarray,
    ) -> float:
        """Overall motion energy between frames.

        Returns:
            Motion energy (mean absolute frame difference).
        """
        _, motion = self.compute_frame_diff(curr_frame, prev_frame)
        return motion

    def detect_scene_change(
        self,
        curr_frame: np.ndarray,
        prev_frame: np.ndarray,
        motion: float | None = None,
    ) -> bool:
        """Detect scene changes via sudden spike in frame difference.

        Scene changes break telecine cadence, so they're important
        for the classifier to handle segment boundaries.
        """
        if motion is None:
            motion = self.compute_motion_energy(curr_frame, prev_frame)
        return motion > self.SCENE_CHANGE_THRESHOLD

    def extract_all(
        self,
        start_frame: int = 0,
        max_frames: int | None = None,
        progress_callback=None,
    ) -> ExtractionResult:
        """Run full metric extraction on the video.

        Args:
            start_frame: First frame to analyze.
            max_frames: Maximum frames to process (None = entire video).
            progress_callback: Optional callable(frames_done, total_frames, fps).

        Returns:
            ExtractionResult with per-frame metrics.
        """
        metrics: list[FrameMetrics] = []
        total = max_frames or self.info.total_frames
        t_start = time.perf_counter()

        prev_frame = None
        frame_idx = start_frame

        for frame in self.reader.read_frames(start=start_frame, count=max_frames):
            m = FrameMetrics(frame_number=frame_idx)

            # Comb score — always computed (doesn't need previous frame)
            m.comb_score, m.comb_score_top, m.comb_score_mid, m.comb_score_bot = (
                self.compute_comb_score(frame)
            )

            # Metrics requiring previous frame
            if prev_frame is not None:
                m.top_field_diff, m.bot_field_diff, m.field_similarity = (
                    self.compute_field_similarity(frame, prev_frame)
                )
                m.frame_similarity, m.motion_energy = (
                    self.compute_frame_diff(frame, prev_frame)
                )
                m.is_scene_change = m.motion_energy > self.SCENE_CHANGE_THRESHOLD

            metrics.append(m)
            prev_frame = frame
            frame_idx += 1

            # Progress reporting
            if progress_callback and frame_idx % 100 == 0:
                elapsed = time.perf_counter() - t_start
                fps = len(metrics) / elapsed if elapsed > 0 else 0
                progress_callback(len(metrics), total, fps)

        elapsed = time.perf_counter() - t_start
        fps = len(metrics) / elapsed if elapsed > 0 else 0

        return ExtractionResult(
            video_path=self.reader.path,
            video_info=self.info,
            metrics=metrics,
            extraction_time_seconds=elapsed,
            frames_per_second=fps,
        )

    def extract_sample(
        self,
        sample_points: int = 5,
        frames_per_sample: int = 150,
    ) -> ExtractionResult:
        """Quick analysis by sampling multiple points in the video.

        Useful for fast classification of straightforward content
        without analyzing every frame. Samples evenly-spaced segments
        throughout the video.

        Note: Sample positions are approximate because FFmpeg's ``-ss``
        before ``-i`` seeks to the nearest keyframe, not the exact frame.

        Args:
            sample_points: Number of positions to sample.
            frames_per_sample: Frames to analyze at each position.

        Returns:
            ExtractionResult with sampled metrics (non-contiguous frame numbers).
        """
        total = self.info.total_frames
        if total <= frames_per_sample * sample_points:
            # Video is short enough to analyze entirely
            return self.extract_all()

        all_metrics: list[FrameMetrics] = []
        t_start = time.perf_counter()

        spacing = total // (sample_points + 1)
        for i in range(sample_points):
            start = spacing * (i + 1)
            for frame_metrics in self._extract_range(start, frames_per_sample):
                all_metrics.append(frame_metrics)

        elapsed = time.perf_counter() - t_start
        fps = len(all_metrics) / elapsed if elapsed > 0 else 0

        return ExtractionResult(
            video_path=self.reader.path,
            video_info=self.info,
            metrics=all_metrics,
            extraction_time_seconds=elapsed,
            frames_per_second=fps,
        )

    def _extract_range(
        self, start: int, count: int,
    ) -> Generator[FrameMetrics, None, None]:
        """Extract metrics for a specific frame range."""
        prev_frame = None
        frame_idx = start

        for frame in self.reader.read_frames(start=start, count=count):
            m = FrameMetrics(frame_number=frame_idx)
            m.comb_score, m.comb_score_top, m.comb_score_mid, m.comb_score_bot = (
                self.compute_comb_score(frame)
            )
            if prev_frame is not None:
                m.top_field_diff, m.bot_field_diff, m.field_similarity = (
                    self.compute_field_similarity(frame, prev_frame)
                )
                m.frame_similarity, m.motion_energy = (
                    self.compute_frame_diff(frame, prev_frame)
                )
                m.is_scene_change = m.motion_energy > self.SCENE_CHANGE_THRESHOLD
            prev_frame = frame
            frame_idx += 1
            yield m

"""Video segment classification engine.

Takes per-frame metrics and cadence analysis results, then classifies
contiguous segments of the video as telecine, interlaced, progressive,
hybrid, or unknown. Applies hysteresis and smoothing to prevent noisy
segment boundaries.

The classifier outputs a segment map that drives the processing pipeline
and the review UI.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np

from frameweaver.analysis.extractor import FrameMetrics, ExtractionResult
from frameweaver.analysis.cadence import CadenceDetector, CadenceResult, CadenceType, CadenceBreak


class SegmentType(Enum):
    """Classification categories for video segments."""
    TELECINE = "telecine"          # 3:2 pulldown detected — needs IVTC
    INTERLACED = "interlaced"      # True interlace — needs deinterlacing
    PROGRESSIVE = "progressive"    # Already progressive — passthrough
    HYBRID = "hybrid"              # Mixed content — partial confidence
    UNKNOWN = "unknown"            # Low confidence — needs human review


@dataclass
class Segment:
    """A classified contiguous segment of the video."""
    start_frame: int
    end_frame: int
    segment_type: SegmentType
    confidence: float            # 0.0 - 1.0
    needs_review: bool           # Flag for human review
    cadence: CadenceResult | None = None
    cadence_breaks: list[CadenceBreak] = field(default_factory=list)

    # Summary statistics for the segment
    mean_comb_score: float = 0.0
    combed_frame_ratio: float = 0.0
    mean_motion_energy: float = 0.0
    scene_change_count: int = 0

    @property
    def frame_count(self) -> int:
        return self.end_frame - self.start_frame + 1

    @property
    def duration_at_fps(self) -> float:
        """Duration in seconds at 29.97fps (NTSC)."""
        return self.frame_count / 29.97

    def to_dict(self) -> dict:
        d = {
            "start_frame": self.start_frame,
            "end_frame": self.end_frame,
            "frame_count": self.frame_count,
            "segment_type": self.segment_type.value,
            "confidence": round(self.confidence, 4),
            "needs_review": self.needs_review,
            "mean_comb_score": round(self.mean_comb_score, 2),
            "combed_frame_ratio": round(self.combed_frame_ratio, 4),
            "mean_motion_energy": round(self.mean_motion_energy, 2),
            "scene_change_count": self.scene_change_count,
            "cadence_breaks": len(self.cadence_breaks),
        }
        if self.cadence:
            d["cadence_type"] = self.cadence.cadence_type.value
            d["cadence_period"] = self.cadence.period
            d["cadence_phase"] = self.cadence.phase
        return d


@dataclass
class ClassificationResult:
    """Complete classification of a video into segments."""
    video_path: str
    segments: list[Segment]
    total_frames: int
    summary: dict[str, Any] = field(default_factory=dict)

    @property
    def needs_review_count(self) -> int:
        return sum(1 for s in self.segments if s.needs_review)

    @property
    def review_frame_count(self) -> int:
        return sum(s.frame_count for s in self.segments if s.needs_review)

    @property
    def review_percentage(self) -> float:
        if self.total_frames == 0:
            return 0.0
        return (self.review_frame_count / self.total_frames) * 100

    def to_dict(self) -> dict:
        return {
            "video_path": self.video_path,
            "total_frames": self.total_frames,
            "total_segments": len(self.segments),
            "needs_review": self.needs_review_count,
            "review_percentage": round(self.review_percentage, 2),
            "summary": self.summary,
            "segments": [s.to_dict() for s in self.segments],
        }

    def to_json(self, path: str | Path | None = None, indent: int = 2) -> str:
        """Serialize to JSON. Optionally write to file."""
        data = json.dumps(self.to_dict(), indent=indent)
        if path:
            Path(path).write_text(data)
        return data

    @classmethod
    def from_json(cls, path: str | Path) -> "ClassificationResult":
        """Load classification result from JSON file."""
        data = json.loads(Path(path).read_text())
        segments = []
        for sd in data["segments"]:
            seg = Segment(
                start_frame=sd["start_frame"],
                end_frame=sd["end_frame"],
                segment_type=SegmentType(sd["segment_type"]),
                confidence=sd["confidence"],
                needs_review=sd["needs_review"],
                mean_comb_score=sd.get("mean_comb_score", 0),
                combed_frame_ratio=sd.get("combed_frame_ratio", 0),
                mean_motion_energy=sd.get("mean_motion_energy", 0),
                scene_change_count=sd.get("scene_change_count", 0),
            )
            segments.append(seg)
        return cls(
            video_path=data["video_path"],
            segments=segments,
            total_frames=data["total_frames"],
            summary=data.get("summary", {}),
        )


class SegmentClassifier:
    """Classifies video content into typed segments.

    Pipeline:
    1. Sliding window cadence analysis
    2. Per-window classification (telecine / interlace / progressive)
    3. Window merging into contiguous segments
    4. Hysteresis smoothing (prevent rapid segment switching)
    5. Confidence assessment and review flagging
    """

    # --- Configuration ---
    WINDOW_SIZE = 50            # Frames per analysis window
    WINDOW_STEP = 10            # Step between windows (overlap = window - step)
    MIN_SEGMENT_FRAMES = 30     # Minimum segment length (shorter = merge with neighbor)

    # Classification thresholds
    COMB_THRESHOLD = 10.0       # Above this = combed frame
    INTERLACE_COMBED_RATIO = 0.75  # >75% combed motion frames = true interlace
    PROGRESSIVE_MAX_COMB = 5.0  # All combs below this = progressive
    REVIEW_CONFIDENCE = 0.65    # Below this = flag for review
    HYBRID_CONFIDENCE = 0.50    # Below this = mark as unknown

    def __init__(self):
        self.cadence_detector = CadenceDetector()

    def classify(self, extraction: ExtractionResult) -> ClassificationResult:
        """Run full classification pipeline on extracted metrics.

        Args:
            extraction: Result from FrameMetricExtractor.

        Returns:
            ClassificationResult with segment map.
        """
        metrics = extraction.metrics
        if not metrics:
            return ClassificationResult(
                video_path=extraction.video_path,
                segments=[],
                total_frames=0,
            )

        # Short-clip path: fewer frames than one window
        if len(metrics) < self.WINDOW_SIZE:
            cadence = self.cadence_detector.analyze_window(metrics)
            seg_type, confidence = self._classify_single_window(metrics, cadence)
            seg = Segment(
                start_frame=metrics[0].frame_number,
                end_frame=metrics[-1].frame_number,
                segment_type=seg_type,
                confidence=confidence,
                needs_review=False,
                cadence=cadence,
            )
            frame_index: dict[int, int] = {
                m.frame_number: i for i, m in enumerate(metrics)
            }
            self._compute_segment_stats(seg, metrics, frame_index)
            seg.needs_review = (
                seg.confidence < self.REVIEW_CONFIDENCE
                or seg.segment_type in (SegmentType.HYBRID, SegmentType.UNKNOWN)
                or len(seg.cadence_breaks) > 3
            )
            summary = self._build_summary([seg], metrics)
            return ClassificationResult(
                video_path=extraction.video_path,
                segments=[seg],
                total_frames=len(metrics),
                summary=summary,
            )

        # Step 1: Sliding window classification
        window_labels = self._classify_windows(metrics)

        # Step 2: Merge adjacent windows with same label
        raw_segments = self._merge_windows(window_labels, metrics)

        # Step 3: Apply hysteresis — absorb tiny segments into neighbors
        smoothed = self._apply_hysteresis(raw_segments)

        # Build frame_number -> index mapping for fast segment lookups
        frame_index = {m.frame_number: i for i, m in enumerate(metrics)}

        # Step 4: Compute segment statistics and flag for review
        for seg in smoothed:
            self._compute_segment_stats(seg, metrics, frame_index)
            seg.needs_review = (
                seg.confidence < self.REVIEW_CONFIDENCE
                or seg.segment_type in (SegmentType.HYBRID, SegmentType.UNKNOWN)
                or len(seg.cadence_breaks) > 3
            )

        # Step 5: Build summary
        summary = self._build_summary(smoothed, metrics)

        return ClassificationResult(
            video_path=extraction.video_path,
            segments=smoothed,
            total_frames=len(metrics),
            summary=summary,
        )

    def _classify_windows(
        self, metrics: list[FrameMetrics],
    ) -> list[tuple[int, int, SegmentType, float, CadenceResult | None]]:
        """Classify overlapping windows across the video.

        Returns:
            List of (start_frame, end_frame, type, confidence, cadence).
        """
        results = []

        for i in range(0, len(metrics) - self.WINDOW_SIZE + 1, self.WINDOW_STEP):
            window = metrics[i : i + self.WINDOW_SIZE]
            start = window[0].frame_number
            end = window[-1].frame_number

            # Cadence analysis
            cadence = self.cadence_detector.analyze_window(window)

            # Classification logic
            seg_type, confidence = self._classify_single_window(window, cadence)

            results.append((start, end, seg_type, confidence, cadence))

        return results

    def _classify_single_window(
        self,
        window: list[FrameMetrics],
        cadence: CadenceResult,
    ) -> tuple[SegmentType, float]:
        """Classify a single window of frames.

        Decision tree:
        1. Strong cadence detected → TELECINE
        2. High combed ratio with no cadence → INTERLACED
        3. Low comb everywhere → PROGRESSIVE
        4. Mixed signals → HYBRID or UNKNOWN
        """
        comb_scores = np.array([m.comb_score for m in window])
        motion = np.array([m.motion_energy for m in window])

        # Only consider frames with motion for combing analysis
        motion_mask = motion > 2.0
        motion_count = int(np.sum(motion_mask))

        if motion_count < 5:
            # Mostly static — classify as progressive (can't tell)
            return SegmentType.PROGRESSIVE, 0.7

        motion_combs = comb_scores[motion_mask]
        combed_ratio = float(np.mean(motion_combs > self.COMB_THRESHOLD))

        # Check for telecine
        if cadence.cadence_type == CadenceType.TELECINE_32:
            if cadence.confidence > 0.7:
                return SegmentType.TELECINE, cadence.confidence
            elif cadence.confidence > 0.5:
                return SegmentType.TELECINE, cadence.confidence * 0.9

        if cadence.cadence_type == CadenceType.TELECINE_22:
            if cadence.confidence > 0.7:
                return SegmentType.TELECINE, cadence.confidence

        # Check for true interlace (high combing, no cadence)
        if combed_ratio > self.INTERLACE_COMBED_RATIO:
            if cadence.cadence_type == CadenceType.NONE:
                return SegmentType.INTERLACED, combed_ratio
            else:
                # High combing but some cadence — possibly broken telecine
                return SegmentType.HYBRID, 0.5

        # Check for progressive (very low combing)
        max_comb = float(np.max(comb_scores)) if len(comb_scores) > 0 else 0
        if max_comb < self.PROGRESSIVE_MAX_COMB:
            return SegmentType.PROGRESSIVE, 0.95

        mean_comb = float(np.mean(comb_scores))
        if mean_comb < self.COMB_THRESHOLD * 0.5 and combed_ratio < 0.1:
            return SegmentType.PROGRESSIVE, 0.85

        # Mixed signals
        if cadence.cadence_type == CadenceType.IRREGULAR:
            return SegmentType.HYBRID, max(0.3, cadence.confidence)

        # Low combing but not clearly progressive
        if combed_ratio < 0.3:
            return SegmentType.PROGRESSIVE, 0.6

        # Unclear — flag for review
        return SegmentType.UNKNOWN, 0.3

    def _merge_windows(
        self,
        window_labels: list[tuple[int, int, SegmentType, float, CadenceResult | None]],
        metrics: list[FrameMetrics],
    ) -> list[Segment]:
        """Merge adjacent windows with the same classification into segments.

        Segment boundaries are placed at window step boundaries — one frame
        before the next window's start — so segments are contiguous and
        non-overlapping regardless of window overlap.
        """
        if not window_labels:
            return []

        segments: list[Segment] = []
        current_start = window_labels[0][0]
        current_type = window_labels[0][2]
        current_confidences: list[float] = [window_labels[0][3]]
        current_cadence = window_labels[0][4]

        for i in range(1, len(window_labels)):
            _, _, seg_type, conf, cadence = window_labels[i]

            if seg_type == current_type:
                # Same type — extend current segment
                current_confidences.append(conf)
            else:
                # Type changed — close at the step boundary (one frame before
                # the next window starts) to prevent overlap with next segment
                segments.append(Segment(
                    start_frame=current_start,
                    end_frame=window_labels[i][0] - 1,
                    segment_type=current_type,
                    confidence=float(np.mean(current_confidences)),
                    needs_review=False,
                    cadence=current_cadence,
                ))
                current_start = window_labels[i][0]
                current_type = seg_type
                current_confidences = [conf]
                current_cadence = cadence

        # Close final segment — always extends to the last analyzed frame
        segments.append(Segment(
            start_frame=current_start,
            end_frame=metrics[-1].frame_number,
            segment_type=current_type,
            confidence=float(np.mean(current_confidences)),
            needs_review=False,
            cadence=current_cadence,
        ))

        return segments

    def _apply_hysteresis(self, segments: list[Segment]) -> list[Segment]:
        """Absorb tiny segments into their neighbors.

        Short segments (< MIN_SEGMENT_FRAMES) are likely noise.
        Merge them into the adjacent segment with higher confidence.
        """
        if len(segments) <= 1:
            return segments

        # Mark segments too short for independent classification
        changed = True
        while changed:
            changed = False
            new_segments: list[Segment] = []

            for i, seg in enumerate(segments):
                if seg.frame_count < self.MIN_SEGMENT_FRAMES:
                    # Absorb into neighbor with higher confidence
                    if i > 0 and (i == len(segments) - 1
                                  or segments[i - 1].confidence >= segments[i + 1].confidence):
                        # Merge into previous
                        if new_segments:
                            new_segments[-1].end_frame = seg.end_frame
                            changed = True
                            continue
                    elif i < len(segments) - 1:
                        # Merge into next (extend next's start)
                        segments[i + 1].start_frame = seg.start_frame
                        changed = True
                        continue

                new_segments.append(seg)

            segments = new_segments

        # Merge consecutive segments of the same type
        merged: list[Segment] = [segments[0]] if segments else []
        for seg in segments[1:]:
            if seg.segment_type == merged[-1].segment_type:
                merged[-1].end_frame = seg.end_frame
                merged[-1].confidence = (merged[-1].confidence + seg.confidence) / 2
            else:
                merged.append(seg)

        return merged

    def _compute_segment_stats(
        self,
        segment: Segment,
        all_metrics: list[FrameMetrics],
        frame_index: dict[int, int] | None = None,
    ) -> None:
        """Compute summary statistics for a segment."""
        if frame_index is not None:
            start_idx = frame_index.get(segment.start_frame)
            end_idx = frame_index.get(segment.end_frame)
            if start_idx is not None and end_idx is not None:
                seg_metrics = all_metrics[start_idx:end_idx + 1]
            else:
                seg_metrics = [
                    m for m in all_metrics
                    if segment.start_frame <= m.frame_number <= segment.end_frame
                ]
        else:
            seg_metrics = [
                m for m in all_metrics
                if segment.start_frame <= m.frame_number <= segment.end_frame
            ]

        if not seg_metrics:
            return

        combs = [m.comb_score for m in seg_metrics]
        segment.mean_comb_score = float(np.mean(combs))
        segment.combed_frame_ratio = float(
            np.mean([1 if c > self.COMB_THRESHOLD else 0 for c in combs])
        )
        segment.mean_motion_energy = float(np.mean([m.motion_energy for m in seg_metrics]))
        segment.scene_change_count = sum(1 for m in seg_metrics if m.is_scene_change)

        # Detect cadence breaks within this segment
        segment.cadence_breaks = self.cadence_detector.detect_breaks(seg_metrics)

    def _build_summary(
        self, segments: list[Segment], metrics: list[FrameMetrics],
    ) -> dict[str, Any]:
        """Build overall classification summary."""
        total_frames = len(metrics)
        if total_frames == 0:
            return {}

        type_frames: dict[str, int] = {}
        for seg in segments:
            key = seg.segment_type.value
            type_frames[key] = type_frames.get(key, 0) + seg.frame_count

        type_pct = {k: round(v / total_frames * 100, 1) for k, v in type_frames.items()}

        # Determine dominant type
        dominant = max(type_frames, key=type_frames.get) if type_frames else "unknown"

        # Overall recommendation
        if type_pct.get("telecine", 0) > 90:
            recommendation = "Standard IVTC — entire video is telecined"
        elif type_pct.get("progressive", 0) > 90:
            recommendation = "No processing needed — video is progressive"
        elif type_pct.get("interlaced", 0) > 90:
            recommendation = "Full deinterlace — video is true interlace"
        elif type_pct.get("telecine", 0) > 50:
            recommendation = "IVTC with hybrid fallback — mostly telecined with some mixed segments"
        else:
            recommendation = "Mixed content — segment-by-segment processing recommended with manual review"

        return {
            "dominant_type": dominant,
            "type_percentages": type_pct,
            "total_segments": len(segments),
            "segments_needing_review": sum(1 for s in segments if s.needs_review),
            "recommendation": recommendation,
        }

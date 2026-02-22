"""Tests for Frameweaver analysis engine.

Tests use synthetic frames to validate metric computation
without requiring actual video files.
"""

import numpy as np
import pytest

from frameweaver.analysis.extractor import FrameMetricExtractor, FrameMetrics
from frameweaver.analysis.cadence import CadenceDetector, CadenceType
from frameweaver.analysis.classifier import SegmentClassifier, SegmentType
from frameweaver.utils.ffmpeg import FieldReader


# ── Helpers ──────────────────────────────────────────────────────


def make_progressive_frame(width=720, height=480, seed=None) -> np.ndarray:
    """Create a synthetic progressive frame (no combing)."""
    rng = np.random.default_rng(seed)
    # Smooth gradient + noise — adjacent lines are similar
    base = np.tile(np.linspace(50, 200, height, dtype=np.float64)[:, None], (1, width))
    noise = rng.normal(0, 5, (height, width))
    return np.clip(base + noise, 0, 255).astype(np.uint8)


def make_combed_frame(width=720, height=480, seed=None) -> np.ndarray:
    """Create a synthetic combed/interlaced frame.

    Simulates two temporally different fields woven together,
    producing alternating-line artifacts in motion areas.
    """
    rng = np.random.default_rng(seed)
    # Field A: bright moving object
    field_a = rng.integers(100, 180, (height // 2, width), dtype=np.uint8)
    # Field B: same object shifted — creates combing
    field_b = rng.integers(60, 140, (height // 2, width), dtype=np.uint8)

    # Weave fields together
    frame = np.empty((height, width), dtype=np.uint8)
    frame[0::2] = field_a
    frame[1::2] = field_b
    return frame


def make_static_frame(width=720, height=480, value=128) -> np.ndarray:
    """Create a flat static frame (no motion, no combing)."""
    return np.full((height, width), value, dtype=np.uint8)


def make_telecine_sequence(n_cycles=6, width=720, height=480) -> list[np.ndarray]:
    """Generate synthetic telecined frame sequence.

    Simulates 3:2 pulldown: 3 clean frames + 2 combed frames per 5-frame cycle.
    """
    frames = []
    for cycle in range(n_cycles):
        seed_base = cycle * 10
        # 3 clean progressive frames
        frames.append(make_progressive_frame(width, height, seed=seed_base))
        frames.append(make_progressive_frame(width, height, seed=seed_base + 1))
        frames.append(make_progressive_frame(width, height, seed=seed_base + 2))
        # 2 combed frames
        frames.append(make_combed_frame(width, height, seed=seed_base + 3))
        frames.append(make_combed_frame(width, height, seed=seed_base + 4))
    return frames


def make_interlaced_sequence(n_frames=30, width=720, height=480) -> list[np.ndarray]:
    """Generate synthetic interlaced sequence (every frame combed)."""
    return [make_combed_frame(width, height, seed=i) for i in range(n_frames)]


def make_progressive_sequence(n_frames=30, width=720, height=480) -> list[np.ndarray]:
    """Generate synthetic progressive sequence (no combing)."""
    return [make_progressive_frame(width, height, seed=i) for i in range(n_frames)]


def frames_to_metrics(
    frames: list[np.ndarray],
    extractor_cls=FrameMetricExtractor,
) -> list[FrameMetrics]:
    """Compute metrics for a list of synthetic frames without reading from file."""
    # We bypass FrameReader and compute metrics directly
    field_reader = FieldReader()
    metrics = []
    prev = None

    for i, frame in enumerate(frames):
        m = FrameMetrics(frame_number=i)

        # Create a temporary extractor to use its methods
        # We need to call the static computation methods
        ext = object.__new__(FrameMetricExtractor)
        ext.field_reader = field_reader

        m.comb_score, m.comb_score_top, m.comb_score_mid, m.comb_score_bot = (
            ext.compute_comb_score(frame)
        )

        if prev is not None:
            m.top_field_diff, m.bot_field_diff, m.field_similarity = (
                ext.compute_field_similarity(frame, prev)
            )
            m.frame_similarity, m.motion_energy = ext.compute_frame_diff(frame, prev)
            m.is_scene_change = ext.detect_scene_change(frame, prev, m.motion_energy)

        metrics.append(m)
        prev = frame

    return metrics


# ── Comb Score Tests ─────────────────────────────────────────────


class TestCombScore:
    """Validate comb score computation."""

    def setup_method(self):
        self.ext = object.__new__(FrameMetricExtractor)
        self.ext.field_reader = FieldReader()

    def test_progressive_frame_low_comb(self):
        """Progressive frames should have low comb scores."""
        frame = make_progressive_frame(seed=42)
        score, _, _, _ = self.ext.compute_comb_score(frame)
        assert score < 10.0, f"Progressive frame comb score too high: {score}"

    def test_combed_frame_high_comb(self):
        """Combed frames should have high comb scores."""
        frame = make_combed_frame(seed=42)
        score, _, _, _ = self.ext.compute_comb_score(frame)
        assert score > 10.0, f"Combed frame comb score too low: {score}"

    def test_static_frame_low_comb(self):
        """Static (flat) frames should have zero/near-zero comb scores."""
        frame = make_static_frame()
        score, _, _, _ = self.ext.compute_comb_score(frame)
        assert score < 1.0, f"Static frame comb score too high: {score}"

    def test_comb_separation(self):
        """Combed frames must score significantly higher than progressive."""
        prog_score, _, _, _ = self.ext.compute_comb_score(make_progressive_frame(seed=1))
        comb_score, _, _, _ = self.ext.compute_comb_score(make_combed_frame(seed=1))
        assert comb_score > prog_score * 2, (
            f"Insufficient separation: progressive={prog_score:.2f}, combed={comb_score:.2f}"
        )

    def test_spatial_regions(self):
        """Comb score should be computed for top/mid/bot regions."""
        frame = make_combed_frame(seed=42)
        overall, top, mid, bot = self.ext.compute_comb_score(frame)
        # All regions should be non-zero for a fully combed frame
        assert top > 0 and mid > 0 and bot > 0
        # Overall should be close to average of regions
        region_avg = (top + mid + bot) / 3
        assert abs(overall - region_avg) < overall * 0.5


# ── Field / Frame Similarity Tests ───────────────────────────────


class TestSimilarity:
    """Validate frame and field similarity metrics."""

    def setup_method(self):
        self.ext = object.__new__(FrameMetricExtractor)
        self.ext.field_reader = FieldReader()

    def test_identical_frames_high_similarity(self):
        """Identical frames should have similarity close to 1.0."""
        frame = make_progressive_frame(seed=42)
        sim = self.ext.compute_frame_similarity(frame, frame.copy())
        assert sim > 0.99, f"Identical frame similarity too low: {sim}"

    def test_different_frames_lower_similarity(self):
        """Different frames should have lower similarity."""
        a = make_progressive_frame(seed=1)
        # Create a substantially different frame (inverted + noise)
        b = (255 - a).astype(np.uint8)
        sim = self.ext.compute_frame_similarity(a, b)
        assert sim < 0.75, f"Inverted frame similarity too high: {sim}"

    def test_field_similarity_repeated_field(self):
        """When top field is repeated, top_field_diff should be near zero."""
        frame_a = make_progressive_frame(seed=42)
        # Create frame_b with same top field but different bottom
        frame_b = frame_a.copy()
        frame_b[1::2] = make_progressive_frame(seed=99)[1::2]  # Replace bottom field

        top_diff, bot_diff, _ = self.ext.compute_field_similarity(frame_b, frame_a)
        assert top_diff < bot_diff, (
            f"Repeated top field should have lower diff: top={top_diff}, bot={bot_diff}"
        )


# ── Cadence Detection Tests ──────────────────────────────────────


class TestCadenceDetector:
    """Validate telecine cadence detection."""

    def setup_method(self):
        self.detector = CadenceDetector()

    def test_telecine_detected(self):
        """Standard 3:2 pulldown sequence should be classified as telecine."""
        frames = make_telecine_sequence(n_cycles=8)
        metrics = frames_to_metrics(frames)
        result = self.detector.analyze_window(metrics)

        assert result.cadence_type == CadenceType.TELECINE_32, (
            f"Expected TELECINE_32, got {result.cadence_type}"
        )
        assert result.confidence > 0.5, f"Confidence too low: {result.confidence}"
        assert result.period == 5

    def test_interlace_no_cadence(self):
        """True interlace (every frame combed) should show no telecine cadence."""
        frames = make_interlaced_sequence(n_frames=40)
        metrics = frames_to_metrics(frames)
        result = self.detector.analyze_window(metrics)

        assert result.cadence_type != CadenceType.TELECINE_32, (
            f"Interlaced content misdetected as telecine"
        )

    def test_progressive_no_cadence(self):
        """Progressive content should show no cadence."""
        frames = make_progressive_sequence(n_frames=40)
        metrics = frames_to_metrics(frames)
        result = self.detector.analyze_window(metrics)

        assert result.cadence_type in (CadenceType.NONE, CadenceType.IRREGULAR)

    def test_short_window_handled(self):
        """Windows shorter than minimum should return NONE gracefully."""
        metrics = frames_to_metrics(make_progressive_sequence(n_frames=5))
        result = self.detector.analyze_window(metrics)
        assert result.cadence_type == CadenceType.NONE

    def test_cadence_break_detection(self):
        """Should detect cadence breaks at content transitions."""
        # Telecine -> Progressive transition
        telecine = make_telecine_sequence(n_cycles=6)
        progressive = make_progressive_sequence(n_frames=30)
        combined = telecine + progressive
        metrics = frames_to_metrics(combined)

        breaks = self.detector.detect_breaks(metrics, window_size=20, step=5)
        # Should find at least one break near the transition point
        assert len(breaks) > 0, "No cadence breaks detected at transition"


# ── Segment Classifier Tests ─────────────────────────────────────


class TestSegmentClassifier:
    """Validate segment classification logic."""

    def setup_method(self):
        self.classifier = SegmentClassifier()

    def _make_extraction_result(self, frames):
        """Helper to create a mock ExtractionResult from frames."""
        from frameweaver.analysis.extractor import ExtractionResult
        from frameweaver.utils.ffmpeg import VideoInfo

        metrics = frames_to_metrics(frames)
        info = VideoInfo(
            width=720, height=480, fps_num=30000, fps_den=1001,
            total_frames=len(frames), duration_seconds=len(frames) / 29.97,
            codec="mpeg2video", pix_fmt="yuv420p",
            field_order="tff", scan_type="interlaced",
        )
        return ExtractionResult(
            video_path="test.vob",
            video_info=info,
            metrics=metrics,
            extraction_time_seconds=0.1,
            frames_per_second=1000,
        )

    def test_pure_telecine_classification(self):
        """Pure telecine content should classify as TELECINE."""
        frames = make_telecine_sequence(n_cycles=20)
        extraction = self._make_extraction_result(frames)
        result = self.classifier.classify(extraction)

        telecine_frames = sum(
            s.frame_count for s in result.segments
            if s.segment_type == SegmentType.TELECINE
        )
        total = sum(s.frame_count for s in result.segments)
        telecine_pct = telecine_frames / total if total else 0

        assert telecine_pct > 0.5, (
            f"Only {telecine_pct*100:.1f}% classified as telecine"
        )

    def test_pure_interlace_classification(self):
        """Pure interlaced content should classify as INTERLACED."""
        frames = make_interlaced_sequence(n_frames=100)
        extraction = self._make_extraction_result(frames)
        result = self.classifier.classify(extraction)

        interlaced_frames = sum(
            s.frame_count for s in result.segments
            if s.segment_type == SegmentType.INTERLACED
        )
        total = sum(s.frame_count for s in result.segments)
        interlaced_pct = interlaced_frames / total if total else 0

        assert interlaced_pct > 0.5, (
            f"Only {interlaced_pct*100:.1f}% classified as interlaced"
        )

    def test_pure_progressive_classification(self):
        """Pure progressive content should classify as PROGRESSIVE."""
        frames = make_progressive_sequence(n_frames=100)
        extraction = self._make_extraction_result(frames)
        result = self.classifier.classify(extraction)

        progressive_frames = sum(
            s.frame_count for s in result.segments
            if s.segment_type == SegmentType.PROGRESSIVE
        )
        total = sum(s.frame_count for s in result.segments)
        prog_pct = progressive_frames / total if total else 0

        assert prog_pct > 0.5, (
            f"Only {prog_pct*100:.1f}% classified as progressive"
        )

    def test_hybrid_content_detection(self):
        """Mixed telecine + interlace should produce multiple segment types."""
        telecine = make_telecine_sequence(n_cycles=10)
        interlaced = make_interlaced_sequence(n_frames=50)
        combined = telecine + interlaced
        extraction = self._make_extraction_result(combined)
        result = self.classifier.classify(extraction)

        types = set(s.segment_type for s in result.segments)
        assert len(types) >= 2, (
            f"Expected at least 2 segment types in hybrid content, got {types}"
        )

    def test_segments_non_overlapping(self):
        """Classified segments must be strictly non-overlapping and contiguous."""
        telecine = make_telecine_sequence(n_cycles=10)
        interlaced = make_interlaced_sequence(n_frames=50)
        extraction = self._make_extraction_result(telecine + interlaced)
        result = self.classifier.classify(extraction)

        segs = result.segments
        assert segs, "Expected at least one segment"
        for i in range(len(segs) - 1):
            a, b = segs[i], segs[i + 1]
            assert a.end_frame < b.start_frame, (
                f"Segment {i} (frames {a.start_frame}-{a.end_frame}) "
                f"overlaps segment {i+1} "
                f"(frames {b.start_frame}-{b.end_frame})"
            )
            assert a.end_frame + 1 == b.start_frame, (
                f"Gap between segment {i} and {i+1}: "
                f"ends at {a.end_frame}, next starts at {b.start_frame}"
            )

    def test_segment_frame_count_totals(self):
        """Sum of segment frame_counts must equal total_frames."""
        frames = make_progressive_sequence(n_frames=100)
        extraction = self._make_extraction_result(frames)
        result = self.classifier.classify(extraction)

        total = sum(s.frame_count for s in result.segments)
        assert total == result.total_frames, (
            f"Segments sum to {total} frames, "
            f"total_frames is {result.total_frames}"
        )
        pcts = result.summary.get("type_percentages", {})
        pct_sum = sum(pcts.values())
        assert pct_sum <= 100.1, (
            f"type_percentages sum exceeds 100%: {pct_sum:.1f}%"
        )

    def test_short_clip_classification(self):
        """Clips shorter than WINDOW_SIZE must still yield a classified segment."""
        n_frames = SegmentClassifier.WINDOW_SIZE - 1
        frames = make_telecine_sequence(n_cycles=n_frames // 5)
        # Trim to exactly n_frames
        frames = frames[:n_frames]
        assert len(frames) < SegmentClassifier.WINDOW_SIZE

        extraction = self._make_extraction_result(frames)
        result = self.classifier.classify(extraction)

        assert len(result.segments) >= 1, (
            f"Short clip ({len(frames)} frames) produced no segments"
        )
        assert result.segments[0].start_frame == 0
        assert result.segments[-1].end_frame == len(frames) - 1

    def test_json_roundtrip(self):
        """Classification results should survive JSON serialization."""
        frames = make_telecine_sequence(n_cycles=10)
        extraction = self._make_extraction_result(frames)
        result = self.classifier.classify(extraction)

        # Serialize
        json_str = result.to_json()

        # Deserialize
        import tempfile, os
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(json_str)
            tmp_path = f.name

        try:
            from frameweaver.analysis.classifier import ClassificationResult
            loaded = ClassificationResult.from_json(tmp_path)

            assert loaded.total_frames == result.total_frames
            assert len(loaded.segments) == len(result.segments)
            for orig, loaded_seg in zip(result.segments, loaded.segments):
                assert orig.segment_type == loaded_seg.segment_type
                assert orig.start_frame == loaded_seg.start_frame
                assert orig.end_frame == loaded_seg.end_frame
        finally:
            os.unlink(tmp_path)

    def test_empty_input(self):
        """Empty input should return empty classification gracefully."""
        from frameweaver.analysis.extractor import ExtractionResult
        from frameweaver.utils.ffmpeg import VideoInfo

        info = VideoInfo(
            width=720, height=480, fps_num=30000, fps_den=1001,
            total_frames=0, duration_seconds=0,
            codec="mpeg2video", pix_fmt="yuv420p",
            field_order="tff", scan_type="interlaced",
        )
        extraction = ExtractionResult(
            video_path="empty.vob", video_info=info,
            metrics=[], extraction_time_seconds=0, frames_per_second=0,
        )
        result = self.classifier.classify(extraction)
        assert len(result.segments) == 0
        assert result.needs_review_count == 0


# ── Field Reader Tests ───────────────────────────────────────────


class TestFieldReader:
    """Validate field splitting and weaving."""

    def test_split_and_weave_roundtrip(self):
        """Splitting and re-weaving should produce the original frame."""
        frame = make_progressive_frame(seed=42)
        top, bot = FieldReader.split_fields(frame)

        assert top.shape[0] == frame.shape[0] // 2
        assert bot.shape[0] == frame.shape[0] // 2

        reconstructed = FieldReader.weave_fields(top, bot)
        np.testing.assert_array_equal(frame, reconstructed)

    def test_field_isolation(self):
        """Top field should contain even lines, bottom field odd lines."""
        frame = np.arange(480 * 720, dtype=np.uint8).reshape(480, 720)
        top, bot = FieldReader.split_fields(frame)

        np.testing.assert_array_equal(top, frame[0::2])
        np.testing.assert_array_equal(bot, frame[1::2])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""Telecine cadence detection and analysis.

Detects the 3:2 pulldown pattern that characterizes telecined content.
In standard NTSC telecine, film frames are distributed across video fields
in a repeating 5-field cycle: AA BB BC CD DD → producing 3 clean frames
and 2 combed frames per cycle.

The cadence detector looks for this periodic pattern in the comb score
signal using autocorrelation and peak detection.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np

from frameweaver.analysis.extractor import FrameMetrics


class CadenceType(Enum):
    """Detected telecine cadence types."""
    TELECINE_32 = "3:2 pulldown"      # Standard NTSC telecine
    TELECINE_22 = "2:2 pulldown"      # PAL telecine / field-doubled
    NONE = "no cadence"               # True interlace or progressive
    IRREGULAR = "irregular cadence"    # Broken or mixed cadence


@dataclass
class CadenceResult:
    """Result of cadence analysis on a window of frames."""
    cadence_type: CadenceType
    confidence: float          # 0.0 - 1.0
    period: int                # Detected period (5 for 3:2, 4 for 2:2, 0 for none)
    phase: int                 # Offset into the cadence cycle (0-4 for 3:2)
    clean_ratio: float         # Fraction of frames that are clean (not combed)
    combed_pattern: list[bool]  # Per-frame combing flags in the window


@dataclass
class CadenceBreak:
    """A detected break/shift in the telecine cadence."""
    frame_number: int
    break_type: str   # 'phase_shift', 'cadence_loss', 'scene_change'
    confidence: float


class CadenceDetector:
    """Detects telecine cadence patterns in frame metric sequences.

    Uses autocorrelation of the comb score signal to find periodic
    patterns, then validates against expected telecine characteristics.
    """

    # Thresholds
    COMB_BINARY_THRESHOLD = 10.0   # Comb score above this = "combed" frame
    CADENCE_MIN_CONFIDENCE = 0.6   # Minimum autocorrelation peak for detection
    MIN_WINDOW_SIZE = 15           # Minimum frames for cadence analysis
    CLEAN_RATIO_TELECINE = 0.55    # 3:2 telecine should have ~60% clean frames

    def analyze_window(
        self,
        metrics: list[FrameMetrics],
        comb_threshold: float | None = None,
    ) -> CadenceResult:
        """Analyze a window of frames for telecine cadence.

        Args:
            metrics: Sequence of per-frame metrics to analyze.
            comb_threshold: Override for comb score binary threshold.

        Returns:
            CadenceResult with detected cadence type and confidence.
        """
        if len(metrics) < self.MIN_WINDOW_SIZE:
            return CadenceResult(
                cadence_type=CadenceType.NONE,
                confidence=0.0,
                period=0,
                phase=0,
                clean_ratio=0.0,
                combed_pattern=[],
            )

        thresh = self.COMB_BINARY_THRESHOLD if comb_threshold is None else comb_threshold
        comb_scores = np.array([m.comb_score for m in metrics], dtype=np.float64)

        # Binary combing flags
        combed = comb_scores > thresh
        combed_pattern = combed.tolist()

        # Skip analysis if no motion (static content looks progressive)
        motion = np.array([m.motion_energy for m in metrics])
        motion_frames = np.sum(motion > 2.0)
        if motion_frames < len(metrics) * 0.2:
            # Mostly static — can't reliably detect cadence
            return CadenceResult(
                cadence_type=CadenceType.NONE,
                confidence=0.3,
                period=0,
                phase=0,
                clean_ratio=float(1.0 - np.mean(combed)),
                combed_pattern=combed_pattern,
            )

        # Autocorrelation of the comb score signal
        period_5_conf = self._autocorrelation_strength(comb_scores, period=5)
        period_4_conf = self._autocorrelation_strength(comb_scores, period=4)

        clean_ratio = float(1.0 - np.mean(combed))

        # Determine cadence type
        if period_5_conf > self.CADENCE_MIN_CONFIDENCE and period_5_conf > period_4_conf:
            # Validate: 3:2 telecine should have ~60% clean frames (3 of 5)
            if 0.35 < clean_ratio < 0.85:
                phase = self._detect_phase(combed, period=5)
                return CadenceResult(
                    cadence_type=CadenceType.TELECINE_32,
                    confidence=float(period_5_conf),
                    period=5,
                    phase=phase,
                    clean_ratio=clean_ratio,
                    combed_pattern=combed_pattern,
                )

        if period_4_conf > self.CADENCE_MIN_CONFIDENCE and period_4_conf > period_5_conf:
            phase = self._detect_phase(combed, period=4)
            return CadenceResult(
                cadence_type=CadenceType.TELECINE_22,
                confidence=float(period_4_conf),
                period=4,
                phase=phase,
                clean_ratio=clean_ratio,
                combed_pattern=combed_pattern,
            )

        # No clear cadence
        combed_ratio = float(np.mean(combed))
        if combed_ratio > 0.8:
            # Almost everything combed — true interlace, not telecine
            return CadenceResult(
                cadence_type=CadenceType.NONE,
                confidence=combed_ratio,
                period=0,
                phase=0,
                clean_ratio=clean_ratio,
                combed_pattern=combed_pattern,
            )

        return CadenceResult(
            cadence_type=CadenceType.IRREGULAR,
            confidence=max(period_5_conf, period_4_conf),
            period=0,
            phase=0,
            clean_ratio=clean_ratio,
            combed_pattern=combed_pattern,
        )

    def detect_breaks(
        self,
        metrics: list[FrameMetrics],
        window_size: int = 30,
        step: int = 5,
    ) -> list[CadenceBreak]:
        """Find points where the telecine cadence breaks or shifts.

        Cadence breaks occur at edit points, scene changes, and
        transitions between different content types. These are the
        primary source of IVTC failures and the main reason for
        human review.

        Args:
            metrics: Full video metric sequence.
            window_size: Analysis window size.
            step: Step between analysis windows.

        Returns:
            List of detected cadence breaks with frame numbers.
        """
        breaks: list[CadenceBreak] = []
        prev_result: CadenceResult | None = None

        for i in range(0, len(metrics) - window_size, step):
            window = metrics[i : i + window_size]
            result = self.analyze_window(window)

            if prev_result is not None:
                # Detect cadence type change
                if result.cadence_type != prev_result.cadence_type:
                    breaks.append(CadenceBreak(
                        frame_number=metrics[i].frame_number,
                        break_type="cadence_loss"
                            if result.cadence_type == CadenceType.NONE
                            else "cadence_change",
                        confidence=result.confidence,
                    ))

                # Detect phase shift within same cadence type
                elif (
                    result.cadence_type == CadenceType.TELECINE_32
                    and result.phase != prev_result.phase
                ):
                    breaks.append(CadenceBreak(
                        frame_number=metrics[i].frame_number,
                        break_type="phase_shift",
                        confidence=0.7,
                    ))

            prev_result = result

        # Also flag scene changes as potential breaks
        for m in metrics:
            if m.is_scene_change:
                breaks.append(CadenceBreak(
                    frame_number=m.frame_number,
                    break_type="scene_change",
                    confidence=0.5,
                ))

        # Deduplicate nearby breaks (within 10 frames)
        breaks.sort(key=lambda b: b.frame_number)
        deduped: list[CadenceBreak] = []
        for b in breaks:
            if not deduped or b.frame_number - deduped[-1].frame_number > 10:
                deduped.append(b)
            elif b.confidence > deduped[-1].confidence:
                deduped[-1] = b

        return deduped

    def _autocorrelation_strength(
        self,
        signal_data: np.ndarray,
        period: int,
    ) -> float:
        """Compute autocorrelation strength at a specific period.

        High autocorrelation at period=5 indicates 3:2 telecine cadence.
        High autocorrelation at period=4 indicates 2:2 telecine.

        Returns:
            Normalized correlation strength 0-1.
        """
        if len(signal_data) < period * 3:
            return 0.0

        # Normalize signal
        sig = signal_data - np.mean(signal_data)
        std = np.std(sig)
        if std < 1e-6:
            return 0.0  # Flat signal — no pattern
        sig = sig / std

        # Compute autocorrelation at the target period
        n = len(sig)
        shifted = sig[period:]
        original = sig[:n - period]

        correlation = float(np.mean(original * shifted))

        # Also check harmonics (2x period should also correlate)
        if len(sig) >= period * 6:
            shifted_2x = sig[period * 2:]
            original_2x = sig[:n - period * 2]
            corr_2x = float(np.mean(original_2x * shifted_2x))
            # Harmonic consistency boosts confidence
            correlation = (correlation * 0.7 + corr_2x * 0.3)

        return max(0.0, min(1.0, correlation))

    def _detect_phase(self, combed: np.ndarray, period: int) -> int:
        """Determine the phase offset of the telecine cadence.

        For 3:2 pulldown with period 5, there are 5 possible phases
        (which of the 5 positions in the cycle is the first combed frame).

        Returns:
            Phase offset (0 to period-1).
        """
        best_phase = 0
        best_score = -1.0

        for phase in range(period):
            # Create expected pattern for this phase
            # For 3:2: positions 3 and 4 in the cycle are combed
            if period == 5:
                expected = np.zeros(period, dtype=np.float64)
                expected[(3 + phase) % 5] = 1.0
                expected[(4 + phase) % 5] = 1.0
            elif period == 4:
                expected = np.zeros(period, dtype=np.float64)
                expected[(1 + phase) % 4] = 1.0
                expected[(3 + phase) % 4] = 1.0
            else:
                continue

            # Tile expected pattern to match signal length
            tiled = np.tile(expected, (len(combed) // period) + 1)[:len(combed)]

            # Correlation with actual combing pattern
            score = float(np.corrcoef(combed.astype(np.float64), tiled)[0, 1])
            if not np.isnan(score) and score > best_score:
                best_score = score
                best_phase = phase

        return best_phase

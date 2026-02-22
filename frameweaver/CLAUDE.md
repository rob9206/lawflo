# CLAUDE.md — Frameweaver Project Context

## What is this project?

Frameweaver is a desktop application that uses AI-powered video analysis to automatically detect, classify, and process telecined (3:2 pulldown), interlaced, and progressive video content from DVD and Blu-ray disc rips. It flags uncertain segments for human review via a PyQt6 GUI.

**Product name:** Frameweaver
**Owner:** Robbie @ Thunderhorse Tuning (Utica, NY)
**License:** Proprietary

## Project Structure

```
frameweaver/
├── frameweaver/                 # Main package
│   ├── __init__.py              # Version: 0.1.0
│   ├── cli.py                   # CLI entry point (frameweaver analyze / info)
│   ├── analysis/                # Phase 1 — COMPLETE
│   │   ├── extractor.py         # Frame-level metric extraction (comb score, field/frame similarity, motion, scene change)
│   │   ├── cadence.py           # Telecine cadence detection (autocorrelation, phase detection, break detection)
│   │   └── classifier.py        # Segment classification (telecine/interlace/progressive/hybrid/unknown)
│   ├── processing/              # Phase 2 — NOT STARTED
│   │   └── __init__.py          # Will contain: VapourSynth IVTC, FFmpeg fallback, encoding presets
│   ├── ui/                      # Phase 3 — NOT STARTED
│   │   └── __init__.py          # Will contain: PyQt6 review UI (timeline, frame preview, flag list)
│   ├── training/                # Phase 4 — NOT STARTED
│   │   └── __init__.py          # Will contain: synthetic data gen, label collection, XGBoost/CNN training
│   └── utils/
│       └── ffmpeg.py            # FFmpeg subprocess wrapper (probe, frame reader, field reader)
├── tests/
│   └── test_analysis.py         # 21 tests — ALL PASSING
├── pyproject.toml               # Project config, dependencies, CLI entry point
└── README.md
```

## Current State

**Phase 1 (Detection Engine) is COMPLETE.** ~2,000 lines, 21/21 tests passing.

### What works:
- `frameweaver info <video>` — probes video metadata via ffprobe
- `frameweaver analyze <video>` — full analysis pipeline: extract frame metrics → detect cadence → classify segments → output JSON
- `frameweaver analyze <video> --sample` — quick sampling mode
- Comb score computation (cross-field vs same-field line energy)
- Field similarity detection (repeated field identification for telecine)
- Telecine cadence detection via autocorrelation at period 5 (3:2) and period 4 (2:2)
- Cadence phase detection and cadence break detection
- Segment classification with sliding windows, hysteresis smoothing, and confidence scoring
- JSON serialization/deserialization of classification results
- Color-coded terminal output with progress bar

### What needs real-world testing:
- The thresholds (COMB_THRESHOLD=10.0, SCENE_CHANGE_THRESHOLD=40.0, etc.) were set based on synthetic frame tests. They need tuning against actual DVD rips (.vob files from MakeMKV). The unit tests use constructed combed frames and validate the math is correct, but real MPEG-2 content will have different noise characteristics.
- FFmpeg's telecine filter on synthetic sources produces subtle combing. Real disc rips with sharp motion edges will produce much stronger comb signals.

## Tech Stack

- **Python 3.11+** (developed on 3.12)
- **NumPy** — all frame math (comb scores, similarity, motion energy)
- **SciPy** — signal processing (imported in cadence.py but autocorrelation is manual)
- **OpenCV** — listed as dependency but not yet used (available for future SSIM, etc.)
- **tqdm** — listed as dependency for progress bars (CLI uses custom progress callback)
- **FFmpeg** — frame decoding via subprocess pipe (luma-only gray output for speed)
- **pytest** — test framework

## Architecture Decisions

### Frame reading strategy
We stream raw luma (gray8) frames from FFmpeg via stdout pipe. Only the Y plane is needed for comb/motion detection — no chroma decode overhead. This achieves 57+ fps on 480i in testing.

### Comb score algorithm
Cross-field energy minus same-field energy: `max(|line[n] - line[n+1]| - |line[n] - line[n+2]|, 0)`. This specifically detects the alternating-line discontinuity pattern of interlaced combing, not just general edge energy.

### Cadence detection
Autocorrelation of the comb score signal at period 5. Also checks harmonics (period 10) for confidence boosting. Phase detection uses template correlation against expected combed-frame positions in the cycle.

### Classification pipeline
Sliding window (50 frames, step 10) → per-window classify → merge adjacent same-type windows → hysteresis (absorb segments < 30 frames into neighbors) → compute stats → flag low-confidence for review.

### No ML yet (intentional)
Phase 1 is entirely rule-based. The metrics extracted ARE the features that Phase 4's ML model will train on. The rule-based classifier gets ~88% accuracy on synthetic data. XGBoost on the same features should reach ~95%, CNN on raw frame patches ~97%.

## Development Phases

### Phase 2 — Processing Pipeline (NEXT)
Build the actual IVTC/deinterlace processing using VapourSynth (primary) and FFmpeg (fallback).

Files to create:
- `frameweaver/processing/manager.py` — Filter chain orchestration per segment type
- `frameweaver/processing/vapoursynth_proc.py` — VapourSynth VIVTC + QTGMC chains
- `frameweaver/processing/ffmpeg_proc.py` — FFmpeg fieldmatch+yadif+decimate fallback
- `frameweaver/processing/encoder.py` — Output encoding (x264/x265/FFV1 with presets)
- `frameweaver/processing/timecodes.py` — VFR timecode generation for hybrid content

Key integration points:
- `Segment` objects from `classifier.py` drive filter chain selection
- VapourSynth's Python API (`import vapoursynth as vs`) for filter access
- FFmpeg subprocess for encoding
- Must handle VFR output (telecine segments at 23.976fps, interlaced at 29.97fps)

### Phase 3 — Review UI
PyQt6 desktop app with segment timeline, side-by-side frame preview, flagged segment list, and override controls. Robbie has extensive PyQt6 experience from DynoAI.

### Phase 4 — ML Model
Train XGBoost on extracted features, then CNN on raw frame patches. Synthetic training data generator creates labeled telecine/interlace/progressive sequences programmatically.

### Phase 5 — Polish & Ship
Batch processing, library scanning, encoding presets, installer packaging (PyInstaller + Inno Setup for Windows).

## Key Domain Concepts

- **Telecine (3:2 pulldown):** Film at 23.976fps converted to 29.97i by repeating fields in a 3:2 pattern. Creates 3 clean + 2 combed frames per 5-frame cycle. IVTC reverses this losslessly.
- **True interlace:** Video captured at 29.97i where every field is from a different time. Every motion frame is combed. Needs deinterlacing (lossy).
- **Soft telecine:** Disc stores 23.976p with RFF flags. FFmpeg ignores these by default, so output is already progressive. No processing needed.
- **Hard telecine:** 3:2 pulldown baked into the encoded bitstream. Requires IVTC processing.
- **TIVTC/VIVTC:** Gold standard IVTC filters for AviSynth/VapourSynth. TFM does field matching, TDecimate removes duplicates.
- **QTGMC:** Premier deinterlacing algorithm. Used as fallback for frames that can't be cleanly field-matched.
- **DGIndex:** Creates .d2v index files from MPEG-2 with pulldown flag data. Dramatically improves TFM accuracy.
- **Field order:** TFF (top field first) is standard for DVD MPEG-2. BFF is common for DV. Getting this wrong breaks everything.

## Running Tests

```bash
cd frameweaver
pip install -e ".[dev]"
pytest tests/ -v
```

All 21 tests should pass. Tests use synthetic frames (no video files needed).

## Running the CLI

```bash
# Requires FFmpeg in PATH
frameweaver info some_video.vob
frameweaver analyze some_video.mkv -v -o analysis.json
```

## Business Context

Frameweaver is intended as a commercial product targeting physical media collectors, anime archivists, and boutique restoration studios. Pricing model: Free tier (analysis only), $69 Standard, $149 Pro, $299/year Studio. Key positioning: "the missing preprocessing step before Topaz Video AI" — Topaz has no native IVTC and their community has been requesting it since 2023.

Full product plan is in `detelecine-plan.md` (separate from the codebase).

## Code Style

- Type hints on all public functions
- Dataclasses for data structures
- Docstrings on all classes and public methods
- No external dependencies beyond numpy/scipy/opencv for core analysis
- FFmpeg interaction via subprocess only (no python-ffmpeg wrappers)
- Tests use synthetic frame generation, not video file fixtures

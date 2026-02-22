# Frameweaver

**Intelligent video detelecine and deinterlace detection.**

Frameweaver scans DVD and Blu-ray rips, automatically classifies content as telecined (3:2 pulldown), interlaced, or progressive, and flags uncertain segments for human review. It's the missing preprocessing step before tools like Topaz Video AI.

## Quick Start

```bash
# Install
pip install -e .

# Probe a video file
frameweaver info input.vob

# Full analysis — outputs a segment map with classifications
frameweaver analyze input.mkv

# Quick sample analysis (faster, less thorough)
frameweaver analyze input.mkv --sample

# Analyze first 1000 frames only
frameweaver analyze input.mkv --max-frames 1000

# Verbose output with per-segment details
frameweaver analyze input.mkv -v
```

## What It Detects

| Content Type | Pattern | Action Needed |
|---|---|---|
| **Telecine (3:2)** | Repeating 5-frame cycle: 3 clean + 2 combed | Inverse telecine (IVTC) → 23.976fps |
| **True Interlace** | Every motion frame combed, no pattern | Deinterlace (QTGMC/bwdif) |
| **Progressive** | No combing artifacts | No processing needed |
| **Hybrid** | Mixed telecine + interlace segments | Per-segment processing |
| **Unknown** | Low confidence — needs human eyes | Flagged for review |

## Output

The `analyze` command produces a JSON segment map:

```json
{
  "total_frames": 142891,
  "total_segments": 5,
  "needs_review": 2,
  "review_percentage": 3.4,
  "summary": {
    "dominant_type": "telecine",
    "type_percentages": {
      "telecine": 91.2,
      "interlaced": 5.4,
      "unknown": 3.4
    },
    "recommendation": "IVTC with hybrid fallback"
  },
  "segments": [...]
}
```

## Project Structure

```
frameweaver/
├── analysis/
│   ├── extractor.py     # Frame-level metric extraction
│   ├── cadence.py       # Telecine cadence detection
│   └── classifier.py    # Segment classification engine
├── processing/          # (Phase 2) Filter chain orchestration
├── ui/                  # (Phase 3) PyQt6 review interface
├── training/            # (Phase 4) ML model training
├── utils/
│   └── ffmpeg.py        # FFmpeg/ffprobe wrapper
└── cli.py               # Command-line interface
```

## Requirements

- Python 3.11+
- FFmpeg (in PATH)
- NumPy, SciPy, OpenCV, tqdm

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## License

Proprietary — Thunderhorse Tuning

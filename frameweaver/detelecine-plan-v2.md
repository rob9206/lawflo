# Frameweaver — Revised Product & Technical Plan v2

## What Changed From v1

The original plan had the right pieces but the wrong order. Key changes:

1. **Swapped Phase 2 and 3** — UI comes before processing pipeline. The analysis + review UI IS the free tier product and the demand validator. Don't build VapourSynth integration until you know people want this.
2. **Added Phase 1.5 — Real-World Calibration** — The most critical step was missing entirely. You need 2 weeks of testing against actual DVD/BD rips to tune thresholds before anything else.
3. **Deferred ML to post-launch** — Rule-based classifier with tuned thresholds is sufficient for v1.0. ML requires real user data you won't have until after launch.
4. **Split processing into FFmpeg-first (easy) and VapourSynth (hard/optional)** — Ship with FFmpeg processing, add VapourSynth as a premium quality option later.
5. **Added soft telecine detection** — Quick win that prevents unnecessary processing.
6. **Added audio sync handling** — Critical gap in v1 plan.
7. **Windows-only for v1** — Don't waste time on cross-platform packaging until demand is proven.
8. **Restructured free tier** — Sample analysis free, full analysis + review UI is paid.

---

## Revised Phase Order

```
Phase 1:    Detection Engine                    ✅ COMPLETE (2,002 lines, 21 tests)
Phase 1.5:  Real-World Calibration              2 weeks — CRITICAL, DO THIS NEXT
Phase 2:    Review UI (PyQt6)                   3 weeks — This IS the product
Phase 3:    FFmpeg Processing Pipeline          2 weeks — Simple, no dependency hell
Phase 4:    Beta Release + Feedback Loop        2 weeks — Ship to VideoHelp/Doom9
Phase 5:    VapourSynth Premium Processing      3 weeks — Only if demand validates
Phase 6:    Polish, Packaging, Launch           2 weeks — Windows installer, licensing
--- POST-LAUNCH ---
Phase 7:    ML Model Training                   When you have 500+ user sessions
Phase 8:    Batch Processing                    Based on user demand
Phase 9:    macOS/Linux Ports                   Based on user demand
```

**Total to beta: ~9 weeks (not 18)**
**Total to v1.0 paid launch: ~14 weeks**

The original plan was 18 weeks to beta. This gets you to beta in 9 by cutting premature optimization (ML, VapourSynth bundling, cross-platform) and focusing on the novel value: detection + review UI.

---

## Phase 1.5 — Real-World Calibration (Weeks 1–2)

**This is the most important phase and it was missing from v1.**

The current thresholds were tuned against synthetic frames. Real DVD content will be different. You need to build a calibration dataset and iteratively tune.

### 1.5.1 Build a Test Library

Collect 20+ real disc rips covering the problem space:

| Source Type | Examples | Why |
|---|---|---|
| Clean film DVD (telecine) | Any well-authored Hollywood DVD | Baseline — should detect perfectly |
| Anime DVD (telecine) | Any anime DVD with hard telecine | Different combing characteristics (flat colors, sharp edges) |
| TV show DVD (hybrid) | Seinfeld, Friends, X-Files | Mixed telecine film + interlaced video segments |
| Live action interlace | Sports DVD, concert DVD | True interlace baseline |
| Soft telecine DVD | Most newer Hollywood DVDs | Should detect as progressive (no processing needed) |
| 1080i Blu-ray | TV show BD, anime BD | Higher resolution interlace |
| 1080p Blu-ray | Any film BD | Progressive baseline — should pass through |
| Bad authoring | Cheap/bootleg DVDs | Broken cadences, wrong field order |
| PAL DVD | Any Region 2 disc | Different frame rate (25fps), 2:2 pulldown or speed-up |

### 1.5.2 Calibration Process

```bash
# For each test file:
frameweaver analyze test_file.vob -v -o test_file_analysis.json

# Log results in a spreadsheet:
# File | Expected Type | Detected Type | Confidence | Comb Threshold Needed | Notes
```

Iterate on these thresholds in `extractor.py` and `classifier.py`:

| Threshold | Current | What to Watch |
|---|---|---|
| `COMB_THRESHOLD` | 10.0 | Too low = false positives on noisy progressive. Too high = misses subtle telecine combing. |
| `SCENE_CHANGE_THRESHOLD` | 40.0 | Test against actual scene changes vs. just high-motion scenes |
| `CADENCE_MIN_CONFIDENCE` | 0.6 | Does autocorrelation work on real cadences with noise? |
| `INTERLACE_COMBED_RATIO` | 0.75 | Real interlaced content may have static scenes that lower the ratio |
| `PROGRESSIVE_MAX_COMB` | 5.0 | Noisy DVDs may have non-zero comb scores even when progressive |
| `MIN_SEGMENT_FRAMES` | 30 | Real cadence breaks may be shorter — are we merging real transitions? |

### 1.5.3 Add Soft Telecine Detection

Add a new segment type and detect it via container metadata before frame analysis:

```python
class SegmentType(Enum):
    TELECINE = "telecine"
    SOFT_TELECINE = "soft_telecine"   # NEW — no processing needed
    INTERLACED = "interlaced"
    PROGRESSIVE = "progressive"
    HYBRID = "hybrid"
    UNKNOWN = "unknown"
```

Detection: check ffprobe output for `codec_tag_string`, `field_order`, and the `r_frame_rate` vs `avg_frame_rate` discrepancy that indicates RFF flags. If ffprobe reports 23.976 original frame rate within a 29.97fps interlaced stream, it's likely soft telecine.

### 1.5.4 Add DGIndex Integration (DVD only)

DGIndex provides frame-accurate pulldown flag data that dramatically improves detection. For MPEG-2 sources:

```python
# utils/dgindex.py
class DGIndexWrapper:
    """Run DGIndex to create .d2v index with pulldown flags."""

    def create_index(self, vob_path: str) -> D2VResult:
        """Returns d2v path and film percentage."""
        # dgindex -i input.vob -o output -exit
        # Parse output for Film%
        pass

    def get_film_percentage(self, d2v_path: str) -> float:
        """Read Film% from d2v project file."""
        # >95% film = Force Film mode (instant progressive output)
        # 80-95% film = IVTC with hybrid handling
        # <80% film = complex hybrid, needs full analysis
        pass
```

This is a quick add that immediately improves accuracy for DVD content. DGIndex's film percentage alone can classify many sources without frame analysis.

### Phase 1.5 Deliverable

- Tuned thresholds validated against 20+ real sources
- Soft telecine detection
- DGIndex integration for MPEG-2 film percentage
- Accuracy report: % correct classification across test library
- **Target: ≥90% correct classification on test library before proceeding**

---

## Phase 2 — Review UI (Weeks 3–5)

**This comes BEFORE processing because the UI IS the product.**

The free tier ships analysis + visualization. Users see their segment maps, understand their content, and share screenshots. This validates demand before you invest in the processing pipeline.

### 2.1 Simplified MVP UI

Cut scope from v1 plan. Ship the minimum UI that's useful:

```
┌─────────────────────────────────────────────────────┐
│  Frameweaver v0.1                        [_][□][X]  │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌───────────────────────────────────────────────┐  │
│  │           FRAME PREVIEW (single)              │  │
│  │     [original frame with comb overlay]        │  │
│  └───────────────────────────────────────────────┘  │
│  Frame: 14,523 / 142,891    Comb: 2.1               │
│  Type: TELECINE (97.2%)     Cadence: ●●●○○          │
│                                                     │
│  [◄◄] [◄] [▶] [►] [►►]   [← Prev Flag] [Next →]   │
│                                                     │
├─────────────────────────────────────────────────────┤
│  SEGMENT TIMELINE (color-coded bar)                 │
│  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░▓▓▓▓▓▓▓▓▓▓▓▓████▓▓▓▓▓▓▓▓  │
├─────────────────────────────────────────────────────┤
│  METRICS GRAPH (comb score + motion over time)      │
│  ╱╲╱╲╱╲╱╲╱╲___╱╲╱╲╱╲╱╲╱╲╱╲▁▁▁▁╱╲╱╲╱╲╱╲╱╲╱╲╱╲   │
├─────────────────────────────────────────────────────┤
│  FLAGGED SEGMENTS          │ SUMMARY               │
│  ⚠ 01:23:45 UNKNOWN  34%  │ Telecine: 91.2%       │
│  ⚠ 01:45:12 HYBRID   61%  │ Interlace: 5.4%       │
│  ⚠ 02:01:33 UNKNOWN  28%  │ Unknown: 3.4%         │
│                            │ Recommendation:        │
│  Override: [T] [I] [P] [S] │ IVTC + hybrid fallback│
├─────────────────────────────────────────────────────┤
│  [Open File] [Re-Analyze]  [Export JSON] [Process →]│
└─────────────────────────────────────────────────────┘
```

### What's CUT from v1 plan (add later):

- ❌ Side-by-side processed preview (requires processing pipeline)
- ❌ Draggable segment boundaries (nice-to-have, not MVP)
- ❌ Batch processing dialog
- ❌ Settings/preferences panel (hardcode sensible defaults)

### What's IN the MVP:

- ✅ Single frame preview with comb score heatmap overlay
- ✅ Frame-by-frame stepping (arrow keys)
- ✅ Color-coded segment timeline (click to jump)
- ✅ Metrics graph (comb score + motion energy over time, synced with timeline)
- ✅ Flagged segment list with override buttons
- ✅ Summary panel with recommendation
- ✅ Export analysis JSON
- ✅ Drag-and-drop file open

### 2.2 Key Implementation Notes

**Frame preview rendering:** Decode individual frames via FFmpeg on demand (not preloaded). Cache ~50 frames around current position for smooth stepping. Render comb overlay by computing per-pixel comb energy and painting red over regions above threshold.

**Timeline widget:** Custom QWidget with paintEvent. Each segment is a colored rectangle proportional to frame count. Click position maps to frame number. Current frame shown as vertical line cursor.

**Metrics graph:** pyqtgraph for the comb score / motion energy traces. Shared x-axis with timeline. Click to seek. This is the most visually compelling part of the UI for screenshots.

**Threading:** Analysis runs in QThread with progress signal. UI stays responsive. Cancel button kills the analysis thread.

### Phase 2 Deliverable

Desktop app (Windows) that opens a video, runs analysis, and shows an interactive segment map with review capabilities. No processing yet — "Process" button is grayed out with tooltip "Coming in v0.2".

**This is your free tier product and your beta launch vehicle.**

---

## Phase 3 — FFmpeg Processing Pipeline (Weeks 6–7)

**FFmpeg only. No VapourSynth yet.** This covers ~80% of use cases with zero bundling complexity.

### 3.1 Why FFmpeg First

| | FFmpeg | VapourSynth |
|---|---|---|
| Bundling | Already required for analysis | Requires VS runtime + 6 plugins + Python bindings |
| Install size | ~80MB (already present) | +200MB minimum |
| IVTC quality | Good (fieldmatch + yadif + decimate) | Best (VIVTC + QTGMC fallback) |
| Handles clean telecine | ✅ Very well | ✅ Perfectly |
| Handles hybrid content | ⚠️ Decent | ✅ Excellent (two-pass VFR) |
| User effort | Zero | Zero |

For cleanly telecined DVDs (the majority of use cases), FFmpeg's IVTC is nearly as good as VIVTC. The quality gap only matters for difficult hybrid content — which is exactly the stuff flagged for review anyway.

### 3.2 Processing Architecture

```python
class FFmpegProcessor:
    """Segment-aware video processing using FFmpeg."""

    def process_video(self, input_path: str, output_path: str,
                      segments: list[Segment]) -> None:
        """Process entire video based on segment classification."""

        if self._is_uniform(segments):
            # Easy case: entire video is one type
            self._process_uniform(input_path, output_path, segments[0].segment_type)
        else:
            # Hard case: segment-by-segment processing
            self._process_segmented(input_path, output_path, segments)

    def _is_uniform(self, segments: list[Segment]) -> bool:
        """Check if all segments are the same type."""
        types = set(s.segment_type for s in segments)
        return len(types) == 1

    def _process_uniform(self, input_path, output_path, seg_type):
        """Single FFmpeg pass for uniform content."""
        if seg_type == SegmentType.TELECINE:
            # fieldmatch + yadif safety + decimate → 23.976fps
            vf = "fieldmatch=order=tff:combmatch=full,yadif=deint=interlaced,decimate"
        elif seg_type == SegmentType.INTERLACED:
            # bwdif deinterlace → 29.97fps progressive
            vf = "bwdif=mode=send_frame:parity=tff"
        elif seg_type == SegmentType.SOFT_TELECINE:
            # No video filter needed — just ensure progressive output
            vf = None
        else:
            # Progressive — copy
            vf = None

        self._run_ffmpeg(input_path, output_path, vf)

    def _process_segmented(self, input_path, output_path, segments):
        """Process segments individually, then concatenate.

        CRITICAL: This is where audio sync gets tricky.
        Strategy: process video segments to intermediate files,
        then use ffmpeg concat demuxer with the original audio.
        """
        temp_files = []
        for i, seg in enumerate(segments):
            temp_out = f"/tmp/frameweaver_seg_{i:04d}.mkv"
            self._process_segment(input_path, temp_out, seg)
            temp_files.append(temp_out)

        # Concatenate video segments
        self._concat_segments(temp_files, output_path, input_path)
        # Clean up
        for f in temp_files:
            os.unlink(f)

    def _process_segment(self, input_path, output_path, segment):
        """Process a single segment with trim + filter."""
        start_time = segment.start_frame / 29.97
        duration = segment.frame_count / 29.97
        # ... build ffmpeg command with -ss and -t
```

### 3.3 Audio Sync Strategy

**This was completely missing from v1 and it's critical.**

When telecine segments get IVTC'd from 29.97fps to 23.976fps, the video duration doesn't change (fewer frames at a slower rate = same duration), so audio stays in sync IF you handle it correctly.

The rules:
1. **Uniform telecine → 23.976fps:** Audio stays synced. No adjustment needed. This is the common case.
2. **Uniform interlace → 29.97fps progressive:** Audio stays synced. Frame rate doesn't change.
3. **Segmented processing (VFR):** Use MKV container with timecodes file. Audio stays constant rate. Video has variable frame timestamps. mkvmerge handles this natively.
4. **NEVER re-encode audio.** Always stream copy (`-c:a copy`). Re-encoding introduces drift.

```python
def _concat_with_audio(self, video_segments: list[str],
                        original_input: str, output: str):
    """Concatenate processed video segments with original audio."""
    # Step 1: Concat video segments (no audio)
    concat_list = self._write_concat_list(video_segments)
    temp_video = "/tmp/frameweaver_video_only.mkv"
    subprocess.run([
        "ffmpeg", "-f", "concat", "-safe", "0",
        "-i", concat_list,
        "-c:v", "copy", "-an",  # Video only, no audio
        temp_video
    ])

    # Step 2: Mux with original audio
    subprocess.run([
        "mkvmerge", "-o", output,
        temp_video,                    # Processed video
        "-D", original_input,          # Audio + subs from original (no video)
    ])
```

### 3.4 Encoding Presets

| Preset | Codec | Settings | Use Case |
|---|---|---|---|
| Lossless | FFV1 | `-c:v ffv1 -level 3 -slicecrc 1` | Archive / Topaz input |
| High Quality | x265 | `-c:v libx265 -crf 18 -preset slow` | Direct playback, small files |
| Compatible | x264 | `-c:v libx264 -crf 18 -preset slow -tune film` | Maximum compatibility |
| Fast Preview | x264 | `-c:v libx264 -crf 28 -preset veryfast` | Quick test encode |

### Phase 3 Deliverable

"Process" button in the UI now works. Users can analyze → review → process → get a clean progressive MKV. FFmpeg-only, no additional dependencies.

---

## Phase 4 — Beta Release (Weeks 8–9)

### 4.1 Where to Launch

| Community | Platform | Why |
|---|---|---|
| VideoHelp Forum | forum.videohelp.com | #1 disc ripping community, expert users, quality feedback |
| Doom9 Forum | forum.doom9.org | AviSynth/VapourSynth power users, will stress-test everything |
| r/DataHoarder | Reddit | Large audience (700K+), media archivists |
| r/anime | Reddit | Anime ripping community, telecine is their #1 pain point |
| MakeMKV Forum | makemkv.com/forum | Natural pipeline: MakeMKV → Frameweaver → Topaz |
| Topaz Community | community.topazlabs.com | Users frustrated by lack of IVTC, warm leads for paid tier |

### 4.2 Beta Strategy

- Free tier only during beta (full analysis + review UI, FFmpeg processing)
- Collect: classification accuracy reports, false positive/negative rates, crash logs
- In-app feedback button: "Was this classification correct? [Yes] [No → correct to: ___]"
- This feedback IS your ML training data for Phase 7

### 4.3 Success Metrics for Beta

| Metric | Target | Why |
|---|---|---|
| Downloads | 200+ in first month | Validates interest |
| Correct classification rate | ≥85% user-reported | Validates detection engine |
| Review rate | <10% of segments flagged | Too many flags = tool isn't useful |
| Forum thread engagement | 50+ replies | Community finds it worth discussing |
| Bug reports | <20 blockers | Stability baseline |

### Phase 4 Deliverable

Beta installed by 200+ users with feedback flowing in. Classification accuracy validated on real-world content. Clear signal on whether to proceed to paid launch.

---

## Phase 5 — VapourSynth Premium Processing (Weeks 10–12)

**Only build this if beta validates demand.** This is the premium quality tier.

### 5.1 VapourSynth Integration

Same architecture as v1 plan but with key additions:

```python
class VapourSynthProcessor:
    """Premium processing using VapourSynth filters."""

    def ivtc(self, clip, d2v_path=None, field_order=1):
        """IVTC with optional DGIndex awareness."""
        if d2v_path:
            # D2V-aware field matching — highest accuracy
            matched = self.core.vivtc.VFM(clip, order=field_order, mode=1,
                                           d2v=d2v_path)  # Pulldown flag data
        else:
            matched = self.core.vivtc.VFM(clip, order=field_order, mode=1)

        # QTGMC fallback for residual combed frames
        deinterlaced = haf.QTGMC(matched, Preset="Fast",
                                  TFF=(field_order == 1))

        # Conditional application
        processed = self.core.std.FrameEval(
            matched, partial(self._select_combed,
                           clip=matched, deint=deinterlaced),
            prop_src=matched
        )
        return self.core.vivtc.VDecimate(processed)

    def ivtc_hybrid_vfr(self, clip, segments, d2v_path=None):
        """Two-pass VFR IVTC for complex hybrid content.

        This is the killer feature that justifies the Pro tier.
        Outputs variable framerate: film at 23.976, video at 29.97.
        """
        # Pass 1: Analyze entire video
        # VFM with output= writes match decisions
        # VDecimate mode=4 writes metrics

        # Pass 2: Process with global optimization
        # VDecimate mode=5 with hybrid=2 for VFR output
        # Generates timecodes file for MKV muxing
        pass
```

### 5.2 Bundling Strategy (Windows Only)

```
frameweaver/
├── frameweaver.exe              # PyInstaller bundle
├── ffmpeg/
│   ├── ffmpeg.exe
│   └── ffprobe.exe
├── vapoursynth/                 # VS Portable
│   ├── vapoursynth64/
│   │   ├── vapsynth.dll
│   │   ├── vsscript.dll
│   │   └── plugins64/
│   │       ├── vivtc.dll
│   │       ├── nnedi3.dll
│   │       ├── bwdif.dll
│   │       └── lsmashsource.dll
│   └── python_embed/            # Embedded Python for VS
├── dgindex/
│   └── DGIndex.exe
└── mkvtoolnix/
    └── mkvmerge.exe
```

Total bundle size: ~350MB. Acceptable for a video processing tool.

**Key risk:** VapourSynth plugin version compatibility. Pin exact versions. Test the bundle on clean Windows installs (VM).

### Phase 5 Deliverable

Pro tier processing: VapourSynth IVTC with QTGMC fallback, two-pass VFR for hybrid content, D2V-aware field matching. Measurably better output than FFmpeg on difficult sources.

---

## Phase 6 — Launch (Weeks 13–14)

### 6.1 Packaging

- **Inno Setup** installer for Windows
- License key system (simple: hash of email + purchase ID, validated locally)
- Auto-update check on launch (compare version against hosted JSON)

### 6.2 Revised Pricing

| Tier | Price | Features |
|---|---|---|
| **Free** | $0 | Sample analysis (5 points), CLI only, JSON export. Enough to see what the tool does. |
| **Standard** | $79 one-time | Full analysis, review UI, FFmpeg processing, all encoding presets |
| **Pro** | $129 one-time | Everything in Standard + VapourSynth processing, D2V integration, two-pass VFR, batch processing |

Changes from v1:
- Dropped Studio tier (premature, adds support burden)
- Free tier is sample-only (not full analysis) — full analysis is the main value
- Tightened the price gap ($79/$129 vs $69/$149) — less decision friction
- One-time only, no subscriptions — this community hates subscriptions (see Topaz backlash)

### 6.3 Realistic Revenue (Year 1)

| Scenario | Free Users | Paid Conversions | Avg Price | Revenue |
|---|---|---|---|---|
| Conservative | 1,000 | 150 (15%) | $95 | $14,250 |
| Moderate | 3,000 | 450 (15%) | $95 | $42,750 |
| Strong | 5,000 | 750 (15%) | $95 | $71,250 |

These are more honest numbers than v1. A niche desktop tool with organic marketing will realistically convert 10-20% of free users. The revenue isn't life-changing, but with zero ongoing costs it's pure profit and validates a market position you can grow from.

---

## Post-Launch Phases

### Phase 7 — ML Model (When you have 500+ user sessions)

Only now do you have enough real-world labeled data to train meaningfully.

**Simplified approach (cut the CNN):**
- XGBoost on extracted feature vectors is sufficient
- The features you already extract (comb score stats, cadence strength, motion energy, field similarity) ARE the optimal features
- A CNN on raw pixels adds massive complexity for marginal accuracy gain
- Train on: synthetic data (bulk) + user corrections from beta feedback (quality)
- Ship as a model file update, not a code update

### Phase 8 — Batch Processing (Based on demand)

Only build if users ask for it. Many users process one disc at a time.

### Phase 9 — macOS/Linux (Based on demand)

If >10% of beta users ask for it. Otherwise, don't invest.

---

## Risks Reassessed

| Risk | Likelihood | Impact | Mitigation | Change from v1 |
|---|---|---|---|---|
| Market too small | Medium | High | Free tier validates before heavy investment | Same |
| Detection accuracy on real content | **HIGH** | **HIGH** | **Phase 1.5 calibration is now mandatory** | **NEW — was unaddressed** |
| VapourSynth bundling | High | Medium | Deferred to Phase 5, FFmpeg-first | Moved later |
| Audio sync issues | Medium | High | Dedicated handling in Phase 3 | **NEW — was missing** |
| Topaz adds native IVTC | Low | Medium | Review UI + detection are unique | Lowered impact |
| Competition from Hybrid | Medium | Medium | Position on AI detection, not filter execution | **NEW — was unaddressed** |
| Users won't pay for processing | Medium | Medium | Free tier limited to sample, review UI is paid | Restructured tiers |
| Scope creep | High | Medium | Strict phase gates, don't start next phase until current delivers | Same |

---

## Critical Path

The shortest path to revenue:

```
NOW:        Run frameweaver against 5 real DVD rips. See what breaks.
Week 1-2:   Tune thresholds until ≥90% accuracy on test library
Week 3-5:   Build PyQt6 review UI (you know this stack cold from DynoAI)
Week 6-7:   FFmpeg processing pipeline + audio sync
Week 8-9:   Beta on VideoHelp + Doom9
Week 10:    If beta validates → implement licensing, build installer
Week 11:    Launch Standard tier ($79)
Week 12-14: VapourSynth integration for Pro tier ($129)
```

**First dollar: ~Week 11 (~2.5 months from now)**

The v1 plan had first dollar at Week 18+ (4.5 months). This plan cuts time-to-revenue nearly in half by shipping the novel value (detection + review) early and deferring commodity features (VapourSynth, ML, batch, cross-platform) until demand is proven.

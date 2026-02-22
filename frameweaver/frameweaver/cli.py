"""Frameweaver — Command-line interface.

Usage:
    frameweaver analyze <input> [--output <json>] [--sample] [--verbose]
    frameweaver info <input>
    frameweaver --version
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from frameweaver import __version__
from frameweaver.utils.ffmpeg import probe_video
from frameweaver.analysis.extractor import FrameMetricExtractor
from frameweaver.analysis.classifier import SegmentClassifier


def cmd_info(args: argparse.Namespace) -> int:
    """Show video stream information."""
    try:
        info = probe_video(args.input)
    except Exception as e:
        print(f"Error probing video: {e}", file=sys.stderr)
        return 1

    print(f"File:         {args.input}")
    print(f"Resolution:   {info.width}x{info.height}")
    print(f"Frame rate:   {info.fps:.3f} fps ({info.fps_num}/{info.fps_den})")
    print(f"Total frames: {info.total_frames}")
    print(f"Duration:     {info.duration_seconds:.1f}s")
    print(f"Codec:        {info.codec}")
    print(f"Pixel format: {info.pix_fmt}")
    print(f"Field order:  {info.field_order}")
    print(f"Scan type:    {info.scan_type}")
    print()

    if info.is_likely_telecined:
        print("⚡ Heuristic: 29.97fps interlaced MPEG-2 — likely telecined film content")
    elif info.scan_type == "interlaced":
        print("⚠  Interlaced content detected — run 'frameweaver analyze' to classify")
    elif info.scan_type == "progressive":
        print("✓  Progressive content — may not need processing")
    else:
        print("?  Scan type unknown — run 'frameweaver analyze' for detailed classification")

    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    """Full analysis and classification pipeline."""
    input_path = args.input
    output_path = args.output

    # Probe video
    print(f"Probing: {input_path}")
    try:
        info = probe_video(input_path)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print(f"  {info.width}x{info.height} @ {info.fps:.3f}fps | {info.codec} | "
          f"{info.scan_type} | {info.total_frames} frames")
    print()

    # Extract metrics
    extractor = FrameMetricExtractor(input_path, info)

    if args.sample:
        print("Running quick sample analysis (5 sample points)...")
        extraction = extractor.extract_sample(sample_points=5, frames_per_sample=150)
    else:
        total = args.max_frames or info.total_frames
        print(f"Extracting frame metrics ({total} frames)...")

        def progress(done: int, total: int, fps: float):
            pct = done / total * 100 if total else 0
            bar_len = 40
            filled = int(bar_len * done / total) if total else 0
            bar = "█" * filled + "░" * (bar_len - filled)
            eta = (total - done) / fps if fps > 0 else 0
            sys.stdout.write(
                f"\r  [{bar}] {pct:5.1f}% | {done}/{total} frames | "
                f"{fps:.0f} fps | ETA: {eta:.0f}s"
            )
            sys.stdout.flush()

        extraction = extractor.extract_all(
            max_frames=args.max_frames,
            progress_callback=progress if not args.quiet else None,
        )

        if not args.quiet:
            print()  # Newline after progress bar

    print(f"\n  Extracted {extraction.total_frames} frames in "
          f"{extraction.extraction_time_seconds:.1f}s "
          f"({extraction.frames_per_second:.0f} fps)")
    print()

    # Classify segments
    print("Classifying segments...")
    classifier = SegmentClassifier()
    result = classifier.classify(extraction)

    # Display results
    _print_results(result, verbose=args.verbose)

    # Save output
    if output_path:
        result.to_json(output_path)
        print(f"\nResults saved to: {output_path}")
    elif not args.quiet:
        # Default output path
        default_out = Path(input_path).stem + "_analysis.json"
        result.to_json(default_out)
        print(f"\nResults saved to: {default_out}")

    return 0


def _print_results(result, verbose: bool = False) -> None:
    """Pretty-print classification results to terminal."""
    summary = result.summary

    # Color codes for terminal
    COLORS = {
        "telecine": "\033[92m",    # Green
        "progressive": "\033[94m", # Blue
        "interlaced": "\033[93m",  # Yellow
        "hybrid": "\033[95m",      # Magenta
        "unknown": "\033[91m",     # Red
    }
    RESET = "\033[0m"
    BOLD = "\033[1m"

    print(f"{BOLD}═══ Classification Results ═══{RESET}")
    print()

    # Summary bar
    if summary.get("type_percentages"):
        print("  Content breakdown:")
        for content_type, pct in sorted(
            summary["type_percentages"].items(), key=lambda x: -x[1]
        ):
            color = COLORS.get(content_type, "")
            bar_len = int(pct / 2)
            bar = "█" * bar_len
            print(f"    {color}{content_type:12s}{RESET} {bar} {pct:.1f}%")
        print()

    # Recommendation
    print(f"  {BOLD}Recommendation:{RESET} {summary.get('recommendation', 'N/A')}")
    print()

    # Review status
    review_count = result.needs_review_count
    if review_count == 0:
        print(f"  ✓ {BOLD}No segments need manual review{RESET} — fully automatable")
    else:
        print(f"  ⚠ {BOLD}{review_count} segment(s) flagged for review{RESET} "
              f"({result.review_percentage:.1f}% of video)")

    print()

    # Segment list
    print(f"  {BOLD}Segments ({len(result.segments)}):{RESET}")
    print(f"  {'#':>3s}  {'Start':>8s}  {'End':>8s}  {'Frames':>7s}  "
          f"{'Type':12s}  {'Conf':>5s}  {'Comb':>5s}  {'Review':>6s}")
    print(f"  {'─' * 68}")

    for i, seg in enumerate(result.segments):
        color = COLORS.get(seg.segment_type.value, "")
        review_flag = "⚠ YES" if seg.needs_review else "  no"

        # Convert frame numbers to timecode (assuming 29.97fps)
        start_tc = _frames_to_tc(seg.start_frame)
        end_tc = _frames_to_tc(seg.end_frame)

        print(
            f"  {i + 1:3d}  {start_tc}  {end_tc}  {seg.frame_count:7d}  "
            f"{color}{seg.segment_type.value:12s}{RESET}  "
            f"{seg.confidence:5.2f}  {seg.mean_comb_score:5.1f}  {review_flag}"
        )

    if verbose:
        print()
        print(f"  {BOLD}Detailed segment data:{RESET}")
        for i, seg in enumerate(result.segments):
            print(f"\n  --- Segment {i + 1} ---")
            for key, val in seg.to_dict().items():
                print(f"    {key}: {val}")


def _frames_to_tc(frame: int, fps: float = 29.97) -> str:
    """Convert frame number to HH:MM:SS timecode."""
    total_seconds = frame / fps
    h = int(total_seconds // 3600)
    m = int((total_seconds % 3600) // 60)
    s = int(total_seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="frameweaver",
        description="Frameweaver — Intelligent video detelecine and deinterlace detection",
    )
    parser.add_argument("--version", action="version", version=f"frameweaver {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- info command ---
    info_parser = subparsers.add_parser("info", help="Show video stream information")
    info_parser.add_argument("input", help="Input video file")

    # --- analyze command ---
    analyze_parser = subparsers.add_parser("analyze", help="Analyze and classify video content")
    analyze_parser.add_argument("input", help="Input video file")
    analyze_parser.add_argument("-o", "--output", help="Output JSON path (default: <input>_analysis.json)")
    analyze_parser.add_argument("--sample", action="store_true",
                                help="Quick analysis using sampled segments instead of full scan")
    analyze_parser.add_argument("--max-frames", type=int, default=None,
                                help="Maximum frames to analyze (default: all)")
    analyze_parser.add_argument("-v", "--verbose", action="store_true",
                                help="Show detailed per-segment data")
    analyze_parser.add_argument("-q", "--quiet", action="store_true",
                                help="Suppress progress output")

    args = parser.parse_args()

    if args.command == "info":
        return cmd_info(args)
    elif args.command == "analyze":
        return cmd_analyze(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())

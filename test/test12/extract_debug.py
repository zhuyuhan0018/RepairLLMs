#!/usr/bin/env python3
"""
Extract debug.records from a test output JSON and split them into per-step txt files.

Default:
- input: test/test12/outputs/thinking_chains/test12_with_debug.json
- output: test/test12/debug/
"""
import argparse
import json
import pathlib
from datetime import datetime


def format_timestamp(ts):
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def infer_stage(record):
    if record.get("stage"):
        return record["stage"]

    if "iteration_type" in record:
        if record["iteration_type"] == "Initial Analysis":
            return "initial_fix_generation"
        if record["iteration_type"] == "Reflection":
            return "iterative_reflection"

    if "fix_point_id" in record:
        if record.get("iteration", 0) > 1:
            return "iterative_reflection"
        return "initial_fix_generation"

    return "unknown"


def get_filename(record, index=None):
    stage = infer_stage(record)
    attempt = record.get("attempt", 0)
    fix_point_id = record.get("fix_point_id")
    iteration = record.get("iteration", 0)

    if stage == "repair_order_analysis":
        return f"repair_order_analysis_attempt_{attempt}.txt"
    if stage == "initial_fix_generation":
        return f"initial_fix_generation_fixpoint_{fix_point_id}_iteration_{iteration}.txt"
    if stage == "iterative_reflection":
        return f"iterative_reflection_fixpoint_{fix_point_id}_iteration_{iteration}.txt"
    if stage == "fix_validation":
        return f"fix_validation_fixpoint_{fix_point_id}_iteration_{iteration}.txt"
    if stage == "merge_thinking_chains":
        return f"merge_thinking_chains_attempt_{attempt}.txt"

    idx = index if index is not None else 0
    return f"unknown_record_{idx}.txt"


def merge_records(records):
    merged = {}
    for record in records:
        stage = infer_stage(record)
        key = (
            stage,
            record.get("attempt", 0),
            record.get("fix_point_id"),
            record.get("iteration", 0),
        )
        if key not in merged:
            merged[key] = {}

        for k, v in record.items():
            if k not in merged[key] or merged[key][k] is None:
                merged[key][k] = v
            elif isinstance(v, dict) and isinstance(merged[key][k], dict):
                merged[key][k].update(v)
    return list(merged.values())


def create_debug_file(record, output_dir, index=None):
    filename = get_filename(record, index)
    filepath = output_dir / filename
    mode = "a" if filepath.exists() else "w"

    with filepath.open(mode, encoding="utf-8") as f:
        if mode == "a":
            f.write("\n\n" + "=" * 80 + "\n")
            f.write("ADDITIONAL RECORD DATA\n")
            f.write("=" * 80 + "\n\n")

        f.write("=" * 80 + "\n")
        f.write("DEBUG RECORD METADATA\n")
        f.write("=" * 80 + "\n")
        f.write(f"Stage: {record.get('stage', 'N/A')}\n")
        f.write(f"Attempt: {record.get('attempt', 'N/A')}\n")

        if "fix_point_id" in record:
            f.write(f"Fix Point ID: {record.get('fix_point_id', 'N/A')}\n")
            f.write(f"Fix Point Location: {record.get('fix_point_location', 'N/A')}\n")
            f.write(f"Fix Point Description: {record.get('fix_point_description', 'N/A')}\n")

        if "iteration" in record:
            f.write(f"Iteration: {record.get('iteration', 'N/A')}\n")
            f.write(f"Iteration Type: {record.get('iteration_type', 'N/A')}\n")

        if "temperature" in record:
            f.write(f"Temperature: {record.get('temperature', 'N/A')}\n")
        if "timestamp" in record:
            try:
                f.write(f"Timestamp: {format_timestamp(record['timestamp'])}\n")
            except Exception:
                f.write(f"Timestamp: {record.get('timestamp')}\n")
        if "api_duration_seconds" in record:
            try:
                f.write(f"API Duration: {record['api_duration_seconds']:.2f} seconds\n")
            except Exception:
                f.write(f"API Duration: {record.get('api_duration_seconds')}\n")
        if "response_chars" in record:
            f.write(f"Response Length: {record.get('response_chars')} characters\n")
        if "buggy_code_chars" in record:
            f.write(f"Buggy Code Length: {record.get('buggy_code_chars')} characters\n")
        f.write("\n")

        if "prompt" in record:
            f.write("=" * 80 + "\n")
            f.write("PROMPT (Sent to Model)\n")
            f.write("=" * 80 + "\n")
            f.write(record["prompt"])
            f.write("\n\n")

        if "response" in record:
            f.write("=" * 80 + "\n")
            f.write("RESPONSE (From Model)\n")
            f.write("=" * 80 + "\n")
            f.write(record["response"])
            f.write("\n\n")

        if "bug_location" in record:
            f.write("=" * 80 + "\n")
            f.write("BUG LOCATION (Context)\n")
            f.write("=" * 80 + "\n")
            f.write(record["bug_location"])
            f.write("\n\n")

        if "thinking" in record:
            f.write("=" * 80 + "\n")
            f.write("THINKING (Parsed)\n")
            f.write("=" * 80 + "\n")
            f.write(record["thinking"])
            f.write("\n\n")

        if "fix" in record:
            f.write("=" * 80 + "\n")
            f.write("FIX CODE (Parsed)\n")
            f.write("=" * 80 + "\n")
            f.write(record["fix"])
            f.write("\n\n")

        if record.get("grep_cmd"):
            f.write("=" * 80 + "\n")
            f.write("GREP COMMAND\n")
            f.write("=" * 80 + "\n")
            f.write(record["grep_cmd"])
            f.write("\n\n")


def main():
    parser = argparse.ArgumentParser(description="Extract and split debug records into per-step txt files.")
    parser.add_argument(
        "--input",
        default=None,
        help="Path to the JSON file containing debug.records (default: test12 outputs file).",
    )
    parser.add_argument(
        "--output-dirname",
        default="debug",
        help="Output directory name under test/test12/ (default: debug).",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="If set, delete the output directory first (safe for debug artifacts).",
    )
    args = parser.parse_args()

    script_dir = pathlib.Path(__file__).parent
    json_file = (
        pathlib.Path(args.input)
        if args.input
        else (script_dir / "outputs" / "thinking_chains" / "test12_with_debug.json")
    )
    debug_dir = script_dir / args.output_dirname

    if args.clean and debug_dir.exists():
        for p in debug_dir.glob("**/*"):
            if p.is_file():
                p.unlink()
        for p in sorted(debug_dir.glob("**/*"), reverse=True):
            if p.is_dir():
                try:
                    p.rmdir()
                except OSError:
                    pass

    debug_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading JSON from: {json_file}")
    with json_file.open("r", encoding="utf-8") as f:
        data = json.load(f)

    debug_records = data.get("debug", {}).get("records", [])
    print(f"Found {len(debug_records)} debug records")

    print("Merging records with same key...")
    merged_records = merge_records(debug_records)
    print(f"After merging: {len(merged_records)} unique records")

    for i, record in enumerate(merged_records, 1):
        filename = get_filename(record, i)
        print(f"Creating file {i}/{len(merged_records)}: {filename}")
        create_debug_file(record, debug_dir, i)

    print(f"\nAll debug files created in: {debug_dir}")
    print(f"Total debug records: {len(debug_records)}")


if __name__ == "__main__":
    main()

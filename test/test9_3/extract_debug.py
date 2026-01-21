#!/usr/bin/env python3
"""
Extract debug records from test9_3_all_fix_points_with_debug.json
and organize them into individual txt files in debug/ directory
"""
import argparse
import json
import pathlib
from datetime import datetime

def format_timestamp(ts):
    """Format timestamp to readable string"""
    return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

def infer_stage(record):
    """Infer stage from record if not explicitly set"""
    if 'stage' in record:
        return record['stage']
    
    # Infer from other fields
    if 'iteration_type' in record:
        if record['iteration_type'] == 'Initial Analysis':
            return 'initial_fix_generation'
        elif record['iteration_type'] == 'Reflection':
            return 'iterative_reflection'
    
    # Default based on fields present
    if 'fix_point_id' in record:
        if 'iteration' in record and record.get('iteration', 0) > 1:
            return 'iterative_reflection'
        else:
            return 'initial_fix_generation'
    
    return 'unknown'

def get_filename(record, index=None):
    """Generate filename for a debug record"""
    stage = infer_stage(record)
    attempt = record.get('attempt', 0)
    fix_point_id = record.get('fix_point_id')
    iteration = record.get('iteration', 0)
    
    if stage == 'repair_order_analysis':
        return f"repair_order_analysis_attempt_{attempt}.txt"
    elif stage == 'initial_fix_generation':
        return f"initial_fix_generation_fixpoint_{fix_point_id}_iteration_{iteration}.txt"
    elif stage == 'iterative_reflection':
        return f"iterative_reflection_fixpoint_{fix_point_id}_iteration_{iteration}.txt"
    else:
        # Use index as fallback
        idx = index if index is not None else 0
        return f"unknown_record_{idx}.txt"

def merge_records(records):
    """Merge records with same key (stage, fix_point_id, iteration, attempt)"""
    merged = {}
    for record in records:
        stage = infer_stage(record)
        key = (
            stage,
            record.get('attempt', 0),
            record.get('fix_point_id'),
            record.get('iteration', 0)
        )
        if key not in merged:
            merged[key] = {}
        # Merge fields, preferring non-None values
        for k, v in record.items():
            if k not in merged[key] or merged[key][k] is None:
                merged[key][k] = v
            elif isinstance(v, dict) and isinstance(merged[key][k], dict):
                merged[key][k].update(v)
    return list(merged.values())

def create_debug_file(record, output_dir, index=None):
    """Create a single debug txt file for a record"""
    filename = get_filename(record, index)
    filepath = output_dir / filename
    
    # Use append mode if file exists (for merging)
    mode = 'a' if filepath.exists() else 'w'
    
    with filepath.open(mode, encoding='utf-8') as f:
        if mode == 'a':
            f.write("\n\n" + "=" * 80 + "\n")
            f.write("ADDITIONAL RECORD DATA\n")
            f.write("=" * 80 + "\n\n")
        # Write metadata
        f.write("=" * 80 + "\n")
        f.write("DEBUG RECORD METADATA\n")
        f.write("=" * 80 + "\n")
        f.write(f"Stage: {record.get('stage', 'N/A')}\n")
        f.write(f"Attempt: {record.get('attempt', 'N/A')}\n")
        if 'fix_point_id' in record:
            f.write(f"Fix Point ID: {record.get('fix_point_id', 'N/A')}\n")
            f.write(f"Fix Point Location: {record.get('fix_point_location', 'N/A')}\n")
            f.write(f"Fix Point Description: {record.get('fix_point_description', 'N/A')}\n")
        if 'iteration' in record:
            f.write(f"Iteration: {record.get('iteration', 'N/A')}\n")
            f.write(f"Iteration Type: {record.get('iteration_type', 'N/A')}\n")
        if 'temperature' in record:
            f.write(f"Temperature: {record.get('temperature', 'N/A')}\n")
        if 'timestamp' in record:
            f.write(f"Timestamp: {format_timestamp(record['timestamp'])}\n")
        if 'api_duration_seconds' in record:
            f.write(f"API Duration: {record['api_duration_seconds']:.2f} seconds\n")
        if 'response_chars' in record:
            f.write(f"Response Length: {record['response_chars']} characters\n")
        if 'buggy_code_chars' in record:
            f.write(f"Buggy Code Length: {record['buggy_code_chars']} characters\n")
        f.write("\n")
        
        # Write prompt
        if 'prompt' in record:
            f.write("=" * 80 + "\n")
            f.write("PROMPT (Sent to Model)\n")
            f.write("=" * 80 + "\n")
            f.write(record['prompt'])
            f.write("\n\n")
        
        # Write response
        if 'response' in record:
            f.write("=" * 80 + "\n")
            f.write("RESPONSE (From Model)\n")
            f.write("=" * 80 + "\n")
            f.write(record['response'])
            f.write("\n\n")
        
        # Write additional fields if present
        if 'bug_location' in record:
            f.write("=" * 80 + "\n")
            f.write("BUG LOCATION (Context)\n")
            f.write("=" * 80 + "\n")
            f.write(record['bug_location'])
            f.write("\n\n")
        
        # Write parsed fields if present (from detailed iteration records)
        if 'thinking' in record:
            f.write("=" * 80 + "\n")
            f.write("THINKING (Parsed)\n")
            f.write("=" * 80 + "\n")
            f.write(record['thinking'])
            f.write("\n\n")
        
        if 'fix' in record:
            f.write("=" * 80 + "\n")
            f.write("FIX CODE (Parsed)\n")
            f.write("=" * 80 + "\n")
            f.write(record['fix'])
            f.write("\n\n")
        
        if 'grep_cmd' in record and record['grep_cmd']:
            f.write("=" * 80 + "\n")
            f.write("GREP COMMAND\n")
            f.write("=" * 80 + "\n")
            f.write(record['grep_cmd'])
            f.write("\n\n")
        
        # Write other metadata
        other_fields = ['prompt_length', 'response_length', 'thinking_length', 'fix_length', 
                       'is_truncated', 'context_available', 'context_length']
        has_other = any(k in record for k in other_fields)
        if has_other:
            f.write("=" * 80 + "\n")
            f.write("ADDITIONAL METADATA\n")
            f.write("=" * 80 + "\n")
            for field in other_fields:
                if field in record:
                    f.write(f"{field}: {record[field]}\n")
            f.write("\n")

def main():
    parser = argparse.ArgumentParser(description="Extract and split debug records into per-step txt files.")
    parser.add_argument(
        "--input",
        default=None,
        help="Path to the JSON file containing debug.records (default: test9_3 outputs file).",
    )
    parser.add_argument(
        "--output-dirname",
        default="debug",
        help="Output directory name under test/test9_3/ (default: debug).",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="If set, delete the output directory first (safe for debug artifacts).",
    )
    args = parser.parse_args()

    # Paths
    script_dir = pathlib.Path(__file__).parent
    json_file = (
        pathlib.Path(args.input)
        if args.input
        else (script_dir / "outputs" / "thinking_chains" / "test9_3_all_fix_points_with_debug.json")
    )
    debug_dir = script_dir / args.output_dirname

    if args.clean and debug_dir.exists():
        # Only remove files inside the debug dir (no recursive surprises)
        for p in debug_dir.glob("**/*"):
            if p.is_file():
                p.unlink()
        # Remove empty subdirs if any
        for p in sorted(debug_dir.glob("**/*"), reverse=True):
            if p.is_dir():
                try:
                    p.rmdir()
                except OSError:
                    pass
    
    # Create debug directory
    debug_dir.mkdir(parents=True, exist_ok=True)
    
    # Load JSON
    print(f"Loading JSON from: {json_file}")
    with json_file.open('r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Extract debug records
    debug_records = data.get('debug', {}).get('records', [])
    print(f"Found {len(debug_records)} debug records")
    
    # Merge records with same key
    print("Merging records with same key...")
    merged_records = merge_records(debug_records)
    print(f"After merging: {len(merged_records)} unique records")
    
    # Create files
    for i, record in enumerate(merged_records, 1):
        filename = get_filename(record, i)
        print(f"Creating file {i}/{len(merged_records)}: {filename}")
        create_debug_file(record, debug_dir, i)
    
    print(f"\nAll debug files created in: {debug_dir}")
    print(f"Total debug records: {len(debug_records)}")

if __name__ == '__main__':
    main()


#!/usr/bin/env python3
"""
Test9_3 (sort-only): Repair Order Analysis only (DEBUG)
- Only run repair order analysis (sorting fix_points)
- Skip initial fix generation and all other stages
- Save all model prompts/responses for this stage
"""
import json
import os
import sys
import pathlib
import time
from datetime import datetime

# Add repo root to path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))


def main() -> int:
    test_file = pathlib.Path(__file__).parent.parent / "test6" / "test6.json"
    if not test_file.exists():
        print(f"Error: Test file not found: {test_file}", flush=True)
        return 1

    with test_file.open("r", encoding="utf-8") as f:
        test_case = json.load(f)

    # Ensure we only run repair order analysis
    os.environ["SKIP_INITIAL_FIX"] = "1"
    os.environ["SKIP_VALIDATION"] = "1"
    os.environ["SKIP_MERGE"] = "1"
    # DO NOT set SKIP_REPAIR_ORDER

    # Build detailed bug_location (same style as test9_3)
    detailed_bug_location = test_case["bug_location"]
    if "vulnerability_type" in test_case:
        detailed_bug_location += f"\n\nVulnerability Type: {test_case['vulnerability_type']}"
    if "root_cause" in test_case:
        detailed_bug_location += f"\nRoot Cause: {test_case['root_cause']}"
    if "fix_goal" in test_case:
        detailed_bug_location += f"\nFix Goal: {test_case['fix_goal']}"
    if "fix_points" in test_case:
        detailed_bug_location += "\n\nVulnerability Details:"
        for i, fp in enumerate(test_case["fix_points"], 1):
            detailed_bug_location += (
                f"\n  {i}. {fp['file']}:{fp.get('function', 'N/A')} (lines {fp['line_start']}-{fp['line_end']})"
            )

    debug_info = []

    try:
        from core.initial_chain_builder import InitialChainBuilder
        from models.aliyun_model import AliyunModel
        from config import ALIYUN_API_KEY

        codebase_path = test_case.get("codebase_path", "datasets/codebases/open62541")
        aliyun_model = AliyunModel(ALIYUN_API_KEY)
        chain_builder = InitialChainBuilder(aliyun_model, codebase_path)

        print("=" * 60, flush=True)
        print("Test9_3 (sort-only): Repair Order Analysis (DEBUG)", flush=True)
        print("Configuration:", flush=True)
        print("  ✓ Repair order analysis: ENABLED (from JSON fix_points, sorted by LLM)", flush=True)
        print("  ✗ Initial fix generation: SKIPPED", flush=True)
        print("  ✗ Validation: SKIPPED", flush=True)
        print("  ✗ Merging: SKIPPED", flush=True)
        print("  ✓ DEBUG: Save prompts and raw responses", flush=True)
        print("=" * 60, flush=True)

        print("\nAnalyzing repair order...", flush=True)
        start = time.time()
        fix_points = chain_builder.analyze_repair_order(
            test_case["buggy_code"],
            detailed_bug_location,
            fix_points=test_case.get("fix_points"),
            debug_info=debug_info,
        )
        end = time.time()

        output_dir = pathlib.Path("test") / "test9_3" / "outputs" / "thinking_chains"
        output_dir.mkdir(parents=True, exist_ok=True)

        results = {
            "case_id": "test9_3_sort_only",
            "original_case_id": test_case.get("case_id", "test6"),
            "created_at": datetime.now().isoformat(),
            "bug_location": detailed_bug_location,
            "repair_order_analysis": {
                "fix_points": fix_points,
                "total_fix_points": len(fix_points) if fix_points else 0,
                "duration_seconds": end - start,
            },
            "debug": {
                "records": debug_info,
                "total_records": len(debug_info),
            },
        }

        json_output = output_dir / "test9_3_sort_only_with_debug.json"
        with json_output.open("w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print("\n" + "=" * 60, flush=True)
        print("Summary:", flush=True)
        print("=" * 60, flush=True)
        print(f"Duration: {end - start:.2f} seconds", flush=True)
        print(f"Fix points: {len(fix_points) if fix_points else 0}", flush=True)
        print(f"Debug records: {len(debug_info)}", flush=True)
        print(f"Saved: {json_output}", flush=True)
        return 0
    except Exception as e:
        print(f"Error: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())





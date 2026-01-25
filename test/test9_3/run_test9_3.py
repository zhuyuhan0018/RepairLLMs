#!/usr/bin/env python3
"""
Test9_3: Repair Order Analysis + All Fix Points Initial Generation (DEBUG)
- Repair order analysis (from JSON fix_points, sorted by LLM)
- Initial generation for ALL fix points
- Skip validation, optimization, and merging
- DEBUG: Save all model prompts and raw responses during the experiment
"""
import json
import os
import sys
import pathlib
import time
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))


def main() -> int:
    test_file = pathlib.Path(__file__).parent.parent / "test6" / "test6.json"
    if not test_file.exists():
        print(f"Error: Test file not found: {test_file}", flush=True)
        return 1

    with test_file.open("r", encoding="utf-8") as f:
        test_case = json.load(f)

    case_id = "test9_3"
    original_case_id = test_case.get("case_id", "test6")
    codebase_path = test_case.get("codebase_path", "datasets/codebases/open62541")

    print("=" * 60, flush=True)
    print("Test9_3: Repair Order Analysis + All Fix Points Initial Generation (DEBUG)")
    print("Configuration:")
    print("  ✓ Repair order analysis: ENABLED (from JSON fix_points, sorted by LLM)")
    print("  ✓ All fix points initial generation: ENABLED")
    print("  ✗ Validation: SKIPPED")
    print("  ✗ Optimization: SKIPPED")
    print("  ✗ Merging thinking chains: SKIPPED")
    print("  ✓ DEBUG: Save prompts and raw responses")
    print("=" * 60, flush=True)

    # Skip stages
    os.environ["SKIP_VALIDATION"] = "1"
    os.environ["SKIP_MERGE"] = "1"
    # DO NOT set SKIP_INITIAL_FIX
    # DO NOT set SKIP_REPAIR_ORDER

    # Build detailed bug_location (JSON-like)
    detailed_bug_location = test_case["bug_location"]
    if "vulnerability_type" in test_case:
        detailed_bug_location += f"\n\nVulnerability Type: {test_case['vulnerability_type']}"
    if "root_cause" in test_case:
        detailed_bug_location += f"\nRoot Cause: {test_case['root_cause']}"
    if "fix_goal" in test_case:
        detailed_bug_location += f"\nFix Goal: {test_case['fix_goal']}"
    if "affected_files" in test_case:
        location_parts = []
        for file_info in test_case["affected_files"]:
            for func in file_info["functions"]:
                location_parts.append(f"{file_info['path']}:{func['name']} (line {func['line']})")
        if location_parts:
            detailed_bug_location += "\n\nDetailed locations:\n" + "\n".join(f"  - {loc}" for loc in location_parts)
    if "fix_points" in test_case:
        detailed_bug_location += "\n\nVulnerability Details:"
        for i, fp in enumerate(test_case["fix_points"], 1):
            detailed_bug_location += (
                f"\n  {i}. {fp['file']}:{fp.get('function', 'N/A')} (lines {fp['line_start']}-{fp['line_end']})"
            )

    # Debug buffer: collect all prompts + responses
    debug_info = []

    try:
        from core.initial_chain_builder import InitialChainBuilder
        from models.aliyun_model import AliyunModel
        from config import ALIYUN_API_KEY

        aliyun_model = AliyunModel(ALIYUN_API_KEY)
        chain_builder = InitialChainBuilder(aliyun_model, codebase_path)

        # Step 1: Repair order analysis
        print("\nAnalyzing repair order...", flush=True)
        repair_order_start = time.time()
        fix_points = chain_builder.analyze_repair_order(
            test_case["buggy_code"],
            detailed_bug_location,
            fix_points=test_case.get("fix_points"),
            debug_info=debug_info,
        )
        repair_order_end = time.time()
        repair_order_duration = repair_order_end - repair_order_start

        if not fix_points:
            print("\n⚠️  No fix points identified. Cannot proceed.", flush=True)
            return 1

        # Step 2: Initial generation for all fix points
        print(f"\nGenerating initial fix for {len(fix_points)} fix points...", flush=True)
        all_thinking_chains = {}
        all_final_fix_codes = {}
        all_fix_point_results = []
        total_initial_fix_duration = 0.0

        for i, fix_point in enumerate(fix_points):
            print(f"\nProcessing Fix Point {i+1}/{len(fix_points)}: {fix_point.get('location', 'N/A')}", flush=True)
            fp_start = time.time()
            thinking_chain, final_fix_code = chain_builder.build_fix_point_chain(
                buggy_code=test_case["buggy_code"],
                fixed_code=None,
                fix_point=fix_point,
                fixed_code_dict=None,
                debug_info=debug_info,
                all_fix_points=fix_points,
                current_fix_point_index=i,
            )
            fp_end = time.time()
            fp_duration = fp_end - fp_start
            total_initial_fix_duration += fp_duration

            location_key = fix_point.get("location", f"fix_point_{i}")
            all_thinking_chains[location_key] = thinking_chain
            all_final_fix_codes[location_key] = final_fix_code

            all_fix_point_results.append({
                "fix_point": fix_point,
                "thinking_chain": thinking_chain,
                "final_fix_code": final_fix_code,
                "duration_seconds": fp_duration,
                "thinking_chain_length": len(thinking_chain),
                "fix_code_length": len(final_fix_code) if final_fix_code else 0,
            })

        # Save results
        output_dir = pathlib.Path("test") / "test9_3" / "outputs" / "thinking_chains"
        output_dir.mkdir(parents=True, exist_ok=True)

        results = {
            "case_id": case_id,
            "original_case_id": original_case_id,
            "bug_location": detailed_bug_location,
            "repair_order_analysis": {
                "fix_points": fix_points,
                "total_fix_points": len(fix_points),
                "api_duration_seconds": repair_order_duration,
            },
            "initial_fix_generation": {
                "thinking_chains": all_thinking_chains,
                "final_fix_codes": all_final_fix_codes,
                "fix_point_results": all_fix_point_results,
                "total_duration_seconds": total_initial_fix_duration,
                "average_duration_per_fix_point": total_initial_fix_duration / len(fix_points) if fix_points else 0,
            },
            "debug": {
                "records": debug_info,
                "total_records": len(debug_info),
            },
            "total_duration_seconds": repair_order_duration + total_initial_fix_duration,
            "created_at": datetime.now().isoformat(),
            "test_config": {
                "skip_initial_fix": False,
                "skip_validation": True,
                "skip_merge": True,
                "use_model_api": True,
                "json_fix_points_available": "fix_points" in test_case,
                "optimization_enabled": False,
                "debug_prompts_and_responses": True,
            },
        }

        if "fix_points" in test_case and test_case["fix_points"]:
            results["comparison"] = {
                "json_fix_points_count": len(test_case["fix_points"]),
                "model_fix_points_count": len(fix_points),
                "identification_rate": len(fix_points) / len(test_case["fix_points"]) if test_case["fix_points"] else 0,
                "json_fix_points": test_case["fix_points"],
            }

        json_output = output_dir / "test9_3_all_fix_points_with_debug.json"
        with json_output.open("w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        debug_output = output_dir / "test9_3_debug.json"
        with debug_output.open("w", encoding="utf-8") as f:
            json.dump({"records": debug_info, "total_records": len(debug_info)}, f, indent=2, ensure_ascii=False)

        print("\n" + "=" * 60, flush=True)
        print("Summary:", flush=True)
        print("=" * 60, flush=True)
        print(f"Repair order duration: {repair_order_duration:.2f} seconds", flush=True)
        print(f"Fix points: {len(fix_points)}", flush=True)
        print(f"Initial generation total: {total_initial_fix_duration:.2f} seconds", flush=True)
        print(f"Debug records: {len(debug_info)}", flush=True)
        print(f"Results saved to: {output_dir}", flush=True)

        return 0
    except Exception as e:
        print(f"Error: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())







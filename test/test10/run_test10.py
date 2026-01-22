#!/usr/bin/env python3
"""
Test10: Repair Order Analysis + All Fix Points Initial Generation + Validation + Merge (DEBUG)

Stages:
1) repair order analysis (sorted fix points)
2) initial fix generation for ALL fix points
3) validation (enabled, using fixed_code dict; model does not see ground truth directly)
4) merge thinking chains (model-based merge unless SKIP_MERGE is enabled)

Artifacts:
- JSON output with all per-fix-point chains, final fixes, merge result, and debug records (prompts/responses)
"""
import json
import os
import sys
import pathlib
import time
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))


def build_detailed_bug_location(test_case: dict) -> str:
    detailed = test_case["bug_location"]
    if "vulnerability_type" in test_case:
        detailed += f"\n\nVulnerability Type: {test_case['vulnerability_type']}"
    if "root_cause" in test_case:
        detailed += f"\nRoot Cause: {test_case['root_cause']}"
    if "fix_goal" in test_case:
        detailed += f"\nFix Goal: {test_case['fix_goal']}"
    if "affected_files" in test_case:
        location_parts = []
        for file_info in test_case["affected_files"]:
            for func in file_info["functions"]:
                location_parts.append(f"{file_info['path']}:{func['name']} (line {func['line']})")
        if location_parts:
            detailed += "\n\nDetailed locations:\n" + "\n".join(f"  - {loc}" for loc in location_parts)
    if "fix_points" in test_case:
        detailed += "\n\nVulnerability Details:"
        for i, fp in enumerate(test_case["fix_points"], 1):
            detailed += f"\n  {i}. {fp['file']}:{fp.get('function', 'N/A')} (lines {fp['line_start']}-{fp['line_end']})"
    return detailed


def main() -> int:
    test_file = pathlib.Path(__file__).parent.parent / "test6" / "test6.json"
    if not test_file.exists():
        print(f"Error: Test file not found: {test_file}", flush=True)
        return 1

    with test_file.open("r", encoding="utf-8") as f:
        test_case = json.load(f)

    case_id = "test10"
    original_case_id = test_case.get("case_id", "test6")
    codebase_path = test_case.get("codebase_path", "datasets/codebases/open62541")

    # Ensure validation + merge are enabled for this experiment
    os.environ.pop("SKIP_VALIDATION", None)
    os.environ.pop("SKIP_MERGE", None)
    os.environ.pop("SKIP_INITIAL_FIX", None)
    os.environ.pop("SKIP_REPAIR_ORDER", None)

    print("=" * 60, flush=True)
    print("Test10: Repair Order + All Fix Points Initial Generation + Validation + Merge (DEBUG)", flush=True)
    print("Configuration:", flush=True)
    print("  ✓ Repair order analysis: ENABLED", flush=True)
    print("  ✓ All fix points initial generation: ENABLED", flush=True)
    print("  ✓ Validation: ENABLED", flush=True)
    print("  ✓ Merge thinking chains: ENABLED", flush=True)
    print("  ✓ DEBUG: Save prompts and raw responses", flush=True)
    print("=" * 60, flush=True)

    detailed_bug_location = build_detailed_bug_location(test_case)
    fixed_code_dict = test_case.get("fixed_code")
    if not fixed_code_dict:
        print("⚠️  fixed_code dictionary is missing in test case; validation cannot run.", flush=True)
        print("    Please ensure test case contains `fixed_code` if you want validation.", flush=True)

    debug_info = []

    try:
        from core.initial_chain_builder import InitialChainBuilder
        from models.aliyun_model import AliyunModel
        from config import ALIYUN_API_KEY

        aliyun_model = AliyunModel(ALIYUN_API_KEY)
        chain_builder = InitialChainBuilder(aliyun_model, codebase_path)

        # Stage 1: repair order analysis
        print("\nAnalyzing repair order...", flush=True)
        ro_start = time.time()
        fix_points = chain_builder.analyze_repair_order(
            test_case["buggy_code"],
            detailed_bug_location,
            fix_points=test_case.get("fix_points"),
            debug_info=debug_info,
        )
        ro_end = time.time()

        if not fix_points:
            print("\n⚠️  No fix points identified. Stop.", flush=True)
            return 1

        # Stage 2+3: initial generation + validation for all fix points
        print(f"\nGenerating initial fixes for {len(fix_points)} fix points (with validation)...", flush=True)
        all_thinking_chains = {}
        all_final_fix_codes = {}
        per_fix_point = []

        gen_start = time.time()
        for i, fp in enumerate(fix_points):
            print(f"\nProcessing Fix Point {i+1}/{len(fix_points)}: {fp.get('location', 'N/A')}", flush=True)
            fp_start = time.time()
            thinking_chain, final_fix_code = chain_builder.build_fix_point_chain(
                buggy_code=test_case["buggy_code"],
                fixed_code=None,
                fix_point=fp,
                fixed_code_dict=fixed_code_dict,
                debug_info=debug_info,
                all_fix_points=fix_points,
                current_fix_point_index=i,
            )
            fp_end = time.time()

            loc_key = fp.get("location", f"fix_point_{i+1}")
            all_thinking_chains[loc_key] = thinking_chain
            all_final_fix_codes[loc_key] = final_fix_code
            per_fix_point.append({
                "fix_point": fp,
                "duration_seconds": fp_end - fp_start,
                "thinking_chain_length": len(thinking_chain),
                "final_fix_code_length": len(final_fix_code) if final_fix_code else 0,
            })
        gen_end = time.time()

        # Stage 4: merge thinking chains
        print("\nMerging thinking chains...", flush=True)
        merge_start = time.time()
        merged_chain = chain_builder.merge_thinking_chains(
            fix_points,
            all_thinking_chains,
            all_final_fix_codes,
            debug_info=debug_info,
        )
        merge_end = time.time()

        # Save artifacts
        out_dir = pathlib.Path("test") / "test10" / "outputs" / "thinking_chains"
        out_dir.mkdir(parents=True, exist_ok=True)

        results = {
            "case_id": case_id,
            "original_case_id": original_case_id,
            "created_at": datetime.now().isoformat(),
            "bug_location": detailed_bug_location,
            "repair_order_analysis": {
                "fix_points": fix_points,
                "total_fix_points": len(fix_points),
                "duration_seconds": ro_end - ro_start,
            },
            "initial_fix_generation": {
                "per_fix_point": per_fix_point,
                "thinking_chains": all_thinking_chains,
                "final_fix_codes": all_final_fix_codes,
                "duration_seconds": gen_end - gen_start,
            },
            "merge": {
                "merged_thinking_chain": merged_chain,
                "duration_seconds": merge_end - merge_start,
            },
            "debug": {
                "records": debug_info,
                "total_records": len(debug_info),
            },
            "durations": {
                "repair_order_seconds": ro_end - ro_start,
                "generation_seconds": gen_end - gen_start,
                "merge_seconds": merge_end - merge_start,
                "total_seconds": (ro_end - ro_start) + (gen_end - gen_start) + (merge_end - merge_start),
            },
        }

        json_path = out_dir / "test10_with_debug.json"
        with json_path.open("w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        txt_path = out_dir / "test10_merged_thinking_chain.txt"
        with txt_path.open("w", encoding="utf-8") as f:
            f.write(merged_chain or "")

        print("\n" + "=" * 60, flush=True)
        print("Summary:", flush=True)
        print("=" * 60, flush=True)
        print(f"Fix points: {len(fix_points)}", flush=True)
        print(f"Repair order: {ro_end - ro_start:.2f}s", flush=True)
        print(f"Generation+validation: {gen_end - gen_start:.2f}s", flush=True)
        print(f"Merge: {merge_end - merge_start:.2f}s", flush=True)
        print(f"Debug records: {len(debug_info)}", flush=True)
        print(f"Saved JSON: {json_path}", flush=True)
        print(f"Saved merged chain TXT: {txt_path}", flush=True)
        return 0

    except Exception as e:
        print(f"Error: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())





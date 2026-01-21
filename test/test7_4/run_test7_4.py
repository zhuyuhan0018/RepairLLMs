#!/usr/bin/env python3
"""
Test7_4: Repair Order Analysis + First Fix Point Initial Generation
- Use model API to analyze and generate repair order
- Generate initial fix for the FIRST fix point only
- Skip validation, optimization, and other fix points
"""
import json
import os
import sys
import pathlib
import time
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))

print("Script started", flush=True)


def main():
    """Run test7_4: Repair order analysis + first fix point initial generation only"""
    print("Entering main()", flush=True)
    
    # Load test case (use test6.json)
    print("Loading test case...", flush=True)
    test_file = pathlib.Path(__file__).parent.parent / 'test6' / 'test6.json'
    print(f"Test file path: {test_file}", flush=True)
    if not test_file.exists():
        print(f"Error: Test file not found: {test_file}", flush=True)
        return 1
    
    print("Opening JSON file...", flush=True)
    with test_file.open('r', encoding='utf-8') as f:
        test_case = json.load(f)
    print("JSON loaded successfully", flush=True)
    
    case_id = 'test7_4'  # Use test7_4 as case_id for output organization
    original_case_id = test_case.get('case_id', 'test6')
    codebase_path = test_case.get('codebase_path', 'datasets/codebases/open62541')
    
    print("="*60, flush=True)
    print("Running Test7_4: Repair Order Analysis + First Fix Point Initial Generation")
    print("Configuration:")
    print("  ✓ Repair order analysis: ENABLED (via model API)")
    print("  ✓ First fix point initial generation: ENABLED")
    print("  ✗ Validation: SKIPPED")
    print("  ✗ Optimization: SKIPPED")
    print("  ✗ Other fix points: SKIPPED")
    print("  ✗ Merging thinking chains: SKIPPED")
    print("="*60, flush=True)
    print(f"Case ID: {case_id}", flush=True)
    print(f"Bug Location: {test_case['bug_location']}", flush=True)
    print(f"Project: {test_case['project']}", flush=True)
    print(f"Codebase Path: {codebase_path}", flush=True)
    print(f"Crash Type: {test_case['crash_type']}", flush=True)
    print(f"Severity: {test_case['severity']}", flush=True)
    
    # Print fix points from JSON for reference
    if 'fix_points' in test_case:
        print(f"\nFix Points in JSON ({len(test_case['fix_points'])} total) - for reference:", flush=True)
        for fp in test_case['fix_points']:
            print(f"  {fp['id']}. {fp['file']}:{fp.get('function', 'N/A')} (lines {fp['line_start']}-{fp['line_end']})", flush=True)
    
    print("\n" + "="*60, flush=True)
    
    # Set environment: Skip validation, merge, and optimization
    os.environ['SKIP_VALIDATION'] = '1'
    os.environ['SKIP_MERGE'] = '1'
    # DO NOT set SKIP_INITIAL_FIX - we want to generate initial fix for first fix point
    # DO NOT set SKIP_REPAIR_ORDER - we want model to analyze
    
    # Build detailed bug_location for model
    detailed_bug_location = test_case['bug_location']
    
    # Add vulnerability type and description if available
    if 'vulnerability_type' in test_case:
        detailed_bug_location += f"\n\nVulnerability Type: {test_case['vulnerability_type']}"
    if 'root_cause' in test_case:
        detailed_bug_location += f"\nRoot Cause: {test_case['root_cause']}"
    if 'fix_goal' in test_case:
        detailed_bug_location += f"\nFix Goal: {test_case['fix_goal']}"
    
    # Add detailed locations from affected_files
    if 'affected_files' in test_case:
        location_parts = []
        for file_info in test_case['affected_files']:
            for func in file_info['functions']:
                location_parts.append(f"{file_info['path']}:{func['name']} (line {func['line']})")
        if location_parts:
            detailed_bug_location += "\n\nDetailed locations:\n" + "\n".join(f"  - {loc}" for loc in location_parts)
    
    # Add vulnerability locations with descriptions (for model reference)
    if 'fix_points' in test_case:
        detailed_bug_location += "\n\nVulnerability Details:"
        for i, fp in enumerate(test_case['fix_points'], 1):
            detailed_bug_location += f"\n  {i}. {fp['file']}:{fp.get('function', 'N/A')} (lines {fp['line_start']}-{fp['line_end']})"
    
    # Initialize models directly (skip pipeline to avoid unnecessary initialization)
    try:
        print("\nInitializing models...", flush=True)
        print("  - Importing modules...", flush=True)
        from core.initial_chain_builder import InitialChainBuilder
        from models.aliyun_model import AliyunModel
        from config import ALIYUN_API_KEY
        print("  - Modules imported successfully", flush=True)
        
        print("  - Creating AliyunModel instance...", flush=True)
        aliyun_model = AliyunModel(ALIYUN_API_KEY)
        print("  - AliyunModel created", flush=True)
        
        print("  - Creating InitialChainBuilder instance...", flush=True)
        chain_builder = InitialChainBuilder(aliyun_model, codebase_path)
        print("  - InitialChainBuilder created", flush=True)
        
        print("✓ Models initialized successfully!", flush=True)
        
        # Step 1: Analyze repair order using model API
        print("\n" + "="*60, flush=True)
        print("Step 1: Analyzing repair order using model API...", flush=True)
        print("="*60, flush=True)
        print("Note: Model will analyze and generate fix points from buggy_code and bug_location", flush=True)
        print("      fixed_code is NOT used in repair order analysis", flush=True)
        print("      JSON fix_points are provided in bug_location for reference only", flush=True)
        print("="*60, flush=True)
        
        repair_order_start = time.time()
        print(f"  - Calling analyze_repair_order...", flush=True)
        print(f"  - Buggy code length: {len(test_case['buggy_code'])} chars", flush=True)
        print(f"  - Bug location length: {len(detailed_bug_location)} chars", flush=True)
        print(f"  - Starting API call (this may take 10-60 seconds)...", flush=True)
        fix_points = chain_builder.analyze_repair_order(
            test_case['buggy_code'],
            detailed_bug_location,
            fix_points=test_case.get('fix_points')
        )
        print(f"  - analyze_repair_order returned {len(fix_points)} fix points", flush=True)
        repair_order_end = time.time()
        repair_order_duration = repair_order_end - repair_order_start
        
        print(f"\n✓ Model API analysis completed in {repair_order_duration:.2f} seconds", flush=True)
        print(f"✓ Identified {len(fix_points)} fix point(s)", flush=True)
        
        # Print fix points identified by model
        print("\n" + "="*60, flush=True)
        print("Fix Points Identified by Model:", flush=True)
        print("="*60, flush=True)
        for fp in fix_points:
            print(f"\nFix Point {fp.get('id', 'N/A')}:", flush=True)
            print(f"  Location: {fp.get('location', 'N/A')}", flush=True)
            print(f"  Description: {fp.get('description', 'N/A')}", flush=True)
        
        if not fix_points:
            print("\n⚠️  No fix points identified. Cannot proceed with initial fix generation.", flush=True)
            return 1
        
        # Step 2: Generate initial fix for FIRST fix point only
        print("\n" + "="*60, flush=True)
        print("Step 2: Generating initial fix for FIRST fix point only...", flush=True)
        print("="*60, flush=True)
        first_fix_point = fix_points[0]
        print(f"Processing Fix Point {first_fix_point.get('id', 'N/A')}:", flush=True)
        print(f"  Location: {first_fix_point.get('location', 'N/A')}", flush=True)
        print(f"  Description: {first_fix_point.get('description', 'N/A')[:100]}...", flush=True)
        print("="*60, flush=True)
        print("Note: Only the first fix point will be processed.", flush=True)
        print("      Validation is SKIPPED in test7_4.", flush=True)
        print("="*60, flush=True)
        
        # Build thinking chain for first fix point
        # Note: fixed_code is passed as None - model should not see the ground truth
        # No validation will be performed (SKIP_VALIDATION is set)
        initial_fix_start = time.time()
        print(f"\n  - Calling build_fix_point_chain for fix point {first_fix_point.get('id', 'N/A')}...", flush=True)
        print(f"  - Buggy code length: {len(test_case['buggy_code'])} chars", flush=True)
        print(f"  - Starting initial fix generation (this may take 30-120 seconds)...", flush=True)
        
        thinking_chain, final_fix_code = chain_builder.build_fix_point_chain(
            buggy_code=test_case['buggy_code'],
            fixed_code=None,  # Model should not see fixed_code
            fix_point=first_fix_point,
            fixed_code_dict=None,  # No validation in test7_1
            debug_info=None  # Can be set to list to collect debug info
        )
        
        initial_fix_end = time.time()
        initial_fix_duration = initial_fix_end - initial_fix_start
        
        print(f"\n✓ Initial fix generation completed in {initial_fix_duration:.2f} seconds", flush=True)
        print(f"✓ Thinking chain length: {len(thinking_chain)} characters", flush=True)
        if final_fix_code:
            print(f"✓ Final fix code generated: {len(final_fix_code)} characters", flush=True)
        else:
            print("⚠️  No final fix code generated", flush=True)
        
        # Print summary
        print("\n" + "="*60, flush=True)
        print("Summary:", flush=True)
        print("="*60, flush=True)
        print(f"Repair Order Analysis:", flush=True)
        print(f"  - Duration: {repair_order_duration:.2f} seconds", flush=True)
        print(f"  - Fix points identified: {len(fix_points)}", flush=True)
        print(f"\nFirst Fix Point Initial Generation:", flush=True)
        print(f"  - Duration: {initial_fix_duration:.2f} seconds", flush=True)
        print(f"  - Thinking chain length: {len(thinking_chain)} characters", flush=True)
        print(f"  - Final fix code: {'Generated' if final_fix_code else 'Not generated'}", flush=True)
        print(f"  - Validation: SKIPPED (test7_4 configuration)", flush=True)
        print(f"  - Total duration: {repair_order_duration + initial_fix_duration:.2f} seconds", flush=True)
        
        # Save results - use test7_4 directory for outputs
        output_dir = pathlib.Path('test') / 'test7_4' / 'outputs'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        results = {
            'case_id': case_id,
            'original_case_id': original_case_id,  # Keep original for reference
            'bug_location': detailed_bug_location,
            'repair_order_analysis': {
                'fix_points': fix_points,
                'total_fix_points': len(fix_points),
                'api_duration_seconds': repair_order_duration,
            },
            'first_fix_point_generation': {
                'fix_point': first_fix_point,
                'thinking_chain': thinking_chain,
                'final_fix_code': final_fix_code,
                'duration_seconds': initial_fix_duration,
                'validation_performed': False,  # No validation in test7_4
            },
            'extraction_method': 'model_api_analysis',
            'total_duration_seconds': repair_order_duration + initial_fix_duration,
            'created_at': datetime.now().isoformat(),
            'test_config': {
                'skip_initial_fix': False,  # We generated initial fix for first point
                'skip_validation': True,  # Validation skipped in test7_4
                'skip_merge': True,
                'use_model_api': True,
                'json_fix_points_available': 'fix_points' in test_case,
                'only_first_fix_point': True,
                'optimization_enabled': False,  # Optimization skipped
            },
        }
        
        # Add comparison data if JSON fix_points available
        if 'fix_points' in test_case and test_case['fix_points']:
            results['comparison'] = {
                'json_fix_points_count': len(test_case['fix_points']),
                'model_fix_points_count': len(fix_points),
                'json_fix_points': test_case['fix_points']
            }
        
        # Save JSON
        json_output = output_dir / 'thinking_chains' / f"test7_4_first_fix_point.json"
        json_output.parent.mkdir(parents=True, exist_ok=True)
        with json_output.open('w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Save TXT summary
        txt_output = output_dir / 'thinking_chains' / f"test7_4_first_fix_point.txt"
        with txt_output.open('w', encoding='utf-8') as f:
            f.write("="*60 + "\n")
            f.write("Test7_4: Repair Order Analysis + First Fix Point Initial Generation\n")
            f.write("="*60 + "\n")
            f.write(f"Case ID: {case_id}\n")
            f.write(f"Original Case ID: {original_case_id}\n")
            f.write(f"Created at: {results['created_at']}\n")
            f.write(f"Total Duration: {results['total_duration_seconds']:.2f} seconds\n")
            
            f.write("\n" + "="*60 + "\n")
            f.write("Repair Order Analysis:\n")
            f.write("-"*60 + "\n")
            f.write(f"Duration: {repair_order_duration:.2f} seconds\n")
            f.write(f"Fix Points Identified: {len(fix_points)}\n")
            f.write("-"*60 + "\n")
            for fp in fix_points:
                f.write(f"\nFix Point {fp.get('id', 'N/A')}:\n")
                f.write(f"  Location: {fp.get('location', 'N/A')}\n")
                f.write(f"  Description: {fp.get('description', 'N/A')}\n")
            
            f.write("\n" + "="*60 + "\n")
            f.write("First Fix Point Initial Generation:\n")
            f.write("-"*60 + "\n")
            f.write(f"Fix Point ID: {first_fix_point.get('id', 'N/A')}\n")
            f.write(f"Location: {first_fix_point.get('location', 'N/A')}\n")
            f.write(f"Description: {first_fix_point.get('description', 'N/A')}\n")
            f.write(f"Duration: {initial_fix_duration:.2f} seconds\n")
            f.write(f"Thinking Chain Length: {len(thinking_chain)} characters\n")
            f.write(f"Final Fix Code: {'Generated' if final_fix_code else 'Not generated'}\n")
            f.write(f"Validation: SKIPPED (test7_4 configuration)\n\n")
            
            f.write("Original Thinking Chain:\n")
            f.write("-"*60 + "\n")
            f.write(thinking_chain)
            f.write("\n\n")
            
            if final_fix_code:
                f.write("Final Fix Code:\n")
                f.write("-"*60 + "\n")
                f.write(final_fix_code)
                f.write("\n\n")
            
            if 'fix_points' in test_case and test_case['fix_points']:
                f.write("="*60 + "\n")
                f.write("Comparison: Model vs JSON\n")
                f.write("="*60 + "\n")
                f.write(f"Model identified: {len(fix_points)} fix point(s)\n")
                f.write(f"JSON contains: {len(test_case['fix_points'])} fix point(s)\n")
                
                f.write("\nJSON Fix Points (for reference):\n")
                f.write("-"*60 + "\n")
                for fp in test_case['fix_points']:
                    f.write(f"\nFix Point {fp['id']}:\n")
                    f.write(f"  File: {fp['file']}\n")
                    f.write(f"  Function: {fp.get('function', 'N/A')}\n")
                    f.write(f"  Lines: {fp['line_start']}-{fp['line_end']}\n")
        
        print("\n" + "="*60, flush=True)
        print("Results saved:", flush=True)
        print(f"  - JSON: {json_output}", flush=True)
        print(f"  - TXT: {txt_output}", flush=True)
        print("="*60, flush=True)
        
        return 0
    except Exception as e:
        print(f"Error: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())


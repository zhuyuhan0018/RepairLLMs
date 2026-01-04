#!/usr/bin/env python3
"""
Test6_3: Repair Order Analysis + First Fix Point Initial Generation
- Use model API to analyze and generate repair order
- Generate initial fix for the FIRST fix point only
- Skip other fix points and subsequent stages (validation, feedback, merge)
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
    """Run test6_3: Repair order analysis + first fix point initial generation"""
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
    
    case_id = test_case.get('case_id', 'test6_3')
    codebase_path = test_case.get('codebase_path', 'datasets/codebases/open62541')
    
    print("="*60, flush=True)
    print("Running Test6_3: Repair Order Analysis + First Fix Point Initial Generation")
    print("Configuration:")
    print("  ✓ Repair order analysis: ENABLED (via model API)")
    print("  ✓ First fix point initial generation: ENABLED")
    print("  ✗ Other fix points: SKIPPED")
    print("  ✗ Validation and feedback: SKIPPED")
    print("  ✗ Merging thinking chains: SKIPPED")
    print("="*60)
    print(f"Case ID: {case_id}")
    print(f"Bug Location: {test_case['bug_location']}")
    print(f"Project: {test_case['project']}")
    print(f"Codebase Path: {codebase_path}")
    print(f"Crash Type: {test_case['crash_type']}")
    print(f"Severity: {test_case['severity']}")
    
    # Print fix points from JSON for reference
    if 'fix_points' in test_case:
        print(f"\nFix Points in JSON ({len(test_case['fix_points'])} total) - for reference:")
        for fp in test_case['fix_points']:
            print(f"  {fp['id']}. {fp['file']}:{fp.get('function', 'N/A')} (lines {fp['line_start']}-{fp['line_end']})")
    
    print("\n" + "="*60)
    
    # Set environment to skip validation and merge, but allow initial fix
    os.environ['SKIP_VALIDATION'] = '1'
    os.environ['SKIP_MERGE'] = '1'
    os.environ['SKIP_LOCAL'] = '1'
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
        print("\nInitializing models...")
        print("  - Importing modules...")
        from core.initial_chain_builder import InitialChainBuilder
        from models.aliyun_model import AliyunModel
        from config import ALIYUN_API_KEY
        print("  - Modules imported successfully")
        
        print("  - Creating AliyunModel instance...")
        aliyun_model = AliyunModel(ALIYUN_API_KEY)
        print("  - AliyunModel created")
        
        print("  - Creating InitialChainBuilder instance...")
        chain_builder = InitialChainBuilder(aliyun_model, codebase_path)
        print("  - InitialChainBuilder created")
        print("✓ Models initialized successfully!")
        
        # Step 1: Analyze repair order using model API
        print("\n" + "="*60)
        print("Step 1: Analyzing repair order using model API...")
        print("="*60)
        print("Note: Model will analyze and generate fix points from buggy_code and bug_location")
        print("      fixed_code is NOT used in repair order analysis")
        print("      JSON fix_points are provided in bug_location for reference only")
        print("="*60)
        
        repair_order_start = time.time()
        print(f"  - Calling analyze_repair_order...", flush=True)
        print(f"  - Buggy code length: {len(test_case['buggy_code'])} chars", flush=True)
        print(f"  - Bug location length: {len(detailed_bug_location)} chars", flush=True)
        print(f"  - Starting API call (this may take 10-60 seconds)...", flush=True)
        fix_points = chain_builder.analyze_repair_order(
            test_case['buggy_code'],
            detailed_bug_location
        )
        print(f"  - analyze_repair_order returned {len(fix_points)} fix points", flush=True)
        repair_order_end = time.time()
        repair_order_duration = repair_order_end - repair_order_start
        
        print(f"\n✓ Model API analysis completed in {repair_order_duration:.2f} seconds")
        print(f"✓ Identified {len(fix_points)} fix point(s)")
        
        # Print fix points identified by model
        print("\n" + "="*60)
        print("Fix Points Identified by Model:")
        print("="*60)
        for fp in fix_points:
            print(f"\nFix Point {fp.get('id', 'N/A')}:")
            print(f"  Location: {fp.get('location', 'N/A')}")
            print(f"  Description: {fp.get('description', 'N/A')}")
        
        if not fix_points:
            print("\n⚠️  No fix points identified. Cannot proceed with initial fix generation.")
            return 1
        
        # Step 2: Generate initial fix for FIRST fix point only
        print("\n" + "="*60)
        print("Step 2: Generating initial fix for FIRST fix point only...")
        print("="*60)
        first_fix_point = fix_points[0]
        print(f"Processing Fix Point {first_fix_point.get('id', 'N/A')}:")
        print(f"  Location: {first_fix_point.get('location', 'N/A')}")
        print(f"  Description: {first_fix_point.get('description', 'N/A')[:100]}...")
        print("="*60)
        print("Note: Only the first fix point will be processed.")
        print("      Other fix points are skipped as requested.")
        print("="*60)
        
        # Extract fixed_code for this fix point if available (for validation only, not passed to model)
        ground_truth_fix = None
        if 'fixed_code' in test_case and isinstance(test_case['fixed_code'], dict):
            # Try to find corresponding fixed_code for this fix point
            # This is a simplified approach - in practice, you'd match by file/function
            # For now, we'll just use None (model shouldn't see ground truth anyway)
            pass
        
        # Build thinking chain for first fix point
        # Note: fixed_code is passed as None - model should not see the ground truth
        # ground_truth_fix can be used for validation but not passed to model
        initial_fix_start = time.time()
        print(f"\n  - Calling build_fix_point_chain for fix point {first_fix_point.get('id', 'N/A')}...", flush=True)
        print(f"  - Buggy code length: {len(test_case['buggy_code'])} chars", flush=True)
        print(f"  - Starting initial fix generation (this may take 30-120 seconds)...", flush=True)
        
        thinking_chain, final_fix_code = chain_builder.build_fix_point_chain(
            buggy_code=test_case['buggy_code'],
            fixed_code=None,  # Model should not see fixed_code
            fix_point=first_fix_point,
            ground_truth_fix=ground_truth_fix,  # Only for validation, not passed to model
            debug_info=None  # Can be set to list to collect debug info
        )
        
        initial_fix_end = time.time()
        initial_fix_duration = initial_fix_end - initial_fix_start
        
        print(f"\n✓ Initial fix generation completed in {initial_fix_duration:.2f} seconds")
        print(f"✓ Thinking chain length: {len(thinking_chain)} characters")
        if final_fix_code:
            print(f"✓ Final fix code generated: {len(final_fix_code)} characters")
        else:
            print("⚠️  No final fix code generated")
        
        # Print summary
        print("\n" + "="*60)
        print("Summary:")
        print("="*60)
        print(f"Repair Order Analysis:")
        print(f"  - Duration: {repair_order_duration:.2f} seconds")
        print(f"  - Fix points identified: {len(fix_points)}")
        print(f"\nFirst Fix Point Initial Generation:")
        print(f"  - Duration: {initial_fix_duration:.2f} seconds")
        print(f"  - Thinking chain length: {len(thinking_chain)} characters")
        print(f"  - Final fix code: {'Generated' if final_fix_code else 'Not generated'}")
        print(f"  - Total duration: {repair_order_duration + initial_fix_duration:.2f} seconds")
        
        # Save results
        output_dir = pathlib.Path('test') / case_id / 'outputs'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        results = {
            'case_id': case_id,
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
            },
            'extraction_method': 'model_api_analysis',
            'total_duration_seconds': repair_order_duration + initial_fix_duration,
            'created_at': datetime.now().isoformat(),
            'test_config': {
                'skip_initial_fix': False,  # We generated initial fix for first point
                'skip_validation': True,
                'skip_merge': True,
                'use_model_api': True,
                'json_fix_points_available': 'fix_points' in test_case,
                'only_first_fix_point': True,
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
        json_output = output_dir / 'thinking_chains' / f"{case_id}_first_fix_point.json"
        json_output.parent.mkdir(parents=True, exist_ok=True)
        with json_output.open('w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Save TXT summary
        txt_output = output_dir / 'thinking_chains' / f"{case_id}_first_fix_point.txt"
        with txt_output.open('w', encoding='utf-8') as f:
            f.write(f"Test6_3: Repair Order Analysis + First Fix Point Initial Generation\n")
            f.write("="*60 + "\n\n")
            f.write(f"Case ID: {case_id}\n")
            f.write(f"Created at: {datetime.now().isoformat()}\n\n")
            
            f.write("Repair Order Analysis:\n")
            f.write("-"*60 + "\n")
            f.write(f"Extraction Method: Model API Analysis\n")
            f.write(f"API Duration: {repair_order_duration:.2f} seconds\n")
            f.write(f"Total Fix Points: {len(fix_points)}\n\n")
            
            f.write("Fix Points Identified by Model:\n")
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
            f.write(f"Final Fix Code: {'Generated' if final_fix_code else 'Not generated'}\n\n")
            
            f.write("Thinking Chain:\n")
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
        
        print("\n" + "="*60)
        print("Results saved:")
        print(f"  - JSON: {json_output}")
        print(f"  - TXT: {txt_output}")
        print("="*60)
        
        return 0
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())


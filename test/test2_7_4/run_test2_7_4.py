"""
Run test2_7_4: Test with enhanced prompts (code format enforcement + enhanced grep encouragement + enhanced logging)
- Force return code format fixes (DIFF format with -/+ prefixes)
- Code format validation to reject text descriptions
- Enhanced grep logging with detailed information (command, path, line numbers)
- Explicitly extract and list actual vulnerability descriptions
- Enhanced grep prompts: model can use grep when needed (optional but encouraged)
- Enhanced response parsing with fallback
- Initial thinking chain only (no optimization)
- Response truncation detection
- Enhanced logging: clear stage markers and complete grep results/errors
- Increased CLOUD_MAX_TOKENS to 2048 to prevent truncation

Step-by-Step Debugging:
  Set environment variables to skip specific steps:
  - SKIP_REPAIR_ORDER=1: Skip repair order analysis (use existing fix_points if available)
  - SKIP_INITIAL_FIX=1: Skip initial fix generation (only do validation/iteration)
  - SKIP_VALIDATION=1: Skip validation and iteration (only generate initial fix)
  - SKIP_MERGE=1: Skip merging thinking chains (use simple concatenation instead)

Examples:
  # Only analyze repair order
  SKIP_INITIAL_FIX=1 SKIP_VALIDATION=1 SKIP_MERGE=1 python3 test/test2_7_4/run_test2_7_4.py

  # Only generate initial fixes (no validation, no merge)
  SKIP_REPAIR_ORDER=1 SKIP_VALIDATION=1 SKIP_MERGE=1 python3 test/test2_7_4/run_test2_7_4.py

  # Only do validation/iteration (skip initial fix generation and merge)
  SKIP_REPAIR_ORDER=1 SKIP_INITIAL_FIX=1 SKIP_MERGE=1 python3 test/test2_7_4/run_test2_7_4.py

  # Only merge thinking chains (skip all other steps)
  SKIP_REPAIR_ORDER=1 SKIP_INITIAL_FIX=1 SKIP_VALIDATION=1 python3 test/test2_7_4/run_test2_7_4.py
"""
import json
import pathlib
import sys
import os
import time

# Force unbuffered output for real-time logging
sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None
sys.stderr.reconfigure(line_buffering=True) if hasattr(sys.stderr, 'reconfigure') else None

# Add project root to Python path
project_root = pathlib.Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.repair_pipeline import RepairPipeline
from config import LOGS_DIR

def main():
    # Load test case
    test_file = pathlib.Path('test/test2_7_4/test2_7_4.json')
    if not test_file.exists():
        print(f"Error: Test file not found: {test_file}")
        return 1
    
    with test_file.open('r', encoding='utf-8') as f:
        test_case = json.load(f)
    
    # Override case_id for output files
    output_case_id = 'test2_7_4'
    
    print("="*60)
    print("Running Test2_7_4: open62541 use-after-free fix")
    print("(Test with ENHANCED prompts + enhanced logging + increased token limit)")
    print("Improvements:")
    print("  - Force return code format fixes (DIFF format with -/+ prefixes)")
    print("  - Code format validation to reject text descriptions")
    print("  - Enhanced grep logging with detailed information (command, path, line numbers)")
    print("  - Explicitly extract and list actual vulnerability descriptions")
    print("  - Enhanced grep prompts: model can use grep when needed (optional but encouraged)")
    print("  - Enhanced response parsing with fallback")
    print("  - Response truncation detection")
    print("  - Enhanced logging: clear stage markers (>>> ENTERING / <<< COMPLETED)")
    print("  - Complete grep results and error messages in logs")
    print("  - Increased CLOUD_MAX_TOKENS to 1024 (from 512) to prevent truncation")
    print("="*60)
    print(f"Case ID: {output_case_id}")
    print(f"Bug Location: {test_case['bug_location']}")
    print(f"Project: {test_case['project']}")
    print(f"Codebase Path: {test_case.get('codebase_path', 'N/A')}")
    print(f"Crash Type: {test_case['crash_type']}")
    print(f"Severity: {test_case['severity']}")
    
    # Print vulnerability locations
    if 'vulnerability_locations' in test_case:
        print(f"\nVulnerability Locations:")
        for i, loc in enumerate(test_case['vulnerability_locations'], 1):
            print(f"  {i}. {loc['file']}:{loc['function']} (lines {loc['line_start']}-{loc['line_end']})")
            print(f"     {loc['description']}")
    
    # Print affected files
    if 'affected_files' in test_case:
        print(f"\nAffected Files:")
        for file_info in test_case['affected_files']:
            print(f"  - {file_info['path']}")
            for func in file_info['functions']:
                print(f"    * {func['name']} (defined at line {func['line']})")
                if 'vulnerable_lines' in func:
                    print(f"      Vulnerable lines: {func['vulnerable_lines'][:5]}..." if len(func['vulnerable_lines']) > 5 else f"      Vulnerable lines: {func['vulnerable_lines']}")
    
    print("\n" + "="*60)
    
    # Get codebase path from test case
    codebase_path = test_case.get('codebase_path', '.')
    if codebase_path and os.path.exists(codebase_path):
        print(f"Using codebase: {codebase_path}")
    else:
        print(f"Warning: Codebase path '{codebase_path}' not found, using current directory")
        codebase_path = "."
    
    # Build detailed bug location string with file, function, and line info
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
    
    # Add vulnerability locations with descriptions (CRITICAL INFORMATION)
    if 'vulnerability_locations' in test_case:
        detailed_bug_location += "\n\nVulnerability Details:"
        for i, loc in enumerate(test_case['vulnerability_locations'], 1):
            detailed_bug_location += f"\n  {i}. {loc['file']}:{loc['function']} (lines {loc['line_start']}-{loc['line_end']})"
            detailed_bug_location += f"\n     Description: {loc['description']}"
    
    # Initialize pipeline (skip local model for initial chain only)
    try:
        # Set environment to skip local model
        os.environ['SKIP_LOCAL'] = '1'
        
        # Check for step-by-step debugging flags
        skip_repair_order = os.getenv("SKIP_REPAIR_ORDER", "0") == "1"
        skip_initial_fix = os.getenv("SKIP_INITIAL_FIX", "0") == "1"
        skip_validation = os.getenv("SKIP_VALIDATION", "0") == "1"
        skip_merge = os.getenv("SKIP_MERGE", "0") == "1"
        
        if skip_repair_order or skip_initial_fix or skip_validation or skip_merge:
            print("\n" + "="*60)
            print("Step-by-Step Debugging Mode Enabled:")
            print("="*60)
            if skip_repair_order:
                print("  ✓ SKIP_REPAIR_ORDER: Will skip repair order analysis")
            if skip_initial_fix:
                print("  ✓ SKIP_INITIAL_FIX: Will skip initial fix generation")
            if skip_validation:
                print("  ✓ SKIP_VALIDATION: Will skip validation and iteration")
            if skip_merge:
                print("  ✓ SKIP_MERGE: Will skip merging thinking chains (use concatenation)")
            print("="*60 + "\n")
        
        pipeline = RepairPipeline(codebase_path=codebase_path)
        
        # Process the test case (only initial chain)
        print("\nProcessing repair case (initial thinking chain only)...")
        print("="*60)
        overall_start_time = time.time()
        
        # We need to modify the pipeline to stop after initial chain
        # For now, we'll use the chain_builder directly
        from core.initial_chain_builder import InitialChainBuilder
        from models.aliyun_model import AliyunModel
        from config import ALIYUN_API_KEY
        
        aliyun_model = AliyunModel(ALIYUN_API_KEY)
        chain_builder = InitialChainBuilder(aliyun_model, codebase_path)
        
        # Step 1: Analyze repair order (unless skipped)
        if not skip_repair_order:
            fix_points = chain_builder.analyze_repair_order(
                test_case['buggy_code'],
                test_case['fixed_code'],
                detailed_bug_location
            )
            print(f"\nIdentified {len(fix_points)} fix points")
        else:
            # Load existing fix points from previous run if available
            print("\n" + "="*60)
            print("SKIP_REPAIR_ORDER enabled: Skipping repair order analysis")
            print("="*60)
            existing_chain_file = pathlib.Path('test') / output_case_id / 'outputs' / 'thinking_chains' / f"{output_case_id}_initial.json"
            if existing_chain_file.exists():
                print(f"Loading fix points from existing file: {existing_chain_file}")
                with existing_chain_file.open('r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    fix_points = existing_data.get('fix_points', [])
                    print(f"Loaded {len(fix_points)} fix points from existing file")
            else:
                print("No existing fix points found, extracting from bug_location...")
                fix_points = chain_builder.analyze_repair_order(
                    test_case['buggy_code'],
                    test_case['fixed_code'],
                    detailed_bug_location
                )
                print(f"Extracted {len(fix_points)} fix points from bug_location")
        
        # Step 2: Build thinking chains for each fix point
        print("\n" + "="*60)
        if skip_initial_fix:
            print("SKIP_INITIAL_FIX enabled: Will skip initial fix generation")
        if skip_validation:
            print("SKIP_VALIDATION enabled: Will skip validation and iteration")
        print("="*60)
        
        thinking_chains = {}
        final_fix_codes = {}  # Store final fix codes for each fix point
        fix_points_start_time = time.time()
        for i, fix_point in enumerate(fix_points, 1):
            # Ensure fix_point is a dict
            if isinstance(fix_point, str):
                fix_point = {'id': f'fix_point_{i}', 'location': fix_point, 'description': fix_point}
            elif not isinstance(fix_point, dict):
                fix_point = {'id': f'fix_point_{i}', 'location': str(fix_point), 'description': str(fix_point)}
            
            # Ensure required fields exist and normalize id format
            if 'id' not in fix_point:
                fix_point['id'] = f'fix_point_{i}'
            # Convert numeric id to string format for consistency
            if isinstance(fix_point['id'], int):
                fix_point['id'] = f'fix_point_{fix_point["id"]}'
            
            if 'location' not in fix_point:
                fix_point['location'] = fix_point.get('description', 'Unknown location')
            
            print(f"\nProcessing fix point {i}/{len(fix_points)}: {fix_point.get('description', fix_point.get('location', 'N/A'))[:60]}...")
            chain, final_fix = chain_builder.build_fix_point_chain(
                test_case['buggy_code'],
                test_case['fixed_code'],
                fix_point,
                ground_truth_fix=test_case['fixed_code']  # Pass fixed_code as ground truth for validation
            )
            # Use location as key (which is what merge_thinking_chains expects)
            thinking_chains[fix_point['location']] = chain
            final_fix_codes[fix_point['location']] = final_fix
        
        fix_points_end_time = time.time()
        fix_points_duration = fix_points_end_time - fix_points_start_time
        print(f"\n[Summary] All fix points processing completed in {fix_points_duration:.2f} seconds")
        
        # Step 3: Merge thinking chains (unless skipped)
        if not skip_merge:
            print("\nMerging thinking chains...")
            merged_chain = chain_builder.merge_thinking_chains(fix_points, thinking_chains, final_fix_codes)
        else:
            print("\n" + "="*60)
            print("SKIP_MERGE enabled: Skipping merging thinking chains")
            print("="*60)
            # Use simple concatenation
            merged_parts = []
            for i, fix_point in enumerate(fix_points, 1):
                location = fix_point.get('location', f'fix_point_{i}')
                chain = thinking_chains.get(location, "")
                if chain:
                    merged_parts.append(f"=== Fix Point {i}: {fix_point.get('description', location)[:60]} ===\n{chain}")
                if final_fix_codes and location in final_fix_codes and final_fix_codes[location]:
                    merged_parts.append(f"\n[Final Fix Code for Fix Point {i}]\n{final_fix_codes[location]}")
            merged_chain = "\n\n".join(merged_parts) if merged_parts else "\n\n".join(thinking_chains.values())
            print(f"Using simple concatenation: {len(merged_parts)} parts merged")
        
        overall_end_time = time.time()
        overall_duration = overall_end_time - overall_start_time
        print(f"\n[Summary] Overall processing completed in {overall_duration:.2f} seconds")
        
        # Save initial chain
        import json as json_lib
        from datetime import datetime
        
        output_data = {
            'case_id': output_case_id,
            'bug_location': detailed_bug_location,
            'fix_points': fix_points,
            'thinking_chains': thinking_chains,
            'final_fix_codes': final_fix_codes,  # Include final fix codes for each fix point
            'merged_chain': merged_chain,
            'metadata': {
                'codebase_path': codebase_path,
                'vulnerability_locations': test_case.get('vulnerability_locations', []),
                'affected_files': test_case.get('affected_files', []),
                'vulnerability_type': test_case.get('vulnerability_type'),
                'root_cause': test_case.get('root_cause'),
                'fix_goal': test_case.get('fix_goal'),
                'original_case_id': test_case['case_id'],
                'created_at': datetime.now().isoformat(),
                'improvements': 'Enhanced prompts: force code format fixes (DIFF format), code format validation, enhanced grep logging with detailed information (command, path, line numbers), explicitly extract actual vulnerability descriptions, enhanced grep prompts (optional but encouraged), response truncation detection, enhanced logging with clear stage markers, increased CLOUD_MAX_TOKENS to 1024'
            }
        }
        
        # Save JSON (using output_case_id) - save to test directory
        test_output_dir = pathlib.Path('test') / output_case_id / 'outputs' / 'thinking_chains'
        test_output_dir.mkdir(parents=True, exist_ok=True)
        json_file = test_output_dir / f"{output_case_id}_initial.json"
        with json_file.open('w', encoding='utf-8') as f:
            json_lib.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"✓ Saved initial chain (JSON): {json_file}")
        
        # Save TXT (using output_case_id) - save to test directory
        txt_file = test_output_dir / f"{output_case_id}_initial.txt"
        with txt_file.open('w', encoding='utf-8') as f:
            f.write(merged_chain.replace('\\n', '\n'))
        print(f"✓ Saved initial chain (TXT): {txt_file}")
        
        print("\n" + "="*60)
        print("Initial thinking chain generation completed!")
        print("="*60)
        print(f"\nOutput files:")
        print(f"  - Initial chain (JSON): {json_file}")
        print(f"  - Initial chain (TXT): {txt_file}")
        
        print("\n" + "="*60)
        print("Merged Thinking Chain Preview (first 800 chars):")
        print("="*60)
        preview = merged_chain[:800] + "..." if len(merged_chain) > 800 else merged_chain
        print(preview)
        
    except Exception as e:
        print(f"\nError running test: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())


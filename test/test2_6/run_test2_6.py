"""
Run test2_6: Initial thinking chain only (no optimization)
With detailed vulnerability location information and generalized prompts
Enhanced grep usage and detailed logging
"""
import json
import pathlib
import sys
import os
from core.repair_pipeline import RepairPipeline
from config import LOGS_DIR

def main():
    # Load test case
    test_file = pathlib.Path('test/test2_6/test2_6.json')
    if not test_file.exists():
        print(f"Error: Test file not found: {test_file}")
        return 1
    
    with test_file.open('r', encoding='utf-8') as f:
        test_case = json.load(f)
    
    print("="*60)
    print("Running Test2_6: open62541 use-after-free fix")
    print("With detailed vulnerability location information")
    print("Using generalized memory access vulnerability prompts")
    print("Enhanced grep usage and detailed stage logging")
    print("="*60)
    print(f"Case ID: {test_case['case_id']}")
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
        
        pipeline = RepairPipeline(codebase_path=codebase_path)
        
        # Process the test case (only initial chain)
        print("\nProcessing repair case (initial thinking chain only)...")
        print("="*60)
        
        # We need to modify the pipeline to stop after initial chain
        # For now, we'll use the chain_builder directly
        from core.initial_chain_builder import InitialChainBuilder
        from models.aliyun_model import AliyunModel
        from config import ALIYUN_API_KEY
        
        aliyun_model = AliyunModel(ALIYUN_API_KEY)
        chain_builder = InitialChainBuilder(aliyun_model, codebase_path)
        
        # Build initial thinking chain
        fix_points = chain_builder.analyze_repair_order(
            test_case['buggy_code'],
            test_case['fixed_code'],
            detailed_bug_location
        )
        
        print(f"\nIdentified {len(fix_points)} fix points")
        
        # Build thinking chains for each fix point
        thinking_chains = {}
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
            chain = chain_builder.build_fix_point_chain(
                test_case['buggy_code'],
                test_case['fixed_code'],
                fix_point
            )
            # Use location as key (which is what merge_thinking_chains expects)
            thinking_chains[fix_point['location']] = chain
        
        # Merge thinking chains
        print("\nMerging thinking chains...")
        merged_chain = chain_builder.merge_thinking_chains(fix_points, thinking_chains)
        
        # Save initial chain
        import json as json_lib
        from datetime import datetime
        from config import THINKING_CHAINS_DIR
        
        output_data = {
            'case_id': test_case['case_id'],
            'bug_location': detailed_bug_location,
            'fix_points': fix_points,
            'thinking_chains': thinking_chains,
            'merged_chain': merged_chain,
            'metadata': {
                'codebase_path': codebase_path,
                'vulnerability_locations': test_case.get('vulnerability_locations', []),
                'affected_files': test_case.get('affected_files', []),
                'vulnerability_type': test_case.get('vulnerability_type'),
                'root_cause': test_case.get('root_cause'),
                'fix_goal': test_case.get('fix_goal'),
                'created_at': datetime.now().isoformat()
            }
        }
        
        # Save JSON
        json_file = pathlib.Path(THINKING_CHAINS_DIR) / f"{test_case['case_id']}_initial.json"
        json_file.parent.mkdir(parents=True, exist_ok=True)
        with json_file.open('w', encoding='utf-8') as f:
            json_lib.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"✓ Saved initial chain (JSON): {json_file}")
        
        # Save TXT
        txt_file = pathlib.Path(THINKING_CHAINS_DIR) / f"{test_case['case_id']}_initial.txt"
        txt_file.parent.mkdir(parents=True, exist_ok=True)
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



#!/usr/bin/env python3
"""
Test6: Repair Order Analysis Only
- Directly extract fix points from JSON fix_points field
- Skip validation, optimization, and thinking chain merging
- Only determine the repair order
"""
import json
import os
import sys
import pathlib
import time
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))

from core.repair_pipeline import RepairPipeline


def main():
    """Run test6: Repair order analysis only"""
    
    # Load test case
    test_file = pathlib.Path(__file__).parent / 'test6.json'
    if not test_file.exists():
        print(f"Error: Test file not found: {test_file}")
        return 1
    
    with test_file.open('r', encoding='utf-8') as f:
        test_case = json.load(f)
    
    case_id = test_case.get('case_id', 'test6')
    codebase_path = test_case.get('codebase_path', 'datasets/codebases/open62541')
    
    print("="*60)
    print("Running Test6: Repair Order Analysis Only")
    print("Configuration:")
    print("  ✓ Repair order analysis: ENABLED (from JSON fix_points)")
    print("  ✗ Fix point processing: SKIPPED")
    print("  ✗ Validation and feedback: SKIPPED")
    print("  ✗ Merging thinking chains: SKIPPED")
    print("="*60)
    print(f"Case ID: {case_id}")
    print(f"Bug Location: {test_case['bug_location']}")
    print(f"Project: {test_case['project']}")
    print(f"Codebase Path: {codebase_path}")
    print(f"Crash Type: {test_case['crash_type']}")
    print(f"Severity: {test_case['severity']}")
    
    # Print fix points from JSON
    if 'fix_points' in test_case:
        print(f"\nFix Points from JSON ({len(test_case['fix_points'])} total):")
        for fp in test_case['fix_points']:
            print(f"  {fp['id']}. {fp['file']}:{fp.get('function', 'N/A')} (lines {fp['line_start']}-{fp['line_end']})")
    
    print("\n" + "="*60)
    
    # Set environment to skip everything except order analysis
    os.environ['SKIP_INITIAL_FIX'] = '1'
    os.environ['SKIP_VALIDATION'] = '1'
    os.environ['SKIP_MERGE'] = '1'
    os.environ['SKIP_LOCAL'] = '1'
    
    # Initialize pipeline
    try:
        pipeline = RepairPipeline(codebase_path=codebase_path)
        
        # Extract fix points directly from JSON
        print("\n" + "="*60)
        print("Extracting fix points from JSON...")
        print("="*60)
        
        if 'fix_points' in test_case and test_case['fix_points']:
            # Directly use fix_points from JSON (only location information)
            fix_points = []
            for fp in test_case['fix_points']:
                fix_point = {
                    'id': fp['id'],
                    'location': f"{fp['file']}:{fp.get('function', 'N/A')} (lines {fp['line_start']}-{fp['line_end']})",
                    'file': fp['file'],
                    'function': fp.get('function'),
                    'line_start': fp['line_start'],
                    'line_end': fp['line_end']
                }
                fix_points.append(fix_point)
            
            print(f"✓ Extracted {len(fix_points)} fix point(s) from JSON")
            print("\n" + "="*60)
            print("Fix Points (location information only):")
            print("="*60)
            for fp in fix_points:
                print(f"\nFix Point {fp['id']}:")
                print(f"  File: {fp['file']}")
                print(f"  Function: {fp.get('function', 'N/A')}")
                print(f"  Lines: {fp['line_start']}-{fp['line_end']}")
                print(f"  Location: {fp['location']}")
            
            # Print fixed_code information (if available)
            if 'fixed_code' in test_case and isinstance(test_case['fixed_code'], dict):
                print("\n" + "="*60)
                print("Fixed Code (by file, diff format):")
                print("="*60)
                for file_path, file_info in test_case['fixed_code'].items():
                    print(f"\nFile: {file_path}")
                    if 'diff' in file_info:
                        print(f"  Diff format available ({len(file_info['diff'])} chars)")
                    if 'changes' in file_info:
                        print(f"  Changes: {len(file_info['changes'])} location(s)")
                        for change in file_info['changes']:
                            print(f"    - Lines {change['line_start']}-{change['line_end']}: {change['operation']}")
            
            # Save results
            output_dir = pathlib.Path('test') / case_id / 'outputs'
            output_dir.mkdir(parents=True, exist_ok=True)
            
            results = {
                'case_id': case_id,
                'bug_location': test_case['bug_location'],
                'fix_points': fix_points,
                'extraction_method': 'direct_from_json',
                'total_fix_points': len(fix_points),
                'created_at': datetime.now().isoformat(),
                'test_config': {
                    'skip_initial_fix': True,
                    'skip_validation': True,
                    'skip_merge': True,
                    'only_order_analysis': True
                }
            }
            
            # Save JSON
            json_output = output_dir / 'thinking_chains' / f"{case_id}_order_analysis.json"
            json_output.parent.mkdir(parents=True, exist_ok=True)
            with json_output.open('w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            # Save TXT summary
            txt_output = output_dir / 'thinking_chains' / f"{case_id}_order_analysis.txt"
            with txt_output.open('w', encoding='utf-8') as f:
                f.write(f"Repair Order Analysis for {case_id}\n")
                f.write("="*60 + "\n\n")
                f.write(f"Total Fix Points: {len(fix_points)}\n")
                f.write(f"Extraction Method: Direct from JSON fix_points field\n\n")
                f.write("Fix Points (location information only):\n")
                f.write("-"*60 + "\n")
                for fp in fix_points:
                    f.write(f"\nFix Point {fp['id']}:\n")
                    f.write(f"  File: {fp['file']}\n")
                    f.write(f"  Function: {fp.get('function', 'N/A')}\n")
                    f.write(f"  Lines: {fp['line_start']}-{fp['line_end']}\n")
                    f.write(f"  Location: {fp['location']}\n")
                    f.write("\n")
                
                # Write fixed_code information
                if 'fixed_code' in test_case and isinstance(test_case['fixed_code'], dict):
                    f.write("\n" + "="*60 + "\n")
                    f.write("Fixed Code (by file, diff format):\n")
                    f.write("="*60 + "\n")
                    for file_path, file_info in test_case['fixed_code'].items():
                        f.write(f"\nFile: {file_path}\n")
                        f.write("-"*60 + "\n")
                        if 'diff' in file_info:
                            f.write(f"\nDiff:\n{file_info['diff']}\n")
                        if 'changes' in file_info:
                            f.write(f"\nChanges ({len(file_info['changes'])} location(s)):\n")
                            for change in file_info['changes']:
                                f.write(f"  Lines {change['line_start']}-{change['line_end']}: {change['operation']}\n")
                                if 'context' in change:
                                    f.write(f"    Context: {change['context']}\n")
                        f.write("\n")
            
            print("\n" + "="*60)
            print("Results saved:")
            print(f"  - JSON: {json_output}")
            print(f"  - TXT: {txt_output}")
            print("="*60)
            
            return 0
        else:
            print("Error: No 'fix_points' field found in JSON")
            return 1
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())


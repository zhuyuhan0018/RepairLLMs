#!/usr/bin/env python3
"""
Test8_6: Repair Order Analysis Only
- Use model API to analyze and sort repair order from JSON fix_points
- Skip all other stages (fix generation, validation, optimization, merge)
"""
import json
import os
import sys
import pathlib
import time
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))


def main():
    """Run test8_6: Repair order analysis only"""
    # Load test case (use test6.json)
    test_file = pathlib.Path(__file__).parent.parent / 'test6' / 'test6.json'
    if not test_file.exists():
        print(f"Error: Test file not found: {test_file}", flush=True)
        return 1
    
    with test_file.open('r', encoding='utf-8') as f:
        test_case = json.load(f)
    
    case_id = 'test8_6'
    original_case_id = test_case.get('case_id', 'test6')
    codebase_path = test_case.get('codebase_path', 'datasets/codebases/open62541')
    
    print("="*60, flush=True)
    print("Test8_6: Repair Order Analysis Only")
    print("Configuration:")
    print("  ✓ Repair order analysis: ENABLED (from JSON fix_points, sorted by LLM)")
    print("  ✗ Fix point generation: SKIPPED")
    print("  ✗ Validation: SKIPPED")
    print("  ✗ Optimization: SKIPPED")
    print("  ✗ Merging thinking chains: SKIPPED")
    print("="*60, flush=True)
    
    # Set environment: Skip all stages except repair order analysis
    os.environ['SKIP_VALIDATION'] = '1'
    os.environ['SKIP_MERGE'] = '1'
    os.environ['SKIP_INITIAL_FIX'] = '1'  # Skip fix generation
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
    
    # Initialize models
    try:
        from core.initial_chain_builder import InitialChainBuilder
        from models.aliyun_model import AliyunModel
        from config import ALIYUN_API_KEY
        
        aliyun_model = AliyunModel(ALIYUN_API_KEY)
        chain_builder = InitialChainBuilder(aliyun_model, codebase_path)
        
        # Analyze repair order
        print("\nAnalyzing repair order...", flush=True)
        repair_order_start = time.time()
        fix_points = chain_builder.analyze_repair_order(
            test_case['buggy_code'],
            detailed_bug_location,
            fix_points=test_case.get('fix_points')
        )
        repair_order_end = time.time()
        repair_order_duration = repair_order_end - repair_order_start
        
        # Print summary
        print("\n" + "="*60, flush=True)
        print("Summary:", flush=True)
        print("="*60, flush=True)
        print(f"Duration: {repair_order_duration:.2f} seconds", flush=True)
        print(f"Fix points identified: {len(fix_points)}", flush=True)
        if 'fix_points' in test_case:
            print(f"JSON fix points: {len(test_case['fix_points'])}", flush=True)
            print(f"Identification rate: {len(fix_points)}/{len(test_case['fix_points'])} = {len(fix_points)/len(test_case['fix_points'])*100:.1f}%", flush=True)
        
        # Print sorted fix points
        print("\nSorted Fix Points (by LLM):", flush=True)
        for i, fp in enumerate(fix_points, 1):
            print(f"  {i}. {fp.get('location', 'N/A')}", flush=True)
        
        # Save results - use test8_6 directory for outputs
        output_dir = pathlib.Path('test') / 'test8_6' / 'outputs'
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
            'extraction_method': 'model_api_analysis',
            'total_duration_seconds': repair_order_duration,
            'created_at': datetime.now().isoformat(),
            'test_config': {
                'skip_initial_fix': True,
                'skip_validation': True,
                'skip_merge': True,
                'use_model_api': True,
                'json_fix_points_available': 'fix_points' in test_case,
                'only_repair_order_analysis': True,
                'optimization_enabled': False,
            },
        }
        
        # Add comparison data if JSON fix_points available
        if 'fix_points' in test_case and test_case['fix_points']:
            results['comparison'] = {
                'json_fix_points_count': len(test_case['fix_points']),
                'model_fix_points_count': len(fix_points),
                'identification_rate': len(fix_points) / len(test_case['fix_points']) if test_case['fix_points'] else 0,
                'json_fix_points': test_case['fix_points']
            }
        
        # Save JSON
        json_output = output_dir / 'thinking_chains' / f"test8_6_repair_order_analysis.json"
        json_output.parent.mkdir(parents=True, exist_ok=True)
        with json_output.open('w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Save TXT summary
        txt_output = output_dir / 'thinking_chains' / f"test8_6_repair_order_analysis.txt"
        with txt_output.open('w', encoding='utf-8') as f:
            f.write("="*60 + "\n")
            f.write("Test8_6: Repair Order Analysis Only (with improved sorting)\n")
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
            if 'fix_points' in test_case:
                f.write(f"JSON Fix Points (for reference): {len(test_case['fix_points'])}\n")
                f.write(f"Identification Rate: {len(fix_points)}/{len(test_case['fix_points'])} = {len(fix_points)/len(test_case['fix_points'])*100:.1f}%\n")
            f.write("-"*60 + "\n")
            
            for i, fp in enumerate(fix_points, 1):
                f.write(f"\nFix Point {i}:\n")
                f.write(f"  Location: {fp.get('location', 'N/A')}\n")
                f.write(f"  Description: {fp.get('description', 'N/A')}\n")
            
            if 'fix_points' in test_case and test_case['fix_points']:
                f.write("\n" + "="*60 + "\n")
                f.write("Comparison: Model vs JSON\n")
                f.write("="*60 + "\n")
                f.write(f"Model identified: {len(fix_points)} fix point(s)\n")
                f.write(f"JSON contains: {len(test_case['fix_points'])} fix point(s)\n")
                f.write(f"Identification Rate: {len(fix_points)/len(test_case['fix_points'])*100:.1f}%\n")
                
                f.write("\nJSON Fix Points (for reference):\n")
                f.write("-"*60 + "\n")
                for fp in test_case['fix_points']:
                    f.write(f"\nFix Point {fp['id']}:\n")
                    f.write(f"  File: {fp['file']}\n")
                    f.write(f"  Function: {fp.get('function', 'N/A')}\n")
                    f.write(f"  Lines: {fp['line_start']}-{fp['line_end']}\n")
        
        print(f"\nResults saved to: {json_output.parent}", flush=True)
        
        return 0
    except Exception as e:
        print(f"Error: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())


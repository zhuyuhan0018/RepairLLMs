#!/usr/bin/env python3
"""
Test9: Repair Order Analysis + All Fix Points Initial Generation
- Use model API to analyze and sort repair order from JSON fix_points
- Generate initial fix for ALL fix points
- Skip validation, optimization, and merging
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
    """Run test9: Repair order analysis + all fix points initial generation"""
    # Load test case (use test6.json)
    test_file = pathlib.Path(__file__).parent.parent / 'test6' / 'test6.json'
    if not test_file.exists():
        print(f"Error: Test file not found: {test_file}", flush=True)
        return 1
    
    with test_file.open('r', encoding='utf-8') as f:
        test_case = json.load(f)
    
    case_id = 'test9'
    original_case_id = test_case.get('case_id', 'test6')
    codebase_path = test_case.get('codebase_path', 'datasets/codebases/open62541')
    
    print("="*60, flush=True)
    print("Test9: Repair Order Analysis + All Fix Points Initial Generation")
    print("Configuration:")
    print("  ✓ Repair order analysis: ENABLED (from JSON fix_points, sorted by LLM)")
    print("  ✓ All fix points initial generation: ENABLED")
    print("  ✗ Validation: SKIPPED")
    print("  ✗ Optimization: SKIPPED")
    print("  ✗ Merging thinking chains: SKIPPED")
    print("="*60, flush=True)
    
    # Set environment: Skip validation and merge, but NOT initial fix generation
    os.environ['SKIP_VALIDATION'] = '1'
    os.environ['SKIP_MERGE'] = '1'
    # DO NOT set SKIP_INITIAL_FIX - we want to generate initial fix for all fix points
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
        
        # Step 1: Analyze repair order
        print("\nAnalyzing repair order...", flush=True)
        repair_order_start = time.time()
        fix_points = chain_builder.analyze_repair_order(
            test_case['buggy_code'],
            detailed_bug_location,
            fix_points=test_case.get('fix_points')
        )
        repair_order_end = time.time()
        repair_order_duration = repair_order_end - repair_order_start
        
        if not fix_points:
            print("\n⚠️  No fix points identified. Cannot proceed with initial fix generation.", flush=True)
            return 1
        
        # Step 2: Generate initial fix for ALL fix points
        print(f"\nGenerating initial fix for {len(fix_points)} fix points...", flush=True)
        
        all_thinking_chains = {}
        all_final_fix_codes = {}
        all_fix_point_results = []
        total_initial_fix_duration = 0
        
        for i, fix_point in enumerate(fix_points):
            print(f"\nProcessing Fix Point {i+1}/{len(fix_points)}: {fix_point.get('location', 'N/A')}", flush=True)
            
            fix_point_start = time.time()
            thinking_chain, final_fix_code = chain_builder.build_fix_point_chain(
                buggy_code=test_case['buggy_code'],
                fixed_code=None,  # Model should not see fixed_code
                fix_point=fix_point,
                fixed_code_dict=None,  # No validation in test9
                debug_info=None,
                all_fix_points=fix_points,  # Pass all fix points from repair order analysis
                current_fix_point_index=i  # Pass current index (0-based)
            )
            fix_point_end = time.time()
            fix_point_duration = fix_point_end - fix_point_start
            total_initial_fix_duration += fix_point_duration
            
            # Store results
            location_key = fix_point.get('location', f"fix_point_{i}")
            all_thinking_chains[location_key] = thinking_chain
            all_final_fix_codes[location_key] = final_fix_code
            
            all_fix_point_results.append({
                'fix_point': fix_point,
                'thinking_chain': thinking_chain,
                'final_fix_code': final_fix_code,
                'duration_seconds': fix_point_duration,
                'thinking_chain_length': len(thinking_chain),
                'fix_code_length': len(final_fix_code) if final_fix_code else 0,
            })
        
        # Print summary
        print("\n" + "="*60, flush=True)
        print("Summary:", flush=True)
        print("="*60, flush=True)
        print(f"Repair Order Analysis:")
        print(f"  - Duration: {repair_order_duration:.2f} seconds", flush=True)
        print(f"  - Fix points identified: {len(fix_points)}", flush=True)
        if 'fix_points' in test_case:
            print(f"  - Identification rate: {len(fix_points)}/{len(test_case['fix_points'])} = {len(fix_points)/len(test_case['fix_points'])*100:.1f}%", flush=True)
        
        print(f"\nAll Fix Points Initial Generation:")
        print(f"  - Total duration: {total_initial_fix_duration:.2f} seconds", flush=True)
        print(f"  - Average per fix point: {total_initial_fix_duration/len(fix_points):.2f} seconds", flush=True)
        print(f"  - Fix points processed: {len(fix_points)}", flush=True)
        
        print(f"\nTotal Duration: {repair_order_duration + total_initial_fix_duration:.2f} seconds", flush=True)
        
        # Save results
        output_dir = pathlib.Path('test') / 'test9' / 'outputs'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        results = {
            'case_id': case_id,
            'original_case_id': original_case_id,
            'bug_location': detailed_bug_location,
            'repair_order_analysis': {
                'fix_points': fix_points,
                'total_fix_points': len(fix_points),
                'api_duration_seconds': repair_order_duration,
            },
            'initial_fix_generation': {
                'thinking_chains': all_thinking_chains,
                'final_fix_codes': all_final_fix_codes,
                'fix_point_results': all_fix_point_results,
                'total_duration_seconds': total_initial_fix_duration,
                'average_duration_per_fix_point': total_initial_fix_duration / len(fix_points) if fix_points else 0,
            },
            'extraction_method': 'model_api_analysis',
            'total_duration_seconds': repair_order_duration + total_initial_fix_duration,
            'created_at': datetime.now().isoformat(),
            'test_config': {
                'skip_initial_fix': False,
                'skip_validation': True,
                'skip_merge': True,
                'use_model_api': True,
                'json_fix_points_available': 'fix_points' in test_case,
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
        json_output = output_dir / 'thinking_chains' / f"test9_all_fix_points.json"
        json_output.parent.mkdir(parents=True, exist_ok=True)
        with json_output.open('w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Save TXT summary
        txt_output = output_dir / 'thinking_chains' / f"test9_all_fix_points.txt"
        with txt_output.open('w', encoding='utf-8') as f:
            f.write("="*60 + "\n")
            f.write("Test9: Repair Order Analysis + All Fix Points Initial Generation\n")
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
                f.write(f"JSON Fix Points: {len(test_case['fix_points'])}\n")
                f.write(f"Identification Rate: {len(fix_points)}/{len(test_case['fix_points'])} = {len(fix_points)/len(test_case['fix_points'])*100:.1f}%\n")
            f.write("-"*60 + "\n")
            
            for i, fp in enumerate(fix_points, 1):
                f.write(f"\nFix Point {i}:\n")
                f.write(f"  Location: {fp.get('location', 'N/A')}\n")
                f.write(f"  Description: {fp.get('description', 'N/A')}\n")
            
            f.write("\n" + "="*60 + "\n")
            f.write("Initial Fix Generation:\n")
            f.write("-"*60 + "\n")
            f.write(f"Total Duration: {total_initial_fix_duration:.2f} seconds\n")
            f.write(f"Average per Fix Point: {total_initial_fix_duration/len(fix_points):.2f} seconds\n")
            f.write(f"Fix Points Processed: {len(fix_points)}\n")
            f.write("-"*60 + "\n")
            
            for i, result in enumerate(all_fix_point_results, 1):
                fp = result['fix_point']
                f.write(f"\nFix Point {i} ({fp.get('id', 'N/A')}):\n")
                f.write(f"  Location: {fp.get('location', 'N/A')}\n")
                f.write(f"  Duration: {result['duration_seconds']:.2f} seconds\n")
                f.write(f"  Thinking Chain Length: {result['thinking_chain_length']} chars\n")
                f.write(f"  Fix Code Length: {result['fix_code_length']} chars\n")
                if result['final_fix_code']:
                    f.write(f"  Fix Code Generated: Yes\n")
                else:
                    f.write(f"  Fix Code Generated: No\n")
        
        print(f"\nResults saved to: {json_output.parent}", flush=True)
        
        return 0
    except Exception as e:
        print(f"Error: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())


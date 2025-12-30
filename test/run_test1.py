#!/usr/bin/env python3
"""
Test script for test1 - harfbuzz buffer overflow fix
"""
import sys
import os
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.repair_pipeline import RepairPipeline

def main():
    # Load test case
    test_file = Path(__file__).parent / "test1.json"
    with open(test_file, 'r', encoding='utf-8') as f:
        test_data = json.load(f)
    
    print("="*60)
    print("Test 1: harfbuzz Buffer Overflow Fix")
    print("="*60)
    print(f"Project: {test_data['project']}")
    print(f"Crash Type: {test_data['crash_type']}")
    print(f"Severity: {test_data['severity']}")
    print(f"Bug Location: {test_data['bug_location']}")
    print(f"Description: {test_data['description']}")
    print("\n" + "="*60)
    print("Buggy Code:")
    print("="*60)
    print(test_data['buggy_code'])
    print("\n" + "="*60)
    print("Fixed Code:")
    print("="*60)
    print(test_data['fixed_code'])
    print("\n" + "="*60)
    print("Starting Repair Pipeline...")
    print("="*60 + "\n")
    
    # Initialize pipeline
    try:
        pipeline = RepairPipeline(codebase_path=".")
        
        # Process the repair case
        result = pipeline.process_repair_case(
            buggy_code=test_data['buggy_code'],
            fixed_code=test_data['fixed_code'],
            bug_location=test_data['bug_location'],
            case_id=test_data['case_id']
        )
        
        print("\n" + "="*60)
        print("Test Completed Successfully!")
        print("="*60)
        print(f"\nInitial thinking chain saved to: outputs/thinking_chains/{test_data['case_id']}_initial.json")
        print(f"Optimized thinking chain saved to: outputs/optimized_chains/{test_data['case_id']}_optimized.json")
        
        print("\n" + "="*60)
        print("Optimized Thinking Chain Preview:")
        print("="*60)
        print(result['optimized_chain'][:500] + "..." if len(result['optimized_chain']) > 500 else result['optimized_chain'])
        
        return 0
        
    except Exception as e:
        print(f"\nError during test execution: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())


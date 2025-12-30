"""
Test case 1: Buffer overflow fix from harfbuzz project
Using patch file: datasets/testdata/patches/buffer_overflow/42470093.patch
"""
import sys
import os
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.repair_pipeline import RepairPipeline


def extract_code_from_patch(patch_path: str):
    """
    Extract buggy and fixed code from patch file
    """
    with open(patch_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find the diff section
    buggy_code = ""
    fixed_code = ""
    in_diff = False
    context_before = []
    
    for i, line in enumerate(lines):
        if line.startswith('diff --git'):
            in_diff = True
            continue
        
        if in_diff and line.startswith('@@'):
            # Extract line numbers
            continue
        
        if in_diff and line.startswith('---'):
            continue
        
        if in_diff and line.startswith('+++'):
            continue
        
        if in_diff:
            if line.startswith('-') and not line.startswith('---'):
                # Buggy code (removed line)
                buggy_code += line[1:]  # Remove '-' prefix
            elif line.startswith('+') and not line.startswith('+++'):
                # Fixed code (added line)
                fixed_code += line[1:]  # Remove '+' prefix
            elif line.startswith(' '):
                # Context line
                context_before.append(line[1:])
    
    # Build full context for buggy and fixed code
    # Include surrounding context
    full_buggy = "".join(context_before[:2]) + buggy_code + "".join(context_before[2:])
    full_fixed = "".join(context_before[:2]) + fixed_code + "".join(context_before[2:])
    
    return full_buggy.strip(), full_fixed.strip()


def main():
    """Run test case 1"""
    print("="*60)
    print("Test Case 1: Buffer Overflow Fix (harfbuzz)")
    print("="*60)
    
    # Path to patch file
    patch_path = Path(__file__).parent.parent / "datasets/testdata/patches/buffer_overflow/42470093.patch"
    
    if not patch_path.exists():
        print(f"Error: Patch file not found at {patch_path}")
        return
    
    print(f"\nReading patch from: {patch_path}")
    
    # Extract code from patch
    buggy_code, fixed_code = extract_code_from_patch(str(patch_path))
    
    print("\nBuggy Code:")
    print("-" * 60)
    print(buggy_code)
    print("\nFixed Code:")
    print("-" * 60)
    print(fixed_code)
    
    # Bug location
    bug_location = "src/hb-dsalgs.hh:492 (hb_auto_t constructor)"
    
    # Initialize pipeline
    print("\n" + "="*60)
    print("Initializing Repair Pipeline...")
    print("="*60)
    
    try:
        pipeline = RepairPipeline(codebase_path=".")
        
        # Process the repair case
        print("\n" + "="*60)
        print("Processing Repair Case...")
        print("="*60)
        
        result = pipeline.process_repair_case(
            buggy_code=buggy_code,
            fixed_code=fixed_code,
            bug_location=bug_location,
            case_id="test1_42470093"
        )
        
        # Save result summary
        output_dir = Path(__file__).parent.parent / "outputs"
        output_dir.mkdir(exist_ok=True)
        
        summary_path = output_dir / "test1_summary.json"
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump({
                'case_id': result['case_id'],
                'bug_location': result['bug_location'],
                'fix_points_count': len(result['fix_points']),
                'initial_chain_length': len(result['initial_chain']),
                'optimized_chain_length': len(result['optimized_chain']),
                'fix_points': result['fix_points']
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Test completed successfully!")
        print(f"✓ Summary saved to: {summary_path}")
        print(f"✓ Full thinking chains saved to outputs/thinking_chains/ and outputs/optimized_chains/")
        
        # Print a snippet of the optimized chain
        print("\n" + "="*60)
        print("Optimized Thinking Chain (first 500 chars):")
        print("="*60)
        print(result['optimized_chain'][:500] + "...")
        
    except Exception as e:
        print(f"\n✗ Error during processing: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())


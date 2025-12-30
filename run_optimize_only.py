"""
Run optimization only: Use local model to optimize high perplexity segments
"""
import json
import pathlib
import sys
from models.local_model import LocalModel
from core.perplexity_optimizer import PerplexityOptimizer
from config import LOCAL_MODEL_PATH, THINKING_CHAINS_DIR, OPTIMIZED_CHAINS_DIR

def main():
    case_id = 'test1'
    input_file = pathlib.Path(THINKING_CHAINS_DIR) / f"{case_id}_initial.json"
    output_file = pathlib.Path(OPTIMIZED_CHAINS_DIR) / f"{case_id}_optimized.json"
    
    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}")
        return 1

    print("="*60)
    print("Running Optimization Only")
    print("="*60)
    print(f"Input: {input_file}")
    print(f"Output: {output_file}")
    print("\n" + "="*60)
    
    # Load initial chain
    with input_file.open('r', encoding='utf-8') as f:
        data = json.load(f)
    
    thinking_chain = data.get('thinking_chain', '')
    print(f"Loaded initial chain: {len(thinking_chain)} characters")
    
    # Load local model
    print("\nLoading local model (this may take time)...")
    try:
        local_model = LocalModel(LOCAL_MODEL_PATH)
        print("✓ Local model loaded")
    except Exception as e:
        print(f"✗ Error loading local model: {e}")
        return 1

    # Initialize optimizer
    optimizer = PerplexityOptimizer(local_model)

    # Optimize thinking chain
    print("\n" + "="*60)
    print("Step 1: Analyzing perplexity...")
    print("="*60)
    perplexity_results = optimizer.analyze_perplexity(thinking_chain)
    high_segments = optimizer.identify_high_perplexity_segments(perplexity_results)
    print(f"Found {len(high_segments)} high perplexity segments")
    
    print("\n" + "="*60)
    print("Step 2: Optimizing high perplexity segments (using local model)...")
    print("="*60)
    print("(This will preserve critical parts like code fixes)")
    
    try:
        optimized_chain = optimizer.optimize_thinking_chain(thinking_chain)

    # Preserve critical parts
    final_chain = optimizer.preserve_critical_parts(thinking_chain, optimized_chain)

        print(f"\n✓ Optimization completed")
        print(f"  Original length: {len(thinking_chain)} characters")
        print(f"  Optimized length: {len(final_chain)} characters")
        
    except Exception as e:
        print(f"\n✗ Error during optimization: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Save result
    output_file.parent.mkdir(parents=True, exist_ok=True)
    result = {
        'case_id': case_id,
        'bug_location': data.get('bug_location'),
        'fix_points': data.get('fix_points'),
        'thinking_chain': final_chain,
        'original_chain': thinking_chain,
        'high_perplexity_segments_count': len(high_segments),
        'note': 'Optimized using local model (qwen2-5-32b-instruct)'
    }
    
    with output_file.open('w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print("\n" + "="*60)
    print("Optimization completed successfully!")
    print("="*60)
    print(f"\nOutput saved to: {output_file}")
    print(f"\nPreview (first 500 chars of optimized chain):")
    print("-" * 60)
    print(final_chain[:500] + "..." if len(final_chain) > 500 else final_chain)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

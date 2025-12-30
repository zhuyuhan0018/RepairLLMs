"""
Main Pipeline for Reverse-Engineered Reasoning Code Repair
"""
import json
import os
import os
from typing import Dict, Optional
from datetime import datetime
from models.aliyun_model import AliyunModel
from models.local_model import LocalModel
from core.initial_chain_builder import InitialChainBuilder
from core.perplexity_optimizer import PerplexityOptimizer
from config import (
    LOCAL_MODEL_PATH, ALIYUN_API_KEY,
    THINKING_CHAINS_DIR, OPTIMIZED_CHAINS_DIR
)


class RepairPipeline:
    """Main pipeline for code repair with reverse-engineered reasoning"""
    
    def __init__(self, codebase_path: str = "."):
        """
        Initialize pipeline
        
        Args:
            codebase_path: Path to codebase root
        """
        self.codebase_path = codebase_path
        skip_local = os.getenv("SKIP_LOCAL", "").lower() in ("1", "true", "yes")
        
        # Initialize models
        print("Initializing models...")
        self.aliyun_model = AliyunModel(ALIYUN_API_KEY)
        
        if skip_local:
            print("SKIP_LOCAL enabled: skipping local model and perplexity optimizer.")
            self.local_model = None
            self.optimizer = None
        else:
            self.local_model = LocalModel(LOCAL_MODEL_PATH)
            self.optimizer = PerplexityOptimizer(self.local_model)
        
        # Initialize components
        self.chain_builder = InitialChainBuilder(self.aliyun_model, codebase_path)
        
        print("Pipeline initialized successfully!")
    
    def process_repair_case(self,
                           buggy_code: str,
                           fixed_code: str,
                           bug_location: str,
                           case_id: Optional[str] = None) -> Dict:
        """
        Process a single repair case
        
        Args:
            buggy_code: Original buggy code
            fixed_code: Fixed code
            bug_location: Location of the bug
            case_id: Optional case identifier
            
        Returns:
            Dictionary containing the complete thinking chain and metadata
        """
        if case_id is None:
            case_id = f"case_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        print(f"\n{'='*60}")
        print(f"Processing repair case: {case_id}")
        print(f"Bug Location: {bug_location}")
        print(f"{'='*60}\n")
        
        # Step 1: Analyze repair order
        print("Step 1: Analyzing repair order...")
        fix_points = self.chain_builder.analyze_repair_order(
            buggy_code, fixed_code, bug_location
        )
        print(f"Identified {len(fix_points)} fix points")
        
        # Step 2: Build thinking chain for each fix point
        print("\nStep 2: Building thinking chains for each fix point...")
        thinking_chains = {}
        final_fix_codes = {}
        
        for fix_point in fix_points:
            print(f"\n  Processing fix point {fix_point['id']}: {fix_point['description']}")
            
            # Extract relevant code for this fix point
            # (In practice, you'd extract the specific code section)
            fix_point_buggy = buggy_code  # Simplified
            fix_point_fixed = fixed_code  # Simplified
            
            chain, final_fix = self.chain_builder.build_fix_point_chain(
                fix_point_buggy,
                fix_point_fixed,
                fix_point,
                ground_truth_fix=fix_point_fixed
            )
            
            thinking_chains[fix_point['location']] = chain
            final_fix_codes[fix_point['location']] = final_fix
            print(f"  ✓ Completed thinking chain for {fix_point['location']}")
        
        # Step 3: Merge thinking chains
        print("\nStep 3: Merging thinking chains...")
        initial_chain = self.chain_builder.merge_thinking_chains(
            fix_points, thinking_chains, final_fix_codes
        )
        print("✓ Merged thinking chains")
        
        # Save initial chain
        initial_chain_path = os.path.join(
            THINKING_CHAINS_DIR, f"{case_id}_initial.json"
        )
        self._save_thinking_chain(initial_chain_path, {
            'case_id': case_id,
            'bug_location': bug_location,
            'fix_points': fix_points,
            'thinking_chain': initial_chain,
            'individual_chains': thinking_chains
        })
        print(f"✓ Saved initial chain to {initial_chain_path}")
        
        # Save initial chain as TXT
        initial_chain_txt_path = os.path.join(
            THINKING_CHAINS_DIR, f"{case_id}_initial.txt"
        )
        with open(initial_chain_txt_path, 'w', encoding='utf-8') as f:
            f.write(initial_chain.replace('\\n', '\n'))
        print(f"✓ Saved initial chain (TXT) to {initial_chain_txt_path}")
        
        # Step 4: Optimize using perplexity
        if self.optimizer is None:
            print("\nStep 4 skipped (SKIP_LOCAL enabled). Using initial chain as final.")
            final_chain = initial_chain
        else:
            print("\nStep 4: Optimizing thinking chain using perplexity...")
            optimized_chain = self.optimizer.optimize_thinking_chain(
                initial_chain, self.aliyun_model
            )
            
            # Preserve critical parts
            final_chain = self.optimizer.preserve_critical_parts(
                initial_chain, optimized_chain
            )
            print("✓ Optimized thinking chain")
        
        # Save optimized (or initial) chain
        optimized_chain_path = os.path.join(
            OPTIMIZED_CHAINS_DIR, f"{case_id}_optimized.json"
        )
        self._save_thinking_chain(optimized_chain_path, {
            'case_id': case_id,
            'bug_location': bug_location,
            'fix_points': fix_points,
            'thinking_chain': final_chain,
            'original_chain': initial_chain
        })
        print(f"✓ Saved optimized chain to {optimized_chain_path}")
        
        # Save optimized chain as TXT
        optimized_chain_txt_path = os.path.join(
            OPTIMIZED_CHAINS_DIR, f"{case_id}_optimized.txt"
        )
        with open(optimized_chain_txt_path, 'w', encoding='utf-8') as f:
            f.write(final_chain.replace('\\n', '\n'))
        print(f"✓ Saved optimized chain (TXT) to {optimized_chain_txt_path}")
        
        return {
            'case_id': case_id,
            'bug_location': bug_location,
            'fix_points': fix_points,
            'initial_chain': initial_chain,
            'optimized_chain': final_chain,
            'individual_chains': thinking_chains
        }
    
    def _save_thinking_chain(self, path: str, data: Dict):
        """Save thinking chain to JSON file"""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def batch_process(self, repair_cases: list) -> list:
        """
        Process multiple repair cases
        
        Args:
            repair_cases: List of dictionaries with 'buggy_code', 'fixed_code', 
                         'bug_location', and optional 'case_id'
        
        Returns:
            List of results
        """
        results = []
        
        for i, case in enumerate(repair_cases):
            print(f"\n\nProcessing case {i+1}/{len(repair_cases)}")
            try:
                result = self.process_repair_case(
                    case['buggy_code'],
                    case['fixed_code'],
                    case['bug_location'],
                    case.get('case_id', f"case_{i+1}")
                )
                results.append(result)
            except Exception as e:
                print(f"Error processing case {i+1}: {e}")
                results.append({
                    'error': str(e),
                    'case_id': case.get('case_id', f"case_{i+1}")
                })
        
        return results


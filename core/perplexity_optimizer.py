"""
Perplexity-based Thinking Chain Optimizer
Optimizes thinking chains by replacing high perplexity segments
"""
import re
from typing import List, Tuple, Dict
from models.local_model import LocalModel
from utils.prompts import PromptTemplates
from config import PERPLEXITY_THRESHOLD, MIN_REPLACEMENT_LENGTH


class PerplexityOptimizer:
    """Optimizes thinking chains using perplexity analysis"""
    
    def __init__(self, local_model: LocalModel):
        """
        Initialize optimizer
        
        Args:
            local_model: Local model instance for perplexity computation
        """
        self.local_model = local_model
    
    def segment_thinking_chain(self, thinking_chain: str, 
                               segment_length: int = 200) -> List[Tuple[str, int, int]]:
        """
        Segment thinking chain into chunks for analysis
        
        Args:
            thinking_chain: Complete thinking chain
            segment_length: Approximate length of each segment in characters
            
        Returns:
            List of (segment_text, start_idx, end_idx) tuples
        """
        segments = []
        start = 0
        
        # Try to segment at natural boundaries (sentences, paragraphs)
        while start < len(thinking_chain):
            end = min(start + segment_length, len(thinking_chain))
            
            # Try to extend to sentence boundary
            if end < len(thinking_chain):
                # Look for sentence endings
                sentence_endings = ['. ', '.\n', '! ', '!\n', '? ', '?\n']
                for ending in sentence_endings:
                    pos = thinking_chain.rfind(ending, start, end + 50)
                    if pos != -1:
                        end = pos + len(ending)
                        break
                
                # Look for paragraph boundaries
                if '\n\n' in thinking_chain[start:end + 100]:
                    para_pos = thinking_chain.find('\n\n', start, end + 100)
                    if para_pos != -1:
                        end = para_pos + 2
            
            segment = thinking_chain[start:end].strip()
            if segment:
                segments.append((segment, start, end))
            
            start = end
        
        return segments
    
    def analyze_perplexity(self, thinking_chain: str) -> List[Tuple[str, float, int, int]]:
        """
        Analyze perplexity of thinking chain segments
        
        Args:
            thinking_chain: Thinking chain to analyze
            
        Returns:
            List of (segment, perplexity, start_idx, end_idx) tuples
        """
        segments = self.segment_thinking_chain(thinking_chain)
        results = []
        
        for segment, start, end in segments:
            try:
                perplexity = self.local_model.compute_perplexity(segment)
                results.append((segment, perplexity, start, end))
            except Exception as e:
                print(f"Error computing perplexity for segment: {e}")
                # Assign high perplexity on error
                results.append((segment, PERPLEXITY_THRESHOLD + 1.0, start, end))
        
        return results
    
    def identify_high_perplexity_segments(self, 
                                         perplexity_results: List[Tuple[str, float, int, int]]) -> List[Tuple[str, int, int]]:
        """
        Identify segments with high perplexity
        
        Args:
            perplexity_results: Results from analyze_perplexity
            
        Returns:
            List of (segment, start_idx, end_idx) for high perplexity segments
        """
        high_perplexity = []
        
        for segment, perplexity, start, end in perplexity_results:
            if perplexity > PERPLEXITY_THRESHOLD and len(segment) >= MIN_REPLACEMENT_LENGTH:
                high_perplexity.append((segment, start, end))
        
        return high_perplexity
    
    def optimize_thinking_chain(self, thinking_chain: str, 
                                aliyun_model=None) -> str:
        """
        Optimize thinking chain by replacing high perplexity segments using local model
        
        Args:
            thinking_chain: Original thinking chain
            aliyun_model: Optional (not used, kept for compatibility)
            
        Returns:
            Optimized thinking chain
        """
        # First, identify and protect critical parts (code blocks, fix sections)
        critical_parts = self._extract_critical_parts(thinking_chain)
        
        # Analyze perplexity
        perplexity_results = self.analyze_perplexity(thinking_chain)
        
        # Identify high perplexity segments
        high_perplexity_segments = self.identify_high_perplexity_segments(perplexity_results)
        
        if not high_perplexity_segments:
            print("No high perplexity segments found. Chain is already optimal.")
            return thinking_chain
        
        print(f"Found {len(high_perplexity_segments)} high perplexity segments to optimize")
        
        # Filter out segments that overlap with critical parts
        safe_segments = self._filter_critical_segments(high_perplexity_segments, critical_parts)
        
        if not safe_segments:
            print("All high perplexity segments are in critical parts. Skipping optimization.")
            return thinking_chain
        
        print(f"Optimizing {len(safe_segments)} safe segments (excluding {len(high_perplexity_segments) - len(safe_segments)} critical parts)")
        
        # Optimize segments one by one using local model
        optimized_chain = thinking_chain
        for segment, start, end in reversed(safe_segments):
            # Generate replacement using local model
            replacement_prompt = f"""Refine the following segment from a code repair thinking chain to make it more coherent and natural, while maintaining the exact meaning and technical accuracy.

Segment to refine:
{segment}

Provide a refined version that:
1. Is clearer and more natural
2. Uses present tense and thinking-aloud style
3. Maintains all technical details
4. Does not change the meaning or conclusions

CRITICAL INSTRUCTIONS:
- DO NOT include any labels, markers, or prefixes like "Refined segment:", "Refined Segment:", "Refined:", or similar
- DO NOT include meta-commentary about the refinement process
- DO NOT repeat the prompt instructions
- Simply write the refined text directly, as if it were part of the original thinking chain
- Write seamlessly and naturally, continuing the thought process

Provide ONLY the refined text, nothing else:"""
            
            try:
                replacement = self.local_model.generate(
                    replacement_prompt,
                    max_tokens=512,
                    temperature=0.7
                )
                # Clean up the replacement (remove any extra formatting)
                replacement = replacement.strip()
                
                # Remove prompt artifacts
                # Remove "Refined segment:" markers
                replacement = re.sub(r'^Refined\s+[Ss]egment:?\s*', '', replacement, flags=re.MULTILINE)
                replacement = re.sub(r'Refined\s+[Ss]egment:?\s*', '', replacement)
                
                # Remove quotes if present
                if replacement.startswith('"') and replacement.endswith('"'):
                    replacement = replacement[1:-1]
                
                # Remove any remaining prompt artifacts
                replacement = replacement.strip()
                
                # Skip if replacement is empty or too short
                if len(replacement) < len(segment) * 0.3:  # At least 30% of original length
                    print(f"  ⚠ Skipped segment at {start}-{end} (replacement too short)")
                    continue
                
                optimized_chain = (
                    optimized_chain[:start] + 
                    replacement + 
                    optimized_chain[end:]
                )
                print(f"  ✓ Optimized segment at position {start}-{end}")
            except Exception as e:
                print(f"  ✗ Error optimizing segment at {start}-{end}: {e}")
                # Keep original segment on error
                continue
        
        # Final cleanup: remove grep errors and other artifacts
        optimized_chain = self._cleanup_artifacts(optimized_chain)
        
        return optimized_chain
    
    def _cleanup_artifacts(self, text: str) -> str:
        """
        Remove artifacts from optimized text (grep errors, prompt markers, etc.)
        
        Args:
            text: Text to clean
            
        Returns:
            Cleaned text
        """
        # Remove grep error messages
        text = re.sub(r'grep:.*?No such file or directory[^\n]*\n?', '', text, flags=re.MULTILINE)
        text = re.sub(r'\[Grep Error:.*?\]', '', text)
        
        # Remove "Refined segment:" markers
        text = re.sub(r'^Refined\s+[Ss]egment:?\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'\nRefined\s+[Ss]egment:?\s*\n', '\n', text)
        text = re.sub(r'Refined\s+[Ss]egment:?\s*', ' ', text)
        
        # Remove excessive newlines
        text = re.sub(r'\n{4,}', '\n\n\n', text)
        
        # Remove standalone "Refined segment:" lines
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if line.lower() in ['refined segment:', 'refined segment', 'refinedsegment:']:
                continue
            cleaned_lines.append(line)
        
        text = '\n'.join(cleaned_lines)
        
        # Clean up multiple spaces
        text = re.sub(r' {3,}', '  ', text)
        
        return text.strip()
    
    def _extract_critical_parts(self, thinking_chain: str) -> List[Tuple[int, int]]:
        """
        Extract positions of critical parts (code blocks, fix sections) that should not be modified
        
        Args:
            thinking_chain: Thinking chain text
            
        Returns:
            List of (start_idx, end_idx) tuples for critical parts
        """
        critical_parts = []
        
        # Find code blocks (```...```)
        code_block_pattern = r'```[a-z]*\n.*?```'
        for match in re.finditer(code_block_pattern, thinking_chain, re.DOTALL):
            critical_parts.append((match.start(), match.end()))
        
        # Find fix sections (<fix>...</fix>)
        fix_pattern = r'<fix>.*?</fix>'
        for match in re.finditer(fix_pattern, thinking_chain, re.DOTALL):
            critical_parts.append((match.start(), match.end()))
        
        # Find validation feedback sections
        validation_pattern = r'\[Validation Feedback\].*?\[Iteration \d+\]'
        for match in re.finditer(validation_pattern, thinking_chain, re.DOTALL):
            critical_parts.append((match.start(), match.end()))
        
        return critical_parts
    
    def _filter_critical_segments(self, segments: List[Tuple[str, int, int]], 
                                  critical_parts: List[Tuple[int, int]]) -> List[Tuple[str, int, int]]:
        """
        Filter out segments that overlap with critical parts
        
        Args:
            segments: List of (segment_text, start_idx, end_idx)
            critical_parts: List of (start_idx, end_idx) for critical parts
            
        Returns:
            Filtered list of safe segments
        """
        safe_segments = []
        
        for segment, seg_start, seg_end in segments:
            is_critical = False
            for crit_start, crit_end in critical_parts:
                # Check if segment overlaps with critical part
                if not (seg_end <= crit_start or seg_start >= crit_end):
                    is_critical = True
                    break
            
            if not is_critical:
                safe_segments.append((segment, seg_start, seg_end))
        
        return safe_segments
    
    def preserve_critical_parts(self, original_chain: str, 
                               optimized_chain: str) -> str:
        """
        Ensure critical parts (like code fixes) are preserved
        
        Args:
            original_chain: Original thinking chain
            optimized_chain: Optimized thinking chain
            
        Returns:
            Final chain with critical parts preserved
        """
        # Extract code blocks from original
        code_blocks = re.findall(r'```[a-z]*\n(.*?)```', original_chain, re.DOTALL)
        
        # Replace code blocks in optimized chain with original ones
        final_chain = optimized_chain
        code_block_pattern = r'```[a-z]*\n.*?```'
        matches = list(re.finditer(code_block_pattern, final_chain, re.DOTALL))
        
        for i, match in enumerate(matches):
            if i < len(code_blocks):
                original_code = code_blocks[i]
                # Find matching code block in original
                original_match = re.search(
                    r'```[a-z]*\n' + re.escape(original_code[:50]) + r'.*?```',
                    original_chain, re.DOTALL
                )
                if original_match:
                    final_chain = (
                        final_chain[:match.start()] +
                        original_match.group(0) +
                        final_chain[match.end():]
                    )
        
        return final_chain


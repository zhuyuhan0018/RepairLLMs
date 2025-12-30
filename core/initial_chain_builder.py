"""
Initial Thinking Chain Builder
Constructs initial thinking chains using external advanced model (Aliyun)
"""
import re
import time
from typing import Dict, List, Tuple, Optional
from models.aliyun_model import AliyunModel
from models.local_model import LocalModel
from utils.grep_tool import GrepTool
from utils.prompts import PromptTemplates
from config import MAX_ITERATIONS, MAX_GREP_ATTEMPTS, SKIP_INITIAL_FIX, SKIP_VALIDATION, SKIP_MERGE


class InitialChainBuilder:
    """Builds initial thinking chains for code repair"""
    
    def __init__(self, aliyun_model: AliyunModel, codebase_path: str = "."):
        """
        Initialize chain builder
        
        Args:
            aliyun_model: Aliyun model instance
            codebase_path: Path to codebase root
        """
        self.aliyun_model = aliyun_model
        self.codebase_path = codebase_path
        self.grep_tool = GrepTool()
    
    def analyze_repair_order(self, buggy_code: str, fixed_code: str, 
                           bug_location: str) -> List[Dict]:
        """
        Analyze repair order and identify fix points
        
        Args:
            buggy_code: Original buggy code
            fixed_code: Fixed code
            bug_location: Location of the bug
            
        Returns:
            List of fix point dictionaries
        """
        from config import SKIP_REPAIR_ORDER
        
        if SKIP_REPAIR_ORDER:
            print("=" * 80)
            print("[Stage] >>> ENTERING: Repair Order Analysis")
            print("=" * 80)
            print("[Stage] SKIPPED (SKIP_REPAIR_ORDER enabled)")
            print("[Stage] Attempting to extract fix points from bug_location...")
            # Try to extract fix points from bug_location if available
            fix_points = self._parse_fix_points("", bug_location)
            if fix_points:
                print(f"[Stage] Extracted {len(fix_points)} fix point(s) from bug_location")
            else:
                print("[Stage] No fix points found in bug_location, creating default fix point")
                fix_points = [{
                    'id': 1,
                    'description': "Main fix location",
                    'location': bug_location.split('\n')[0] if '\n' in bug_location else bug_location
                }]
            print("[Stage] <<< COMPLETED: Repair Order Analysis (SKIPPED)")
            print("=" * 80)
            return fix_points
        
        print("=" * 80)
        print("[Stage] >>> ENTERING: Repair Order Analysis")
        print("=" * 80)
        print("[Stage] Purpose: Analyzing repair order and identifying fix points")
        print(f"[Stage] Input: buggy_code ({len(buggy_code)} chars), fixed_code ({len(fixed_code)} chars)")
        stage_start_time = time.time()
        print(f"[Stage] Calling model API for repair order analysis...")
        api_start_time = time.time()
        prompt = PromptTemplates.get_repair_order_analysis_prompt(
            buggy_code, fixed_code, bug_location
        )
        
        response = self.aliyun_model.generate(prompt)
        api_end_time = time.time()
        api_duration = api_end_time - api_start_time
        print(f"[Stage] Model API call completed in {api_duration:.2f} seconds")
        print(f"[Stage] Model response received ({len(response)} characters)")
        
        # Parse fix points from response
        print(f"[Stage] Parsing fix points from response...")
        fix_points = self._parse_fix_points(response, bug_location)
        stage_end_time = time.time()
        stage_duration = stage_end_time - stage_start_time
        print(f"[Stage] Repair Order Analysis - Identified {len(fix_points)} fix point(s)")
        print(f"[Stage] Total stage duration: {stage_duration:.2f} seconds (API: {api_duration:.2f}s, Other: {stage_duration - api_duration:.2f}s)")
        print("[Stage] <<< COMPLETED: Repair Order Analysis")
        print("=" * 80)
        
        return fix_points
    
    def _parse_fix_points(self, response: str, bug_location: str = "unknown") -> List[Dict]:
        """Parse fix points from model response"""
        fix_points = []
        
        # Extract fix points from XML tags
        fix_point_pattern = r'<fix_points>(.*?)</fix_points>'
        match = re.search(fix_point_pattern, response, re.DOTALL)
        
        if match:
            content = match.group(1)
            # Extract numbered items
            items = re.findall(r'\d+\.\s*(.+)', content)
            for i, item in enumerate(items):
                fix_points.append({
                    'id': i + 1,
                    'description': item.strip(),
                    'location': f"fix_point_{i+1}"
                })
        
        # If no fix points found, try to extract from vulnerability_locations in bug_location
        if not fix_points and "Vulnerability Details:" in bug_location:
            # Extract vulnerability locations from bug_location string
            vuln_section = bug_location.split("Vulnerability Details:")[1] if "Vulnerability Details:" in bug_location else ""
            if vuln_section:
                # Parse each vulnerability location
                # Format: "  1. file:function (lines X-Y)\n     Description: ..."
                vuln_pattern = r'(\d+)\.\s+([^:]+):([^(]+)\s+\(lines\s+(\d+)-(\d+)\)\s+Description:\s+(.+?)(?=\n\s*\d+\.|$)'
                matches = re.findall(vuln_pattern, vuln_section, re.DOTALL)
                for match in matches:
                    idx, file_path, func_name, line_start, line_end, description = match
                    fix_points.append({
                        'id': int(idx),
                        'description': description.strip(),
                        'location': f"{file_path.strip()}:{func_name.strip()} (line {line_start})"
                    })
        
        # Final fallback: create single fix point
        if not fix_points:
            fix_points.append({
                'id': 1,
                'description': "Main fix location",
                'location': bug_location.split('\n')[0] if '\n' in bug_location else bug_location
            })
        
        return fix_points
    
    def build_fix_point_chain(self, 
                             buggy_code: str,
                             fixed_code: str,
                             fix_point: Dict,
                             ground_truth_fix: Optional[str] = None) -> Tuple[str, Optional[str]]:
        """
        Build thinking chain for a single fix point
        
        Args:
            buggy_code: Buggy code at this location
            fixed_code: Fixed code at this location (not provided to model, only for validation)
            fix_point: Fix point dictionary
            ground_truth_fix: Ground truth fix for validation
            
        Returns:
            Tuple of (thinking_chain, final_fix_code)
            - thinking_chain: Complete thinking chain for this fix point
            - final_fix_code: Final fix code generated (None if no valid fix)
        """
        thinking_chain = ""
        iteration = 0
        grep_attempts = 0
        context = ""
        no_fix_count = 0  # Track consecutive iterations without fix
        final_fix_code = None  # Track final fix code
        
        print("")
        print("    " + "=" * 80)
        print(f"    [Stage] >>> ENTERING: Fix Point Chain Building")
        print("    " + "=" * 80)
        chain_building_start_time = time.time()
        print(f"    [Stage] Fix Point: {fix_point.get('description', fix_point.get('location', 'N/A'))[:60]}")
        print(f"    [Stage] Fix Point ID: {fix_point.get('id', 'N/A')}")
        print(f"    [Stage] Location: {fix_point.get('location', 'N/A')}")
        if ground_truth_fix:
            print(f"    [Stage] Ground Truth: Available ({len(ground_truth_fix)} characters) - will be used for validation")
        else:
            print(f"    [Stage] Ground Truth: NOT available - validation will be skipped")
        print("    " + "-" * 80)
        
        while iteration < MAX_ITERATIONS:
            # Generate initial fix or continue thinking
            if iteration == 0:
                if SKIP_INITIAL_FIX:
                    print(f"    [Stage] >>> ITERATION {iteration + 1}: SKIPPED (SKIP_INITIAL_FIX enabled)")
                    print(f"    [Stage] Skipping initial fix generation, proceeding to validation/iteration")
                    print("    " + "-" * 80)
                    # Skip initial fix, but still need to set up for validation
                    thinking = None
                    fix = None
                    grep_cmd = None
                    # If we have existing thinking chain, use it; otherwise create placeholder
                    if not thinking_chain:
                        thinking_chain = "[Initial fix generation skipped - SKIP_INITIAL_FIX enabled]"
                    iteration += 1
                    continue
                else:
                    print(f"    [Stage] >>> ITERATION {iteration + 1}: Initial Analysis")
                    print(f"    [Stage] Purpose: Generating initial analysis and fix proposal")
                    print("    " + "-" * 80)
                    iteration_start_time = time.time()
                    # Do NOT pass fixed_code in initial fix prompt - only provide it during validation
                    prompt = PromptTemplates.get_initial_fix_prompt(
                        buggy_code, fix_point['location'], context, None
                    )
            else:
                print(f"    [Stage] >>> ITERATION {iteration + 1}: Reflecting and Improving")
                print(f"    [Stage] Purpose: Reflecting and improving analysis based on previous thinking")
                if context:
                    print(f"    [Stage] Context available: Grep results from previous iteration ({len(context)} chars)")
                print("    " + "-" * 80)
                iteration_start_time = time.time()
                # Do NOT pass fixed_code in iterative reflection - only provide it during validation
                prompt = PromptTemplates.get_iterative_reflection_prompt(
                    thinking_chain, buggy_code, None, None, context if grep_attempts > 0 else None
                )
            
            print(f"    [Stage] Calling model API...")
            api_start_time = time.time()
            response = self.aliyun_model.generate(prompt)
            api_end_time = time.time()
            api_duration = api_end_time - api_start_time
            print(f"    [Stage] Model API call completed in {api_duration:.2f} seconds")
            print(f"    [Stage] Model response received ({len(response)} characters)")
            
            # Check if response is truncated (missing closing tags)
            is_truncated = False
            if '<thinking>' in response and '</thinking>' not in response:
                is_truncated = True
                print(f"    [Warning] Response appears truncated: <thinking> tag found but </thinking> missing")
            if '<fix>' in response and '</fix>' not in response:
                is_truncated = True
                print(f"    [Warning] Response appears truncated: <fix> tag found but </fix> missing")
            if is_truncated:
                print(f"    [Warning] Truncated response may cause parsing issues. Consider increasing max_tokens.")
            
            # Extract thinking and fix from response
            thinking, fix, grep_cmd = self._parse_response(response)
            
            # Debug: Save response if thinking is empty (for debugging)
            if not thinking:
                import pathlib
                debug_dir = pathlib.Path("debug_responses")
                debug_dir.mkdir(exist_ok=True)
                debug_file = debug_dir / f"fp_{fix_point.get('id', 'unknown')}_iter{iteration}_response.txt"
                with debug_file.open('w', encoding='utf-8') as f:
                    f.write(f"=== Fix Point: {fix_point.get('description', 'N/A')[:60]} ===\n\n")
                    f.write(f"Response length: {len(response)} characters\n\n")
                    f.write("=== Full Response ===\n")
                    f.write(response)
                    f.write("\n\n=== Parsing Attempts ===\n")
                    # Try to show what patterns were tried
                    f.write("Looking for <thinking>...</thinking> tags...\n")
                print(f"    [Debug] No thinking extracted, saved response to {debug_file}")
                
                # Try one more aggressive fallback: if response looks like thinking, use it
                if len(response) > 100:
                    # Check if response contains thinking-like content but no tags
                    reasoning_words = ['think', 'consider', 'analyze', 'looking', 'maybe', 'actually', 
                                     'wait', 'hmm', 'reconsider', 'should', 'need', 'must', 'vulnerability',
                                     'buggy', 'fixed', 'code', 'memory', 'subscription', 'session']
                    word_count = sum(1 for word in reasoning_words if word in response.lower())
                    if word_count >= 3:  # Has enough reasoning words
                        thinking = response.strip()
                        print(f"    [Fallback] Using entire response as thinking (contains reasoning content)")
            
            if thinking:
                thinking_chain += f"\n\n[Iteration {iteration + 1}]\n{thinking}"
                print(f"    [Stage] Thinking extracted ({len(thinking)} characters)")
            else:
                print(f"    [Warning] No thinking extracted from response ({len(response)} characters)")
                # Don't add empty thinking to chain, but continue iteration
            
            if grep_cmd:
                print(f"    [Stage] >>> Grep command detected in model response")
                print(f"    [Stage] Grep command: {grep_cmd}")
                # Grep command resets no_fix_count (grep is valid action)
                no_fix_count = 0
            elif fix:
                print(f"    [Stage] Fix code detected in response ({len(fix)} characters)")
                no_fix_count = 0  # Reset counter when fix is found
            else:
                # No grep and no fix - increment counter
                no_fix_count += 1
                if no_fix_count >= 2:
                    print(f"    [Warning] No fix code generated after {no_fix_count} consecutive iterations")
                    print(f"    [Warning] This may indicate the model is not following the required format")
                    # Add explicit feedback to thinking chain
                    thinking_chain += f"\n\n[Warning: Model failed to generate fix code after {no_fix_count} iterations. Response format may be incorrect.]"
            
            # Handle grep command
            if grep_cmd:
                if grep_attempts < MAX_GREP_ATTEMPTS:
                    print("    " + "-" * 80)
                    print(f"    [Stage] >>> ENTERING: Grep Execution")
                    print(f"    [Stage] Attempt: {grep_attempts + 1}/{MAX_GREP_ATTEMPTS}")
                    print(f"    [Grep Request] Command: {grep_cmd}")
                    print(f"    [Grep Request] Codebase path: {self.codebase_path}")
                    print(f"    [Grep Request] Full command will be executed in: {self.codebase_path}")
                    print("    " + "-" * 80)
                    success, grep_results = self.grep_tool.execute_grep(
                        grep_cmd, self.codebase_path
                    )
                    if success:
                        # Log complete grep results for inspection with detailed information
                        print(f"    [Grep Success] Results received ({len(grep_results)} characters)")
                        print("")
                        print("    " + "=" * 80)
                        print("    [Grep Results - Full Content - For Accuracy Verification]")
                        print("    " + "=" * 80)
                        print(f"    [Grep Info] Command executed: {grep_cmd}")
                        print(f"    [Grep Info] Codebase: {self.codebase_path}")
                        print(f"    [Grep Info] Result size: {len(grep_results)} characters, {len(grep_results.split(chr(10)))} lines")
                        print("    " + "-" * 80)
                        # Print all results, with clear formatting
                        if grep_results.strip():
                            line_num = 0
                            for line in grep_results.split('\n'):
                                line_num += 1
                                # Preserve original formatting, but indent for readability
                                # Mark matched lines if they contain >>> (from grep tool formatting)
                                if line.strip().startswith('>>>'):
                                    print(f"    [Line {line_num}] {line}")
                                else:
                                    print(f"    [Line {line_num}] {line}")
                        else:
                            print("    (Empty results - no matches found)")
                        print("    " + "-" * 80)
                        print(f"    [Grep Summary] Total lines: {len(grep_results.split(chr(10)))}")
                        print(f"    [Grep Summary] Total characters: {len(grep_results)}")
                        print("    " + "=" * 80)
                        print(f"    [Stage] <<< COMPLETED: Grep Execution (SUCCESS)")
                        print("    " + "-" * 80)
                        print(f"    [Stage] Grep completed successfully, continuing to next iteration with context")
                        print("")
                        
                        context = grep_results
                        grep_attempts += 1
                        iteration += 1
                        continue
                    else:
                        # Log grep errors completely with detailed information
                        print("    " + "=" * 80)
                        print("    [Grep Error - Full Error Message - For Debugging]")
                        print("    " + "=" * 80)
                        print(f"    [Grep Error Info] Command attempted: {grep_cmd}")
                        print(f"    [Grep Error Info] Codebase: {self.codebase_path}")
                        print("    " + "-" * 80)
                        print(f"    [Grep Error Details - Complete Error Message]")
                        print("    " + "-" * 80)
                        # Print error message line by line for clarity
                        if grep_results:
                            for line in grep_results.split('\n'):
                                print(f"    {line}")
                        else:
                            print("    (Empty error message)")
                        print("    " + "-" * 80)
                        print(f"    [Grep Error Summary] Error message length: {len(grep_results)} characters")
                        print("    " + "=" * 80)
                        print(f"    [Stage] <<< COMPLETED: Grep Execution (FAILED)")
                        print("    " + "-" * 80)
                        print(f"    [Stage] Continuing without grep results")
                        print("")
                        # Continue without adding error to chain
                        iteration += 1
                        continue
                else:
                    print("    " + "-" * 80)
                    print(f"    [Stage] Max grep attempts ({MAX_GREP_ATTEMPTS}) reached")
                    print(f"    [Stage] Continuing without grep - max attempts limit reached")
                    print("    " + "-" * 80)
                    thinking_chain += "\n\n[Max grep attempts reached]"
            
            # If we have a fix, validate it (unless validation is skipped)
            if fix and ground_truth_fix:
                if SKIP_VALIDATION:
                    print(f"    [Stage] Validation - SKIPPED (SKIP_VALIDATION enabled)")
                    print(f"    [Stage] Skipping validation, using fix as-is")
                    thinking_chain += f"\n\n[Fix generated - validation skipped]\n{fix}"
                    final_fix_code = fix
                    break
                else:
                    print(f"    [Stage] Validation - Comparing generated fix with ground truth")
                    validation_start_time = time.time()
                    is_correct, validation_hints = self._validate_fix(
                        fix, ground_truth_fix, fix_point['location']
                    )
                    validation_end_time = time.time()
                    validation_duration = validation_end_time - validation_start_time
                    print(f"    [Stage] Validation completed in {validation_duration:.2f} seconds")
                    
                    if is_correct:
                        print(f"    [Stage] Validation - Fix is CORRECT!")
                        print(f"    [Stage] Validation - Ending fix point processing immediately (fix is correct)")
                        thinking_chain += f"\n\n[Fix validated as correct]\n{fix}"
                        final_fix_code = fix
                        break
                    else:
                        print(f"    [Stage] Validation - Fix is INCORRECT, receiving feedback for improvement")
                        print(f"    [Validation Feedback] {validation_hints[:200]}..." if len(validation_hints) > 200 else f"    [Validation Feedback] {validation_hints}")
                        thinking_chain += f"\n\n[Validation Feedback]\n{validation_hints}"
                        # Continue with reflection
                    print(f"    [Stage] Iteration {iteration + 1} - Reflecting based on validation feedback")
                    # Do NOT pass fixed_code in iterative reflection - validation feedback already contains the comparison
                    prompt = PromptTemplates.get_iterative_reflection_prompt(
                        thinking_chain, buggy_code, None, validation_hints, None
                    )
                    iteration += 1
                    continue
            elif fix:
                # No ground truth, accept the fix
                # Validate that fix is code format, not text description
                if self._is_code_format(fix):
                    # Check fix completeness
                    is_complete, completeness_issue = self._check_fix_completeness(fix, fixed_code)
                    if not is_complete:
                        print(f"    [Warning] Fix completeness check failed: {completeness_issue}")
                        print(f"    [Warning] Fix may be incomplete - missing parts from fixed_code")
                        print(f"    [Warning] Continuing to next iteration to request complete fix")
                        thinking_chain += f"\n\n[Iteration {iteration + 1} - Note: Previous fix was incomplete. Missing: {completeness_issue}]"
                        no_fix_count += 1
                        iteration += 1
                        continue
                    
                    # Check logic consistency
                    is_consistent, consistency_issue = self._check_logic_consistency(thinking, fix)
                    if not is_consistent:
                        print(f"    [Warning] Logic consistency check failed: {consistency_issue}")
                        print(f"    [Warning] Thinking description may contradict fix code")
                        print(f"    [Warning] Continuing to next iteration to fix logic inconsistency")
                        thinking_chain += f"\n\n[Iteration {iteration + 1} - Note: Logic inconsistency detected. Issue: {consistency_issue}]"
                        no_fix_count += 1
                        iteration += 1
                        continue
                    
                    print(f"    [Stage] No ground truth available, accepting generated fix (code format verified, completeness checked, logic consistent)")
                    thinking_chain += f"\n\n[Final Fix]\n{fix}"
                    final_fix_code = fix
                    break
                else:
                    print(f"    [Warning] Fix detected but appears to be text description, not code format")
                    print(f"    [Warning] Fix content preview: {fix[:200]}...")
                    print(f"    [Warning] Continuing to next iteration to request code format fix")
                    thinking_chain += f"\n\n[Iteration {iteration + 1} - Note: Previous fix was text description, need code format]"
                    no_fix_count += 1  # Count this as no valid fix
                    iteration += 1
                    continue
            
            # Early stop if no fix after multiple iterations
            if no_fix_count >= 2 and iteration > 0:
                print(f"    [Warning] Stopping early: No fix code generated after {no_fix_count} consecutive iterations")
                thinking_chain += f"\n\n[Stopped early: Model failed to generate fix code after {no_fix_count} iterations]"
                break
            
            iteration_end_time = time.time()
            iteration_duration = iteration_end_time - iteration_start_time
            print(f"    [Stage] Iteration {iteration + 1} completed in {iteration_duration:.2f} seconds, continuing to next iteration")
            iteration += 1
        
        chain_building_end_time = time.time()
        chain_building_duration = chain_building_end_time - chain_building_start_time
        if iteration >= MAX_ITERATIONS:
            print(f"    [Stage] Max iterations ({MAX_ITERATIONS}) reached, finishing chain building")
        else:
            print(f"    [Stage] Chain building completed after {iteration + 1} iteration(s)")
        
        print("    " + "=" * 80)
        print(f"    [Stage] <<< COMPLETED: Fix Point Chain Building")
        print(f"    [Stage] Final thinking chain length: {len(thinking_chain)} characters")
        if final_fix_code:
            print(f"    [Stage] Final fix code length: {len(final_fix_code)} characters")
        else:
            print(f"    [Stage] No final fix code generated")
        print(f"    [Stage] Total chain building duration: {chain_building_duration:.2f} seconds")
        print("    " + "=" * 80)
        print("")
        
        return thinking_chain.strip(), final_fix_code
    
    def _parse_response(self, response: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Parse model response to extract thinking, fix, and grep command
        
        Returns:
            Tuple of (thinking, fix, grep_command)
        """
        thinking = None
        fix = None
        grep_cmd = None
        
        # Extract thinking - try multiple patterns for robustness
        thinking_match = None
        patterns = [
            # Pattern 1: Standard format
            (r'<thinking>(.*?)</thinking>', re.DOTALL),
            # Pattern 2: With whitespace around content
            (r'<thinking>\s*(.*?)\s*</thinking>', re.DOTALL),
            # Pattern 3: Case insensitive
            (r'<thinking>(.*?)</thinking>', re.DOTALL | re.IGNORECASE),
            # Pattern 4: With newlines and spaces
            (r'<thinking>\s*\n\s*(.*?)\s*\n\s*</thinking>', re.DOTALL),
            # Pattern 5: Without newlines in tag (single line)
            (r'<thinking>([^<\n]+)</thinking>', re.DOTALL),
        ]
        
        for pattern, flags in patterns:
            thinking_match = re.search(pattern, response, flags)
            if thinking_match:
                break
        
        if thinking_match:
            thinking = thinking_match.group(1).strip()
            # Clean up common artifacts
            if thinking.startswith('[') and thinking.endswith(']'):
                thinking = thinking[1:-1].strip()
        else:
            # Fallback: If no <thinking> tag, try to extract thinking-like content
            # Look for patterns that suggest thinking content (not just code)
            # If response is long and doesn't start with XML tags, use it as thinking
            if len(response) > 200 and not response.strip().startswith('<'):
                # Check if it looks like thinking (contains reasoning words)
                reasoning_indicators = ['think', 'consider', 'analyze', 'looking', 'maybe', 'actually', 
                                      'wait', 'hmm', 'reconsider', 'should', 'need', 'must', 'vulnerability',
                                      'buggy', 'fixed', 'code', 'memory', 'free']
                if any(indicator in response.lower() for indicator in reasoning_indicators):
                    thinking = response.strip()
                    print(f"    [Fallback] Using entire response as thinking (no <thinking> tag found)")
        
        # Extract fix
        fix_match = re.search(r'<fix>(.*?)</fix>', response, re.DOTALL)
        if fix_match:
            fix = fix_match.group(1).strip()
        
        # Extract grep command
        grep_match = re.search(r'<grep_command>(.*?)</grep_command>', response, re.DOTALL)
        if grep_match:
            grep_cmd = grep_match.group(1).strip()
        else:
            # Try to extract from text
            grep_cmd = self.grep_tool.extract_grep_command(response)
        
        return thinking, fix, grep_cmd
    
    def _is_code_format(self, fix: str) -> bool:
        """
        Check if fix is in code format (has diff markers like -/+) or actual code,
        not just text description
        
        Args:
            fix: The fix string to check
            
        Returns:
            True if it looks like code format, False if it's text description
        """
        if not fix or len(fix.strip()) < 10:
            return False
        
        fix_lower = fix.lower()
        
        # Check for diff format markers
        has_diff_markers = ('-' in fix and '+' in fix) or fix.strip().startswith('-') or fix.strip().startswith('+')
        
        # Check for code-like patterns
        has_code_patterns = any(pattern in fix for pattern in [
            ';',  # C code statements
            '{',  # Code blocks
            '}',  # Code blocks
            '(',  # Function calls
            ')',  # Function calls
            '->',  # Pointer access
            '&',   # Address operator
            '*',   # Pointer/dereference
            '#',   # Preprocessor
        ])
        
        # Check if it's clearly a text description (common phrases)
        text_description_indicators = [
            'the fix involves',
            'the fix ensures',
            'this change',
            'this fix',
            'by moving',
            'by ensuring',
            'the code is moved',
            'the fix is',
        ]
        is_text_description = any(indicator in fix_lower for indicator in text_description_indicators)
        
        # If it has diff markers or code patterns, and doesn't look like text description, it's code format
        if (has_diff_markers or has_code_patterns) and not is_text_description:
            return True
        
        # If it's clearly a text description, it's not code format
        if is_text_description and not has_code_patterns:
            return False
        
        # Default: if it has code patterns, assume it's code
        return has_code_patterns
    
    def _check_fix_completeness(self, generated_fix: str, fixed_code: Optional[str]) -> Tuple[bool, Optional[str]]:
        """
        Check if generated fix includes all related code changes from fixed_code
        
        Args:
            generated_fix: Generated fix code
            fixed_code: Reference fixed code to compare against
            
        Returns:
            Tuple of (is_complete, missing_parts_description)
        """
        if not fixed_code:
            return True, None  # No reference to compare against
        
        # Extract key patterns from fixed_code that should be in the fix
        # Look for common cleanup patterns
        missing_parts = []
        
        # Check for publish request cleanup
        if 'UA_PublishResponseEntry' in fixed_code or 'dequeuePublishReq' in fixed_code:
            if 'UA_PublishResponseEntry' not in generated_fix and 'dequeuePublishReq' not in generated_fix:
                missing_parts.append("publish request cleanup (UA_PublishResponseEntry/dequeuePublishReq)")
        
        # Check for subscription cleanup
        if 'UA_Subscription' in fixed_code and 'deleteSubscription' in fixed_code:
            if 'UA_Subscription' not in generated_fix or 'deleteSubscription' not in generated_fix:
                missing_parts.append("subscription cleanup (UA_Subscription/deleteSubscription)")
        
        # Check for conditional compilation blocks
        if '#ifdef' in fixed_code:
            # Count #ifdef blocks in fixed_code
            ifdef_count_fixed = fixed_code.count('#ifdef')
            ifdef_count_generated = generated_fix.count('#ifdef')
            if ifdef_count_fixed > ifdef_count_generated:
                missing_parts.append(f"conditional compilation blocks (expected {ifdef_count_fixed}, found {ifdef_count_generated})")
        
        if missing_parts:
            return False, f"Missing: {', '.join(missing_parts)}"
        
        return True, None
    
    def _check_logic_consistency(self, thinking: str, fix: str) -> Tuple[bool, Optional[str]]:
        """
        Check if thinking description is consistent with fix code
        
        Args:
            thinking: Thinking chain text
            fix: Fix code
            
        Returns:
            Tuple of (is_consistent, inconsistency_description)
        """
        inconsistencies = []
        
        # Check for "before"/"after" consistency
        thinking_lower = thinking.lower()
        fix_lower = fix.lower()
        
        # If thinking mentions "moved from before X to after Y"
        # but the fix actually places code before X, that's inconsistent
        if 'moved from before' in thinking_lower and 'to after' in thinking_lower:
            # This pattern suggests code was moved from "before" to "after"
            # But typically fixes move code TO "before" (to prevent use-after-free)
            # Check if fix actually places code before something
            if 'before' in thinking_lower and 'detach' in thinking_lower:
                # If thinking says "moved from before detach to after cleanup"
                # but fix should place cleanup before detach, that's wrong
                if 'before' not in fix_lower or 'detach' not in fix_lower:
                    # The fix doesn't show "before detach" pattern
                    # This might be okay if the fix is just moving code
                    pass
                else:
                    # Check if the description contradicts the fix
                    if 'after' in thinking_lower and 'before' in fix_lower:
                        inconsistencies.append("Description says 'after' but fix places code 'before'")
        
        # Check for contradictory "before"/"after" statements
        if 'before' in thinking_lower and 'after' in thinking_lower:
            # Look for patterns like "from before X to after Y"
            # This might be correct, but check context
            if 'moved from before' in thinking_lower and 'to after' in thinking_lower:
                # This is suspicious - usually we move TO before, not FROM before TO after
                if 'securechannel' in thinking_lower or 'detach' in thinking_lower:
                    # If it's about SecureChannel detachment, moving FROM before TO after is wrong
                    inconsistencies.append("Description suggests moving from 'before' to 'after', which contradicts the fix goal of ensuring cleanup happens BEFORE detachment")
        
        if inconsistencies:
            return False, "; ".join(inconsistencies)
        
        return True, None
    
    def _validate_fix(self, generated_fix: str, ground_truth_fix: str, 
                     bug_location: str) -> Tuple[bool, Optional[str]]:
        """
        Validate generated fix against ground truth
        
        Returns:
            Tuple of (is_correct, hints)
        """
        print(f"    [Stage] Validation - Calling model API for fix validation...")
        validation_api_start = time.time()
        prompt = PromptTemplates.get_fix_validation_prompt(
            generated_fix, ground_truth_fix, bug_location
        )
        
        response = self.aliyun_model.generate(prompt)
        validation_api_end = time.time()
        validation_api_duration = validation_api_end - validation_api_start
        print(f"    [Stage] Validation - Model API call completed in {validation_api_duration:.2f} seconds")
        print(f"    [Stage] Validation - Model response received ({len(response)} characters)")
        
        # Parse validation result
        correct_match = re.search(r'<correct>(.*?)</correct>', response, re.DOTALL)
        is_correct = False
        if correct_match:
            correct_text = correct_match.group(1).strip().lower()
            is_correct = 'yes' in correct_text or 'correct' in correct_text
        
        hints = None
        if not is_correct:
            review_match = re.search(r'<review>(.*?)</review>', response, re.DOTALL)
            if review_match:
                hints = review_match.group(1).strip()
        
        return is_correct, hints
    
    def merge_thinking_chains(self, fix_points: List[Dict], 
                             thinking_chains: Dict[str, str],
                             final_fix_codes: Dict[str, Optional[str]] = None) -> str:
        """
        Merge individual thinking chains into complete chain
        
        Args:
            fix_points: List of fix point dictionaries
            thinking_chains: Dictionary mapping fix point IDs to thinking chains
            final_fix_codes: Dictionary mapping fix point IDs to final fix codes
            
        Returns:
            Merged thinking chain (including final fix codes)
        """
        if SKIP_MERGE:
            print("")
            print("=" * 80)
            print("[Stage] >>> ENTERING: Merging Thinking Chains")
            print("=" * 80)
            print("[Stage] SKIPPED (SKIP_MERGE enabled)")
            print("[Stage] Using simple concatenation instead of model-based merging")
            print(f"[Stage] Merging {len(fix_points)} fix point(s) with {len(thinking_chains)} thinking chain(s)")
            if final_fix_codes:
                fix_codes_count = sum(1 for code in final_fix_codes.values() if code is not None)
                print(f"[Stage] Including {fix_codes_count} final fix code(s) in merged chain")
            print("[Stage] <<< COMPLETED: Merging Thinking Chains (SKIPPED - using concatenation)")
            print("=" * 80)
            print("")
            
            # Simple concatenation: join all thinking chains with separators
            merged_parts = []
            for i, fix_point in enumerate(fix_points, 1):
                location = fix_point.get('location', f'fix_point_{i}')
                chain = thinking_chains.get(location, "")
                if chain:
                    merged_parts.append(f"=== Fix Point {i}: {fix_point.get('description', location)[:60]} ===\n{chain}")
                if final_fix_codes and location in final_fix_codes and final_fix_codes[location]:
                    merged_parts.append(f"\n[Final Fix Code for Fix Point {i}]\n{final_fix_codes[location]}")
            
            return "\n\n".join(merged_parts) if merged_parts else "\n\n".join(thinking_chains.values())
        
        print("")
        print("=" * 80)
        print("[Stage] >>> ENTERING: Merging Thinking Chains")
        print("=" * 80)
        merge_start_time = time.time()
        print("[Stage] Purpose: Merging individual chains into complete chain")
        print(f"[Stage] Merging {len(fix_points)} fix point(s) with {len(thinking_chains)} thinking chain(s)")
        if final_fix_codes:
            fix_codes_count = sum(1 for code in final_fix_codes.values() if code is not None)
            print(f"[Stage] Including {fix_codes_count} final fix code(s) in merged chain")
        print(f"[Stage] Calling model API for chain merging...")
        api_start_time = time.time()
        prompt = PromptTemplates.get_merge_thinking_chain_prompt(
            [fp['location'] for fp in fix_points], thinking_chains, final_fix_codes or {}
        )
        
        response = self.aliyun_model.generate(prompt)
        api_end_time = time.time()
        api_duration = api_end_time - api_start_time
        print(f"[Stage] Model API call completed in {api_duration:.2f} seconds")
        print(f"[Stage] Model response received ({len(response)} characters)")
        merge_end_time = time.time()
        merge_duration = merge_end_time - merge_start_time
        print(f"[Stage] Total merge duration: {merge_duration:.2f} seconds (API: {api_duration:.2f}s, Other: {merge_duration - api_duration:.2f}s)")
        print("[Stage] <<< COMPLETED: Merging Thinking Chains")
        print("=" * 80)
        print("")
        
        # Extract merged thinking
        merged_match = re.search(r'<complete_thinking>(.*?)</complete_thinking>', 
                                response, re.DOTALL)
        if merged_match:
            return merged_match.group(1).strip()
        else:
            # Fallback: concatenate chains
            return "\n\n".join([
                f"=== Fix Point: {fp['location']} ===\n{thinking_chains.get(fp['location'], '')}"
                for fp in fix_points
            ])


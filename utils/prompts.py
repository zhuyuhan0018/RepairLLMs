"""
代码修复系统的提示词模板
Prompt templates for the code repair system
"""
import re
from typing import Dict, Optional


class PromptTemplates:
    """
    提示词模板集合类
    包含代码修复流程各个阶段所需的提示词模板
    Collection of prompt templates for different stages
    """
    
    @staticmethod
    def get_repair_order_analysis_prompt(buggy_code: str, bug_location: str) -> str:
        """
        生成修复顺序分析提示词
        用于分析需要修复的位置及其逻辑顺序（哪些函数/文件需要先修复）
        
        Prompt for analyzing repair order (which functions/files to fix first)
        
        Args:
            buggy_code: 原始有漏洞的代码
            bug_location: 漏洞位置（文件/函数），可能包含详细的文件、函数和行号信息
            
        Returns:
            格式化后的提示词字符串
        """
        # Extract vulnerability context (simplified)
        vulnerability_context = ""
        if "Vulnerability Details:" in bug_location or "Description:" in bug_location:
            vulnerability_context = """
## Key Understanding:
- "should be added before [X]" → Move code to execute BEFORE X
- "removed from..." → Code is in wrong location/timing
- Focus on EXECUTION ORDER and resource dependencies
- Each vulnerability location description = likely a separate fix point
"""
        
        return f"""Analyze repair order for a MEMORY ACCESS vulnerability. Identify fix points and their logical order.

{vulnerability_context}

---

## Input Information

### Bug Location:
{bug_location}

### Buggy Code:
```c
{buggy_code}
```

---

## Analysis Task

1. **How many fix points?** 
   - Each vulnerability location = one fix point
   - Include: header includes, code additions, code removals, call relationship changes

2. **What is the repair order?** 
   - Consider dependencies between fix points
   - Follow the repair order rules below

---

## Focus Areas

- **Memory safety**: use-after-free, buffer overflow, null pointer
- **Resource release order**: what must be cleaned up before what
- **Dependencies**: what must be done before what
- **Code movement**: why code is moved from one location to another

---

## Repair Order Rules (MUST follow in this order)

1. **Header includes first**: 
   - If a type/function is defined in a file which this file does not include, add the include directive first
   - Example: If code uses `UA_Subscription` but file doesn't include `ua_subscription.h`, add `#include "ua_subscription.h"` first

2. **Ensure target function is ready**: 
   - If call relationship change involves calling a new/modified function, ensure that function has necessary code BEFORE changing the call

3. **Add before remove**: 
   - Add code to new location before removing from old location
   - **MUST add first** - this is critical for correctness

4. **Call relationship changes**: 
   - After target function is ready, change call relationship
   - Example: Change `UA_Session_deleteMembersCleanup(...)` to `removeSession(...)`

5. **Code removal**: 
   - Remove old code last, after new code is in place and calls are updated

---

## Dependency Analysis Guidelines

- **Header dependencies**: 
  - If code uses types/functions from another file → Include that header FIRST
  - Example: `If A type is defined in a file which this file does not include, you should consider include this file first.`

- **Function dependencies**: 
  - If "call X instead of Y" and X needs code added → Add code to X FIRST, then change call
  - Example: If moving code to `removeSession` and `UA_SessionManager_deleteMembers` calls it → Add code to `removeSession` first, then update `UA_SessionManager_deleteMembers`

- **Code movement**: 
  - If code moves from A to B → Add to B first, then remove from A

- **Resource dependencies**: 
  - What resources must be cleaned up before what
  - Example: Subscriptions must be cleaned up before SecureChannel detach

---

## Grep Tool (Optional but Recommended)

**Note**: Grep is optional. The buggy_code and vulnerability description are provided, but use grep when you need more certainty.

**When to use grep:**
- Verify function names or variable names (prevent typos/encoding issues)
- Find where a function/variable is defined or how it is used
- Locate the correct file/line context before writing the fix
- Need the context of the file/line context to write the fix

**Usage format:**
```
<grep_command>grep -rn "pattern" src/</grep_command>
```

**Examples (adjust pattern/file as needed):**
- `<grep_command>grep -rn "UA_Session_deleteSubscription" src/</grep_command>`
- `<grep_command>grep -rn "removeSession" src/server/ua_session_manager.c</grep_command>`
- `<grep_command>grep -rn "serverSubscriptions" src/</grep_command>`

---

## Response Format

**Required structure:**

<analysis>
[Step-by-step analysis of repair order, including:
- Why each fix point is needed
- What dependencies exist between fix points
- Why the identified order is correct]
</analysis>

<fix_points>
1. [First fix point description]
   - Include: file path, function name (if applicable), line numbers, operation type (add/remove/modify/include)
   - Example: "Add subscription cleanup code to removeSession function in src/server/ua_session_manager.c (lines 37-42) - this should execute BEFORE UA_Session_detachFromSecureChannel"

2. [Second fix point description]
   - Same format as above

...
</fix_points>

"""


    
    @staticmethod
    def get_initial_fix_prompt(buggy_code: str, bug_location: str, 
                               context: Optional[str] = None,
                               fixed_code: Optional[str] = None,
                               fix_point_description: Optional[str] = None) -> str:
        """
        生成初始修复提示词
        用于为单个位置生成初步修复方案
        
        Prompt for generating initial fix for a single location
        
        Args:
            buggy_code: 该位置的漏洞代码
            bug_location: 位置标识符
            context: 额外上下文信息（例如来自grep的结果）
            fixed_code: 修复后的代码（用于对比分析，已废弃）
            fix_point_description: 修复点描述（明确说明需要做什么修复）
            
        Returns:
            格式化后的提示词字符串
        """
        # Extract vulnerability descriptions
        actual_descriptions = []
        if "Vulnerability Details:" in bug_location:
            vuln_section = bug_location.split("Vulnerability Details:")[1] if "Vulnerability Details:" in bug_location else ""
            if vuln_section:
                desc_pattern = r'Description:\s+(.+?)(?=\n\s*\d+\.|$)'
                matches = re.findall(desc_pattern, vuln_section, re.DOTALL)
                actual_descriptions = [m.strip() for m in matches]
        
        # Build mandatory requirements section
        mandatory_requirements = []
        
        # Fix point description requirement (highest priority)
        if fix_point_description:
            mandatory_requirements.append(f"""
## ⚠️ CRITICAL REQUIREMENT - Fix Point Description:
**YOU MUST follow this fix point description EXACTLY:**

{fix_point_description}

**Your Task:**
- Generate the fix code EXACTLY as described in the fix point description above
- If the description says "add header include", generate ONLY the include directive
- If the description says "add code to function X", generate ONLY the code for function X
- If the description says "remove code from function Y", generate ONLY the removal for function Y
- DO NOT generate fixes for other fix points
- DO NOT infer additional fixes beyond what is described
- DO NOT modify code that is not mentioned in the description

**Example**: If the description says "Add subscription header include to ua_session_manager.c (lines 1-10)", 
you should generate ONLY: `#include "ua_subscription.h"` at the appropriate location.
""")
        
        # Vulnerability description requirement
        if actual_descriptions:
            desc_list = "\n".join([f"- '{desc}'" for desc in actual_descriptions])
            mandatory_requirements.append(f"""
## ⚠️ CRITICAL REQUIREMENT:
**YOU MUST explicitly quote ONE of these vulnerability descriptions:**
{desc_list}

**Example**: "As the vulnerability description states: 'Subscription cleanup should be added before detaching from SecureChannel'."
**DO NOT quote the prompt text. ONLY quote from the descriptions above.**
""")
        elif "Vulnerability Details:" in bug_location or "Description:" in bug_location:
            mandatory_requirements.append("""
## ⚠️ CRITICAL REQUIREMENT:
**YOU MUST explicitly quote the vulnerability description from "Vulnerability Details" section:**
- Quote the EXACT description text
- Use EXACT terms from the description
- Explain what it means: "This means [X] must happen BEFORE [Y]"
""")
        
        # Code analysis requirement (NO fixed_code provided - analyze based on vulnerability description)
        mandatory_requirements.append("""
## ⚠️ CRITICAL REQUIREMENT:
**YOU MUST analyze the buggy code and identify what needs to be fixed:**
- Say: "In the buggy code, I see [specific code] at [location]"
- Analyze: "This code should be [moved/removed/added] because [reason based on vulnerability description]"
- Identify: What should be REMOVED (-), ADDED (+), or MOVED
- **Note**: You do NOT have access to the correct fix code. You must reason about what the fix should be based on the vulnerability description.
""")
        
        # Grep results requirement
        if context:
            mandatory_requirements.append("""
## 📋 Optional - If you use grep results:
**If you reference grep results, use ACTUAL information:**
- Use EXACT line numbers from grep results
- Use EXACT file names from grep results
- Say: "As shown in the grep results at line [LINE] in [FILE]..."
**DO NOT make up line numbers or file names.**
""")
        
        mandatory_section = "\n".join(mandatory_requirements) if mandatory_requirements else ""
        
        # Build example code separately to avoid f-string issues with ->
        example_code = """Example:
-    UA_Subscription *sub, *tempsub;
-    LIST_FOREACH_SAFE(sub, &session->serverSubscriptions, listEntry, tempsub) {
-        UA_Session_deleteSubscription(server, session, sub->subscriptionId);
-    }
+
+    /* Remove the Subscriptions */
+#ifdef UA_ENABLE_SUBSCRIPTIONS
+    UA_Subscription *sub, *tempsub;
+    LIST_FOREACH_SAFE(sub, &sentry->session.serverSubscriptions, listEntry, tempsub) {
+        UA_Session_deleteSubscription(sm->server, &sentry->session, sub->subscriptionId);
+    }
+#endif"""
        
        # Build context sections
        context_section = ""
        if context:
            context_section = f"""
## Grep Results:
{context}
"""
        
        # Do NOT provide fixed_code - only provide it during validation
        # code_comparison_section = ""  # Removed - fixed_code not provided in initial fix
        
        # Vulnerability context
        vulnerability_context = ""
        if "Vulnerability Details:" in bug_location or "Description:" in bug_location:
            vulnerability_context = """
## Key Understanding:
- "should be added before [X]" → Move code to execute BEFORE X
- "removed from..." → Code is in wrong location/timing
- Focus on EXECUTION ORDER and resource dependencies
- Child resources must be cleaned up BEFORE parent resources
"""
        
        return f"""You are analyzing a MEMORY ACCESS vulnerability. Generate a fix by understanding code movement and execution order.

{mandatory_section}

## Patch Format:
- Lines with "-" = REMOVED (buggy code)
- Lines with "+" = ADDED (fixed code)
- No prefix = context (unchanged)

## Vulnerability Context:
{vulnerability_context}

## Bug Location:
{bug_location}

## Buggy Code:
```c
{buggy_code}
```
{context_section}

## Analysis Focus:
- Use-after-free: accessing memory after it's freed
- Buffer overflow/underflow: array bounds violations
- Null pointer dereference: accessing through null pointers
- Resource release order: what must be cleaned up before what


**Note**: Grep is optional, but if you are uncertain about a definition, signature, or file/line context, you SHOULD issue a grep command to confirm before writing code. The buggy_code and vulnerability description are provided, but use grep when you need more certainty.
## Grep Tool (Optional but recommended ):
Use `<grep_command>grep -rn "pattern" src/</grep_command>` when you need to:
- Verify function names or variable names (prevent typos/encoding issues)
- Find where a function/variable is defined or how it is used
- Locate the correct file/line context before writing the fix
**Examples (adjust pattern/file as needed):**
- `<grep_command>grep -rn "UA_Session_deleteSubscription" src/</grep_command>`
- `<grep_command>grep -rn "removeSession" src/server/ua_session_manager.c</grep_command>`
- `<grep_command>grep -rn "serverSubscriptions" src/</grep_command>`



## Response Format:
<thinking>
[Your step-by-step analysis. YOU MUST include:
1. Quote vulnerability description: "As the vulnerability description states: '[exact quote]'"
2. Analyze buggy code: "In the buggy code, I see [code] at [location]. This should be [moved/removed/added] because [reason]"
3. (Optional) Reference grep results if provided: "As shown in the grep results at line X-Y in file.c..."
]
</thinking>

<fix>
[Your proposed fix code in DIFF FORMAT - YOU MUST provide actual code, NOT text description:
- Lines to REMOVE: prefix with "-"
- Lines to ADD: prefix with "+"
- Context lines: no prefix

{example_code}

**CRITICAL REQUIREMENTS:**
1. **DO NOT provide text descriptions** like "The fix involves moving...". YOU MUST provide actual code in diff format.
2. **FIX COMPLETENESS**: Your fix MUST be complete and address all aspects mentioned in the vulnerability description. If the description mentions multiple operations (e.g., subscription cleanup AND publish request cleanup), your fix MUST include ALL.
3. **Analyze carefully**: Based on the vulnerability description, ensure your fix addresses all related issues.

**LOGIC CONSISTENCY CHECK:**
- When describing code movement, ensure your description matches the actual fix
- If you say "moved from X to Y", verify that X and Y are correct
- If the fix ensures something happens "before" another thing, your description should say "before", not "after"
</fix>

**FINAL CHECKLIST:**
✓ Did I quote the vulnerability description with exact terms?
✓ Did I analyze the buggy code and identify what needs to be fixed?
✓ Did I provide ACTUAL CODE in <fix> section (not text description)?
✓ Did I ensure the fix addresses the vulnerability described?
If ANY answer is NO, my response is INCOMPLETE.
"""
    
    @staticmethod
    def get_fix_validation_prompt(generated_fix: str, ground_truth_fix: str, 
                                  bug_location: str) -> str:
        """
        生成修复验证提示词
        用于将模型生成的修复与标准答案进行对比验证
        
        Prompt for validating generated fix against ground truth
        
        Args:
            generated_fix: 模型生成的修复代码
            ground_truth_fix: 数据集中的正确修复代码
            bug_location: 位置标识符
            
        Returns:
            格式化后的提示词字符串
        """
        return f"""You are reviewing a code fix for a MEMORY ACCESS vulnerability. A model has generated a fix attempt, and you need to compare it with the correct fix.

Bug Location: {bug_location}

Generated Fix:
```c
{generated_fix}
```

Correct Fix:
```c
{ground_truth_fix}
```

Your task is to analyze whether the generated fix correctly addresses the MEMORY ACCESS vulnerability. Focus on:
- Does it fix the memory safety issue? (use-after-free, buffer overflow, etc.)
- Is the resource release order correct?
- Are pointers handled safely?
- Is memory accessed only when valid?

If it is incorrect, provide REFLECTIVE HINTS (not direct solutions) that would guide the model to discover the correct fix on its own.

Important guidelines:
- DO NOT directly provide the correct fix
- DO provide hints about what aspects to reconsider
- DO point out what the model might have missed about memory safety
- DO suggest areas to investigate further (resource dependencies, cleanup order, pointer lifecycle)
- Focus on memory access patterns and resource release order
- Use reflective language like "Have you considered...", "What about...", "Maybe you should think about..."

If the fix is correct, simply state that it is correct.

Format your response as:
<review>
[Your review and hints]
</review>

<correct>
[yes/no]
</correct>
"""
    
    @staticmethod
    def get_iterative_reflection_prompt(previous_thinking: str, 
                                       buggy_code: Optional[str] = None,
                                       fixed_code: Optional[str] = None,
                                       validation_hints: Optional[str] = None,
                                       grep_results: Optional[str] = None) -> str:
        """
        生成迭代反思提示词
        用于在已有思考链基础上进行迭代改进和反思
        核心作用：根据验证反馈（validation_hints）和当前思维链（previous_thinking）进行迭代改进
        
        Prompt for iterative reflection and improvement based on validation feedback and current thinking chain
        
        Args:
            previous_thinking: 之前的思考链（当前思维链状态）
            buggy_code: 原始有漏洞的代码
            fixed_code: 修复后的代码（GROUND TRUTH - 用于对比分析）
            validation_hints: 验证反馈的提示（评价对比模型给出的生成修复验证指导）
            grep_results: grep命令的结果（如果有）
            
        Returns:
            格式化后的提示词字符串
        """
        # Do NOT provide fixed_code in iterative reflection - only validation feedback contains comparison
        # Ground truth is only available during validation stage
        
        # 构建验证反馈部分
        hints_section = ""
        if validation_hints:
            hints_section = f"""
## Validation Feedback:
{validation_hints}

**Note**: This feedback compares your generated fix with the ground truth. Use it to guide your reflection.
"""
        
        # Build sections (concise)
        grep_section = ""
        if grep_results:
            grep_section = f"""
## Grep Results (Optional Context):
{grep_results}
"""
        
        # Check what's missing from previous thinking
        has_vuln_ref = "As the" in previous_thinking and ("description states" in previous_thinking or "vulnerability description" in previous_thinking)
        has_code_comp = "In the buggy code" in previous_thinking  # no fixed code comparison in reflection
        has_fix_tag = "[Final Fix]" in previous_thinking or "<fix>" in previous_thinking
        
        # Build missing requirements reminder
        missing_requirements = []
        
        if not has_fix_tag:
            missing_requirements.append("""
## ⚠️ CRITICAL MISSING: You did NOT provide <fix> tag in your previous response!
**YOU MUST provide <fix> tag with actual code NOW:**
- This is a MANDATORY requirement
- You MUST include <fix> tag with DIFF format code in this response
**If you do NOT include <fix> tag, your response is INVALID.**
""")
        
        if not has_vuln_ref:
            missing_requirements.append("""
## ⚠️ MISSING: You have NOT quoted the vulnerability description yet!
**YOU MUST add this NOW:**
- Say: "As the vulnerability description states: '[exact quote from Bug Location section]'"
- Use EXACT terms from the description
- Explain: "This means [X] must happen BEFORE [Y]"
""")
        
        if not has_code_comp:
            missing_requirements.append("""
## ⚠️ MISSING: You have NOT analyzed the buggy code yet!
**YOU MUST add this NOW:**
- Say: "In the buggy code, I see [code] at [location]"
- Analyze: "This code should be [moved/removed/added] because [reason based on vulnerability description]"
- Explain: "The code needs to be moved from X to Y because [reason]"
""")
        
        missing_section = "\n".join(missing_requirements) if missing_requirements else ""
        
        # Grep requirement
        grep_requirement = ""
        if grep_results:
            grep_requirement = """
## 📋 Optional - If you use grep results:
**If you reference grep results, use ACTUAL information with line numbers:**
- Say: "As shown in the grep results at line X-Y in file.c..."
- Quote specific code from grep results
- Reference file names and line numbers
"""
        
        return f"""Continue analyzing the MEMORY ACCESS vulnerability. Build upon your previous thinking and address any feedback provided.

**Core Purpose of This Iteration:**
You are iteratively improving your analysis and fix based on:
1. **Validation Feedback** (if provided): Review feedback from the evaluation model that compares your fix with the ground truth
2. **Your Previous Thinking**: Build upon and refine your current thinking chain
3. **Missing Requirements**: Address any missing elements identified in your previous response

**Important**: You do NOT have direct access to the correct fix code. You must reason about improvements based on:
- The vulnerability description
- Your previous analysis
- Validation feedback (if provided) - which contains hints about what might be missing or incorrect

**Grep when uncertain**: If you are unsure about a function/variable definition, signature, or file/line context, issue a grep command to confirm (e.g., `<grep_command>grep -rn "removeSession" src/server/ua_session_manager.c</grep_command>`).

{missing_section}
{grep_requirement}

## Your Previous Thinking:
{previous_thinking}
{hints_section}
{grep_section}

## Continue Your Analysis:
- Use present tense, think aloud
- Use phrases: "Wait, let me reconsider...", "Actually, thinking about this more..."
- Focus on memory safety: use-after-free, buffer overflow, resource release order
- Consider: when is memory valid? when does it become invalid? what is correct cleanup order?
- **If validation feedback is provided, carefully address the points raised**
- **Use validation feedback to guide your improvements** - it contains hints about what might be missing or incorrect

## 🔍 Grep Tool (Optional):
Use `<grep_command>grep -rn "pattern" src/</grep_command>` when you need to:
- Verify function names (prevent typos and character encoding errors)
- Check function usage patterns
- Find related code

**Note**: Grep is optional - use it when helpful. The previous thinking and validation feedback may already contain needed information.

## Response Format:
<thinking>
[Your continued thinking. If you see "MISSING" sections above, you MUST add those requirements NOW:
1. Quote vulnerability description: "As the vulnerability description states: '[exact quote]'"
2. Analyze buggy code: "In the buggy code, I see... This should be..."
3. (Optional) Reference grep results: "As shown at line X-Y..." (if grep results provided and helpful)
4. If validation feedback is provided, address the points raised and improve your fix accordingly
]
</thinking>

<fix>
[Your updated fix code in DIFF FORMAT - YOU MUST provide actual code, NOT text description:
- Lines to REMOVE: prefix with "-"
- Lines to ADD: prefix with "+"
- Context lines: no prefix

**CRITICAL REQUIREMENTS:**
1. **DO NOT provide text descriptions** like "The fix involves moving...". YOU MUST provide actual code in diff format.
2. **FIX COMPLETENESS**: Your fix MUST be complete and address all aspects mentioned in the vulnerability description and validation feedback (if provided). If the description mentions multiple operations, your fix MUST include ALL.
3. **Address validation feedback**: If validation feedback is provided, ensure your fix addresses all points raised.

**LOGIC CONSISTENCY CHECK:**
- Verify your description matches the actual fix code
- If you describe "moved from X to Y", ensure X and Y are correct
- If the fix ensures something happens "before" another thing, your description must say "before", not "after"
</fix>

## ⚠️ MANDATORY - YOU MUST INCLUDE <fix> TAG:
**EVERY response MUST include a <fix> tag with actual code in DIFF format.**
**If your previous response did not include <fix>, you MUST include it NOW.**
**Responses without <fix> tag will be rejected and iteration will continue.**

**FINAL CHECK:**
✓ Did I address all "MISSING" requirements above?
✓ Did I provide ACTUAL CODE (not text description)?
✓ Did I include <fix> tag?
✓ **FIX COMPLETENESS**: Did I include ALL related code changes? (Check vulnerability description and validation feedback - if they mention multiple operations, include ALL)
✓ **LOGIC CONSISTENCY**: Does my description match the fix code? (Verify "before"/"after" descriptions match actual code placement)
If ANY answer is NO, my response is INCOMPLETE.
"""
    
    @staticmethod
    def get_merge_thinking_chain_prompt(fix_points: list, thinking_chains: Dict[str, str], 
                                       final_fix_codes: Dict[str, Optional[str]] = None) -> str:
        """
        生成合并思考链提示词
        用于将多个独立的思考链合并成一个完整的推理过程
        
        Prompt for merging individual thinking chains into a complete chain
        
        Args:
            fix_points: 修复点标识符列表
            thinking_chains: 修复点到其思考链的映射字典
            final_fix_codes: 修复点到最终修复代码的映射字典
            
        Returns:
            格式化后的提示词字符串
        """
        # 将所有修复点的思考链组合成文本
        chains_text_parts = []
        for i, fp in enumerate(fix_points):
            chain_text = f"Fix Point {i+1}: {fp}\n{thinking_chains.get(fp, '')}"
            # Add final fix code if available
            if final_fix_codes and fp in final_fix_codes and final_fix_codes[fp]:
                chain_text += f"\n\n[Final Fix Code for this fix point]:\n{final_fix_codes[fp]}"
            chains_text_parts.append(chain_text)
        
        chains_text = "\n\n".join(chains_text_parts)
        
        return f"""You are synthesizing multiple thinking chains into one coherent, complete reasoning process.

You have analyzed and fixed multiple locations in the code. Now, merge all these individual thinking processes into a single, unified reasoning chain that shows how you approached the entire repair problem.

Individual Thinking Chains (with final fix codes):
{chains_text}

Please create a merged thinking chain that:
1. Shows the overall problem understanding
2. Demonstrates how you identified the need to fix multiple locations
3. Shows the logical flow between different fix points
4. Maintains the reflective, thinking-aloud style
5. Uses present tense throughout
6. **Includes the final fix codes** for each fix point in the merged chain

Format your response as:
<complete_thinking>
[Your merged, complete thinking chain - MUST include final fix codes]
</complete_thinking>
"""
    
    @staticmethod
    def get_perplexity_optimization_prompt(thinking_chain: str, 
                                          high_perplexity_segments: list) -> str:
        """
        生成困惑度优化提示词
        用于优化思考链中困惑度较高的片段，使其更清晰连贯
        
        Prompt for optimizing high perplexity segments in thinking chain
        
        Args:
            thinking_chain: 当前的思考链
            high_perplexity_segments: 高困惑度片段列表
            
        Returns:
            格式化后的提示词字符串
        """
        # 将高困惑度片段组合成文本（每个片段只显示前100个字符）
        segments_text = "\n".join([
            f"Segment {i+1}: {seg[:100]}..."
            for i, seg in enumerate(high_perplexity_segments)
        ])
        
        return f"""You are refining a thinking chain. Some segments have been identified as needing improvement for clarity and coherence.

Current Thinking Chain:
{thinking_chain}

Segments Needing Refinement:
{segments_text}

Please refine these segments to make them more coherent and natural, while:
1. Maintaining the overall meaning and logic
2. Keeping the reflective, thinking-aloud style
3. Preserving critical technical details
4. Using present tense
5. Making the flow more natural

IMPORTANT INSTRUCTIONS:
- DO NOT include any markers like "Refined segment:", "Refined Segment:", or similar labels in your output
- DO NOT repeat the prompt instructions in your response
- DO NOT include meta-commentary about the refinement process
- Simply provide the refined text directly, as if it were the original thinking chain
- Write naturally and seamlessly, as if you are continuing the original thought process

Provide the refined thinking chain.

Format your response as:
<refined_thinking>
[Your refined thinking chain - write directly, no markers or meta-commentary]
</refined_thinking>
"""


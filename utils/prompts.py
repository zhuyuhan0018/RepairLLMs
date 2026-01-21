"""
代码修复系统的提示词模板
Prompt templates for the code repair system
"""
import re
from typing import Dict, Optional, List


class PromptTemplates:
    """
    提示词模板集合类
    包含代码修复流程各个阶段所需的提示词模板
    Collection of prompt templates for different stages
    """
    
    @staticmethod
    def get_repair_order_analysis_prompt(buggy_code: str, bug_location: str, 
                                        fix_points: Optional[List[Dict]] = None) -> str:
        """
        生成修复顺序分析提示词
        用于分析需要修复的位置及其逻辑顺序（哪些函数/文件需要先修复）
        
        Prompt for analyzing repair order (which functions/files to fix first)
        
        Args:
            buggy_code: 原始有漏洞的代码
            bug_location: 漏洞位置（文件/函数），可能包含详细的文件、函数和行号信息
            fix_points: 修复点列表（可选），格式为 [{"id": 1, "file": "...", "function": "...", "line_start": X, "line_end": Y}, ...]
                       如果提供，将直接从 JSON 读取；否则从 bug_location 中的 "Vulnerability Details" 提取
            
        Returns:
            格式化后的提示词字符串
        """
        # Build fix points section from fix_points parameter (preferred) or bug_location (fallback)
        fix_points_section = ""
        
        if fix_points:
            # Build "Vulnerability Details" format from fix_points JSON
            vuln_lines = []
            for fp in fix_points:
                file_path = fp.get('file', '')
                function_name = fp.get('function')
                if function_name is None:
                    function_name = 'None'
                line_start = fp.get('line_start', '')
                line_end = fp.get('line_end', '')
                vuln_lines.append(f"  {fp.get('id', len(vuln_lines) + 1)}. {file_path}:{function_name} (lines {line_start}-{line_end})")
            
            vuln_section = "\n".join(vuln_lines)
            fix_points_section = f"""
## Fix Points from JSON Input

The fix points are provided from the JSON `fix_points` array. **These correspond to the JSON format:**
- Each fix point has: `id`, `file`, `function` (or `null` for header includes), `line_start`, `line_end`
- Format below: `id. file_path:function_name (lines line_start-line_end)`
- If `function` is `null` in JSON, it appears as `None` below

**Your task is to:**
1. **Extract all fix points** from the list below
2. **Merge fix points** that are in the same file AND same function (see merging rules)
3. **Sort the merged fix points** according to the repair order rules (THIS IS THE CORE TASK)

**Fix Points from JSON:**
{vuln_section}

**Merging Rules (CRITICAL):**
- **Merge ONLY if**: Two or more fix points have the **same file path AND same function name**
  - Same file + same function → Merge into ONE fix point
  - Same file + `function: null` (both) → Merge into ONE fix point
- **Merged line range**: Use the combined range (min line_start to max line_end)
- **Do NOT merge if**:
  - Different files → Keep separate
  - Different functions → Keep separate
  - One has function name, one has `null` → Keep separate

**Merging Examples:**
- ✅ Merge: `file.c:funcA (lines 10-20)` + `file.c:funcA (lines 25-30)` → `file.c:funcA (lines 10-30)`
- ✅ Merge: `file.c:None (lines 5-10)` + `file.c:None (lines 12-15)` → `file.c:None (lines 5-15)`
- ❌ Do NOT merge: `file.c:funcA (lines 10-20)` + `file.c:funcB (lines 25-30)` → Keep as 2 separate fix points
- ❌ Do NOT merge: `file.c:funcA (lines 10-20)` + `file.c:None (lines 5-10)` → Keep as 2 separate fix points

---
"""
        elif "Vulnerability Details:" in bug_location:
            # Fallback: Extract from bug_location (for backward compatibility)
            vuln_section = bug_location.split("Vulnerability Details:")[1]
            fix_points_section = f"""
## Fix Points from JSON Input

The fix points are provided in the "Vulnerability Details" section below. **These correspond to the JSON `fix_points` array format:**
- Each fix point has: `id`, `file`, `function` (or `null` for header includes), `line_start`, `line_end`
- Format in "Vulnerability Details": `id. file_path:function_name (lines line_start-line_end)`
- If `function` is `null` in JSON, it appears as `None` in "Vulnerability Details"

**Your task is to:**
1. **Extract all fix points** from "Vulnerability Details" below
2. **Merge fix points** that are in the same file AND same function (see merging rules)
3. **Sort the merged fix points** according to the repair order rules (THIS IS THE CORE TASK)

**Fix Points from "Vulnerability Details":**
{vuln_section.strip()}

**Merging Rules (CRITICAL):**
- **Merge ONLY if**: Two or more fix points have the **same file path AND same function name**
  - Same file + same function → Merge into ONE fix point
  - Same file + `function: null` (both) → Merge into ONE fix point
- **Merged line range**: Use the combined range (min line_start to max line_end)
- **Do NOT merge if**:
  - Different files → Keep separate
  - Different functions → Keep separate
  - One has function name, one has `null` → Keep separate

**Merging Examples:**
- ✅ Merge: `file.c:funcA (lines 10-20)` + `file.c:funcA (lines 25-30)` → `file.c:funcA (lines 10-30)`
- ✅ Merge: `file.c:None (lines 5-10)` + `file.c:None (lines 12-15)` → `file.c:None (lines 5-15)`
- ❌ Do NOT merge: `file.c:funcA (lines 10-20)` + `file.c:funcB (lines 25-30)` → Keep as 2 separate fix points
- ❌ Do NOT merge: `file.c:funcA (lines 10-20)` + `file.c:None (lines 5-10)` → Keep as 2 separate fix points

---
"""
        
        return f"""Analyze repair order for a MEMORY ACCESS vulnerability. **SORTING IS THE CORE TASK** - you must sort the provided fix points in the correct logical order according to repair order rules.

---

## ⚠️ CRITICAL - Sorting Requirement

**YOU MUST SORT THE FIX POINTS - DO NOT OUTPUT THEM IN THE ORIGINAL JSON ORDER**

## ⚠️ CRITICAL - Output Format (NON-NEGOTIABLE)

**You MUST output ONLY a `<fix_points>` block.**

- Your response MUST contain exactly one `<fix_points>...</fix_points>` section
- Do NOT output `<thinking>` or any other tags
- Do NOT output free-form analysis text
- **Responses without `<fix_points>` will be treated as INVALID**

The fix points in the JSON input are provided in an arbitrary order (by `id`). **Your primary task is to sort them according to the repair order rules below.**

**Example of correct sorting:**
- If JSON provides: [Remove code, Header include, Add code, Call change]
- Correct sorted order: [Header include, Add code, Call change, Remove code]
- **Reason**: Header includes must come first, then add code before remove, then call changes, then remove code last

**You MUST:**
1. Extract all fix points from the JSON input
2. Merge fix points in the same file + same function (if any)
3. **Sort the merged fix points according to repair order rules** (THIS IS THE CORE TASK)
4. Output the sorted list in `<fix_points>` section (and NOTHING ELSE)

**You MUST NOT:**
- Output fix points in the original JSON order
- Skip the sorting step
- Ignore the repair order rules

---

## Input Information

The input follows this JSON structure:
- **bug_location**: Contains file paths, vulnerability type, root cause, fix goal
- **buggy_code**: The vulnerable code snippets from affected files
- **fix_points** (in JSON): Array of fix points with `id`, `file`, `function` (or `null`), `line_start`, `line_end`
  - The fix points are listed below in JSON order (by `id`), but you MUST sort them

### Bug Location:
{bug_location}

### Buggy Code:
```c
{buggy_code}
```

---{fix_points_section}
## Analysis Task

**Task 1: Merge fix points (if needed)**
- Review all fix points from the JSON input
- **Merge fix points** that are in the same file AND same function (or both have `function: null`)
- Merged fix points should cover the combined line range
- **Do NOT merge** fix points from different files or different functions

**Task 2: Sort merged fix points (CORE TASK)**
- **This is the most important task**
- Consider dependencies between fix points
- Follow the repair order rules below STRICTLY
- Ensure the order respects all dependencies
- **DO NOT output in the original JSON order**

---

## Key Understanding

- "should be added before [X]" → Code must execute BEFORE X
- "removed from..." → Code is in wrong location/timing
- Focus on EXECUTION ORDER and resource dependencies
- Each vulnerability location = a separate fix point
- **Call relationship changes are independent**: Even if you add code to function B, changing function A to call B is still a separate fix point

---

## Repair Order Rules (MUST follow in this EXACT order)

**These rules define the CORRECT order. You MUST sort fix points according to these rules:**

1. **Header includes first** (Priority 1 - HIGHEST)
   - Add #include directives before using types/functions from other files
   - **Example**: If a fix point is `file.c:None (lines 11-16)` and it's a header include, it MUST be first

2. **Add code to target function** (Priority 2)
   - If you need to add code to a function (e.g., add cleanup code to `target_function`), do this BEFORE changing call relationships
   - **Example**: Adding code to `target_function` must come before changing `caller_function` to call `target_function`

3. **Change call relationships** (Priority 3)
   - After the target function has the necessary code, change the call relationship
   - **This is a SEPARATE fix point** from adding code to the target function
   - **Example**: Changing `caller_function` to call `target_function` instead of directly calling `old_function`

4. **Remove old code** (Priority 4 - LAST)
   - Remove old code LAST, after new code is in place and calls are updated
   - **Example**: Removing cleanup code from `old_function` must be LAST

**Dependency principles:**
- Header dependencies: Include headers before using their types/functions
- Function dependencies: Add code to target function before changing call to it (but these are TWO separate fix points)
- Resource dependencies: Clean up child resources before parent resources

**Sorting Example (based on typical use-after-free fix):**
- **JSON order** (by id): [Remove code (id=1), Header include (id=2), Add code (id=3), Call change (id=4)]
- **Correct sorted order**: [Header include (id=2), Add code (id=3), Call change (id=4), Remove code (id=1)]
- **Why**: Headers first, then add code before remove, then change calls, then remove old code last

---

## Focus Areas

- **Memory safety**: use-after-free, buffer overflow, null pointer
- **Resource release order**: what must be cleaned up before what
- **Code movement**: why code is moved from one location to another

---

## Grep Tool (Optional but Recommended)

**Important**: You should actively decide whether to use grep tools. The buggy_code and vulnerability description are provided, but if you need more certainty about function names, variable names, definitions, or context, you SHOULD use grep.

**When to use grep:**
- Verify function names or variable names (prevent typos/encoding issues)
- Find where a function/variable is defined or how it is used
- Locate the correct file/line context before writing the fix
- Need the context of the file/line context to write the fix
- Uncertain about the exact signature or usage of a function/variable

**Grep result format:**
- When grep is executed, it returns the matching line PLUS 3 lines before and after for context
- This gives you a complete view of the code around the match
- Example: If grep finds a match at line 50, you'll see lines 47-53 (3 lines before, the match, 3 lines after)

**Usage format:**
```
<grep_command>grep -rn "pattern" src/</grep_command>
```

**How to use:**
1. In your `<thinking>` section, if you need more information, issue a grep command
2. The system will execute grep and return results with context
3. Use the grep results to inform your analysis
4. Reference the grep results in your analysis: "As shown in the grep results at line X-Y in file.c..."

**Example grep commands (adjust pattern/file as needed):**
- `<grep_command>grep -rn "function_name" src/</grep_command>`
- `<grep_command>grep -rn "variable_name" src/path/to/file.c</grep_command>`
- `<grep_command>grep -rn "type_name" src/</grep_command>`

---

## Response Format

<fix_points>
1. file_path:function_name (lines line_start-line_end)
   - Use exact format: "file_path:function_name (lines line_start-line_end)"
   - For header includes (function is null): "file_path:None (lines line_start-line_end)"
   - Examples:
     * "src/module/file.c:None (lines 5-10)" - header include (function is null)
     * "src/module/file.c:target_function (lines 20-30)" - function fix
     * "src/module/file.c:old_function (lines 40-50)" - function fix
     * "src/module/file.c:caller_function (lines 60-80)" - function fix

2. file_path:function_name (lines line_start-line_end)

3. file_path:function_name (lines line_start-line_end)

4. file_path:function_name (lines line_start-line_end)

...
[List ALL fix points after merging, in the CORRECT REPAIR ORDER (sorted according to repair order rules). Use the exact format above. Do not skip any. DO NOT output in the original JSON order.]
</fix_points>

**IMPORTANT REMINDERS:**
- Output ONLY `<fix_points>` (no extra text)
- **Merge same file + same function**: If two fix points are in the same file AND same function (or both have `function: null`), merge them into one
- **Do NOT merge different files or functions**: Only merge fix points that are in the same file AND same function
- **Sort according to repair order rules**: Follow the repair order rules STRICTLY - this is the core task
- **DO NOT output in original JSON order**: The JSON order (by `id`) is arbitrary - you MUST sort according to repair order rules
- **Include all fix points**: After merging, include all fix points from the JSON input in your sorted list

"""


    
    @staticmethod
    def get_initial_fix_prompt(buggy_code: str, bug_location: str, 
                               context: Optional[str] = None,
                               fixed_code: Optional[str] = None,
                               fix_point_description: Optional[str] = None,
                               all_fix_points: Optional[List[Dict]] = None,
                               current_fix_point_index: Optional[int] = None) -> str:
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
            all_fix_points: 所有修复点的排序列表（来自repair order analysis）
            current_fix_point_index: 当前修复点在排序列表中的索引（0-based）
            
        Returns:
            格式化后的提示词字符串
        """
        # Build context sections (grep results)
        context_section = ""
        if context:
            context_section = f"""
### Grep Results:
```
{context}
```
"""
        
        # Build repair order context section
        repair_order_section = ""
        if all_fix_points and current_fix_point_index is not None:
            total_fix_points = len(all_fix_points)
            current_position = current_fix_point_index + 1
            repair_order_section = f"""
---

## ⚠️ CRITICAL - Repair Order Context

**You are processing Fix Point {current_position} of {total_fix_points} in the repair sequence.**

**The repair order has been determined by repair order analysis. You MUST follow this order:**

"""
            for i, fp in enumerate(all_fix_points):
                fp_num = i + 1
                fp_location = fp.get('location', 'N/A')
                fp_desc = fp.get('description', 'N/A')
                if i == current_fix_point_index:
                    repair_order_section += f"**→ Fix Point {fp_num} (CURRENT): {fp_location}**\n"
                    repair_order_section += f"   Description: {fp_desc}\n"
                    repair_order_section += f"   **YOU ARE HERE - Generate fix for THIS fix point only**\n"
                else:
                    repair_order_section += f"- Fix Point {fp_num}: {fp_location}\n"
                    repair_order_section += f"  Description: {fp_desc}\n"
            
            repair_order_section += f"""
**Important:**
- Fix points are processed in the order shown above (determined by repair order analysis)
- You are currently at Fix Point {current_position}
- DO NOT generate fixes for other fix points (Fix Points {', '.join(str(i+1) for i in range(total_fix_points) if i != current_fix_point_index)})
- Focus ONLY on the current fix point
- The order ensures dependencies are respected (e.g., headers before code, add before remove)

---
"""
        
        # Build fix point description section
        fix_point_section = ""
        if fix_point_description:
            fix_point_section = f"""
---

## ⚠️ CRITICAL - Fix Point Description

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


---
"""
        
        # Build example code separately to avoid f-string issues with ->
        # Use unrelated C/C++ example to prevent model from copying the example
        # This example is about file operations, completely unrelated to the test case
        example_code = """Example diff format (for reference only, NOT related to your task):
-    FILE *fp = fopen(filename, "r");
-    char buffer[256];
-    fgets(buffer, sizeof(buffer), fp);
-    process_buffer(buffer);
-    fclose(fp);
+
+    FILE *fp = fopen(filename, "r");
+    if (fp == NULL) {
+        return -1;
+    }
+    char buffer[256];
+    if (fgets(buffer, sizeof(buffer), fp) != NULL) {
+        process_buffer(buffer);
+    }
+    fclose(fp);"""
        
        return f"""Generate a fix for a MEMORY ACCESS vulnerability. Analyze the buggy code and generate the fix code in diff format.

---

## Input Information

### Bug Location:
{bug_location}

### Buggy Code:
```c
{buggy_code}
```
{context_section}

---

## Critical Requirements

### 1. Repair Order Context (HIGHEST PRIORITY)
{repair_order_section if repair_order_section else "**No repair order context provided. Process this fix point independently.**"}

### 2. Fix Point Description
{fix_point_section if fix_point_section else "**No specific fix point description provided. Analyze based on vulnerability description.**"}

### 2. Code Analysis Requirement

**YOU MUST analyze the buggy code and identify what needs to be fixed:**
- Say: "In the buggy code, I see [specific code] at [location]"
- Analyze: "This code should be [moved/removed/added] because [reason based on vulnerability description]"
- Identify: What should be REMOVED (-), ADDED (+), or MOVED
- **Note**: You must reason about what the fix should be based on the vulnerability description and you can use grep tools .

### 3. Grep Tool Usage

**You should actively decide whether to use grep tools:**
- If you are uncertain about function names, variable names, or their definitions, USE grep to verify
- If you need to find where a function/variable is defined or how it is used, USE grep
- If you need more context about file/line locations, USE grep
- **Grep results will include the matching line PLUS 3 lines before and after for context**

**If you have grep results (from previous grep calls):**
- Use EXACT line numbers from grep results
- Use EXACT file names from grep results
- Say: "As shown in the grep results at line [LINE] in [FILE]..."
- **DO NOT make up line numbers or file names.**

**If you don't have grep results yet:**
- Consider using grep if you need more information
- Issue a grep command in your thinking if needed
- The system will execute grep and return results with context (3 lines before and after)

---

## Analysis Focus

- **Use-after-free**: accessing memory after it's freed
- **Buffer overflow/underflow**: array bounds violations
- **Null pointer dereference**: accessing through null pointers
- **Resource release order**: what must be cleaned up before what

---

## Grep Tool (Optional but Recommended)

**Important**: You should actively decide whether to use grep tools. The buggy_code and vulnerability description are provided, but if you need more certainty about function names, variable names, definitions, or context, you SHOULD use grep.

**When to use grep:**
- Verify function names or variable names (prevent typos/encoding issues)
- Find where a function/variable is defined or how it is used
- Locate the correct file/line context before writing the fix
- Need the context of the file/line context to write the fix
- Uncertain about the exact signature or usage of a function/variable

**Grep result format:**
- When grep is executed, it returns the matching line PLUS 3 lines before and after for context
- This gives you a complete view of the code around the match
- Example: If grep finds a match at line 50, you'll see lines 47-53 (3 lines before, the match, 3 lines after)

**Usage format:**
```
<grep_command>grep -rn "pattern" src/</grep_command>
```

**How to use:**
1. In your `<thinking>` section, if you need more information, issue a grep command
2. The system will execute grep and return results with context
3. Use the grep results to inform your analysis
4. Reference the grep results in your analysis: "As shown in the grep results at line X-Y in file.c..."

**Example grep commands (adjust pattern/file as needed):**
- `<grep_command>grep -rn "function_name" src/</grep_command>`
- `<grep_command>grep -rn "variable_name" src/path/to/file.c</grep_command>`
- `<grep_command>grep -rn "type_name" src/</grep_command>`

---

## Patch Format

- Lines with `-` = REMOVED (buggy code)
- Lines with `+` = ADDED (fixed code)
- No prefix = context (unchanged)

---

## Response Format

**Required structure:**

<thinking>
[Your step-by-step analysis. YOU MUST include:
1. Analyze buggy code: "In the buggy code, I see [code] at [location]. This should be [moved/removed/added] because [reason]"
2. (If needed) Issue grep commands: If you need more information about function names, variable names, or context, issue grep commands here
3. (If grep results available) Reference grep results: "As shown in the grep results at line X-Y in file.c..."
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
2. **FIX COMPLETENESS**: Your fix MUST be complete and address all aspects mentioned in the vulnerability description. If the description mentions multiple operations (e.g., resource cleanup AND related operations), your fix MUST include ALL.
3. **Analyze carefully**: Based on the vulnerability description, ensure your fix addresses all related issues.

**LOGIC CONSISTENCY CHECK:**
- When describing code movement, ensure your description matches the actual fix
- If you say "moved from X to Y", verify that X and Y are correct
- If the fix ensures something happens "before" another thing, your description should say "before", not "after"
</fix>

"""
    
    @staticmethod
    def get_fix_validation_prompt(generated_fix: str, fixed_code: Dict, 
                                  fix_point: Dict, bug_location: str) -> str:
        """
        生成修复验证提示词
        用于将模型生成的修复与标准答案进行对比验证
        
        Prompt for validating generated fix against ground truth
        
        Args:
            generated_fix: 模型生成的修复代码
            fixed_code: 完整的修复代码字典，包含所有文件的修复（格式：{file_path: {diff: ..., changes: [...]}}）
            fix_point: 修复点信息，包含文件路径、函数名、行号等
            bug_location: 位置标识符
            
        Returns:
            格式化后的提示词字符串
        """
        # Format fixed_code for display
        fixed_code_str = ""
        for file_path, file_info in fixed_code.items():
            fixed_code_str += f"\n\nFile: {file_path}\n"
            fixed_code_str += "Diff:\n"
            fixed_code_str += "```diff\n"
            fixed_code_str += file_info.get('diff', '')
            fixed_code_str += "\n```\n"
            if 'changes' in file_info:
                fixed_code_str += "Changes:\n"
                for change in file_info['changes']:
                    fixed_code_str += f"  - Lines {change.get('line_start', '?')}-{change.get('line_end', '?')}: {change.get('operation', '?')} - {change.get('context', 'N/A')}\n"
        
        # Extract fix point information
        fix_point_file = fix_point.get('file', '')
        fix_point_function = fix_point.get('function')
        fix_point_description = fix_point.get('description', '')
        
        return f"""You are reviewing a code fix for a MEMORY ACCESS vulnerability. A model has generated a fix attempt for a specific fix point, and you need to compare it with the correct fix.

Bug Location: {bug_location}

Fix Point Information:
- File: {fix_point_file}
- Function: {fix_point_function if fix_point_function else 'N/A'}
- Description: {fix_point_description}

Generated Fix:
```c
{generated_fix}
```

Complete Fixed Code (all files):
{fixed_code_str}

Your task:
1. **Identify the relevant fix**: From the "Complete Fixed Code" above, identify which part corresponds to the current fix point (based on file path, function name, and description).
2. **Compare**: Compare the generated fix with the relevant part of the correct fix.
3. **Analyze**: Determine if the generated fix correctly addresses the MEMORY ACCESS vulnerability for this specific fix point.

Focus on:
- Does it fix the memory safety issue? (use-after-free, buffer overflow, etc.)
- Is the resource release order correct?
- Are pointers handled safely?
- Is memory accessed only when valid?
- Does it match the correct fix for this specific fix point?

If it is incorrect, provide REFLECTIVE HINTS (not direct solutions) that would guide the model to discover the correct fix on its own.

Important guidelines:
- DO NOT directly provide the correct fix
- DO provide hints about what aspects to reconsider
- DO point out what the model might have missed about memory safety
- DO suggest areas to investigate further (resource dependencies, cleanup order, pointer lifecycle)
- Focus on memory access patterns and resource release order
- Use reflective language like "Have you considered...", "What about...", "Maybe you should think about..."
- If the fix point is in a specific file/function, make sure your hints are relevant to that location

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

**Grep when uncertain**: If you are unsure about a function/variable definition, signature, or file/line context, issue a grep command to confirm (e.g., `<grep_command>grep -rn "function_name" src/path/to/file.c</grep_command>`).

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


# 模型未使用Grep工具的原因分析

## 问题现象

从 `test5_1_3` 的debug信息可以看到：
- **所有3次迭代的 `grep_cmd` 都是 `null`**
- 模型完全没有使用grep工具来查找 `removeSession` 函数的定义和上下文
- 模型直接基于不完整的代码片段生成了错误的修复

## 当前Prompt中关于Grep的说明

### 位置1：初始修复Prompt (`get_initial_fix_prompt`)
```python
## 🔍 Grep Tool (Optional but recommended when unsure):
Use `<grep_command>grep -rn "pattern" src/</grep_command>` when you need to:
- Verify function names or variable names (prevent typos/encoding issues)
- Find where a function/variable is defined or how it is used
- Locate the correct file/line context before writing the fix

**Note**: Grep is optional, but if you are uncertain about a definition, signature, or file/line context, you SHOULD issue a grep command to confirm before writing code.
```

### 位置2：迭代反思Prompt (`get_iterative_reflection_prompt`)
```python
**Grep when uncertain**: If you are unsure about a function/variable definition, signature, or file/line context, issue a grep command to confirm (e.g., `<grep_command>grep -rn "removeSession" src/server/ua_session_manager.c</grep_command>`).
```

## 问题分析

### 1. Prompt表述不够强制

**问题**：
- 使用了 "Optional but recommended" - 这暗示grep是可选的
- 使用了 "if you are uncertain" - 但模型可能没有意识到自己不确定
- 没有明确说明在什么情况下**必须**使用grep

**影响**：
- 模型可能认为从提供的代码片段中已经足够理解
- 模型可能过度自信，没有意识到自己需要更多信息

### 2. 模型可能没有意识到自己不确定

**实际情况**：
- Fix Point 1的描述是"Add subscription cleanup code to removeSession function"
- 但提供的 `buggy_code` 片段主要包含 `UA_Session_deleteMembersCleanup` 的代码
- `removeSession` 函数在代码片段中只有部分定义，不完整

**模型的行为**：
- 模型看到了 `removeSession` 的部分代码，可能认为已经理解了
- 模型没有意识到需要查看完整的 `removeSession` 函数定义
- 模型没有意识到需要确认 `removeSession` 函数的参数、变量名等

### 3. Prompt没有针对Fix Point的特殊情况

**问题**：
- 当Fix Point描述中提到特定函数时（如"Add code to removeSession function"），应该**强制**模型先grep查找该函数
- 当前prompt是通用的，没有针对这种情况的特殊处理

### 4. 缺少明确的检查清单

**问题**：
- FINAL CHECKLIST中没有包含"Did I use grep to verify function definitions when needed?"
- 模型可能在检查清单时没有意识到需要使用grep

## 改进建议

### 1. 强化Grep的重要性

**修改前**：
```
## 🔍 Grep Tool (Optional but recommended when unsure):
```

**修改后**：
```
## 🔍 Grep Tool (STRONGLY RECOMMENDED - Use when in doubt):
**IMPORTANT**: If the fix point description mentions a specific function (e.g., "Add code to removeSession function"), you MUST use grep to find that function's complete definition before writing the fix.
```

### 2. 添加强制使用Grep的场景

在prompt中添加明确的场景说明：

```python
## When to Use Grep (MANDATORY in these cases):
1. **Fix Point mentions a specific function**: If the fix point description says "Add code to [function_name]" or "Modify [function_name]", you MUST grep for that function first
2. **Function location unclear**: If you're not sure which file contains the target function, grep first
3. **Variable names unclear**: If you see different variable names in different parts of the code, grep to verify
4. **Function signature unclear**: If you need to know function parameters or return type, grep first

**Examples of MANDATORY grep usage:**
- Fix Point says "Add code to removeSession function" → `<grep_command>grep -rn "removeSession" src/server/ua_session_manager.c</grep_command>`
- Fix Point says "Modify UA_Session_deleteMembersCleanup" → `<grep_command>grep -rn "UA_Session_deleteMembersCleanup" src/server/ua_session.c</grep_command>`
```

### 3. 改进FINAL CHECKLIST

添加grep相关的检查项：

```python
**FINAL CHECKLIST:**
✓ Did I quote the vulnerability description with exact terms?
✓ Did I analyze the buggy code and identify what needs to be fixed?
✓ **Did I use grep to verify function definitions when the fix point mentions a specific function?**
✓ Did I provide ACTUAL CODE in <fix> section (not text description)?
✓ Did I ensure the fix addresses the vulnerability described?
```

### 4. 在Fix Point描述解析时自动添加Grep提示

**建议**：在生成prompt时，如果检测到Fix Point描述中提到特定函数，自动在prompt中添加：

```python
## ⚠️ CRITICAL: This fix point mentions "removeSession" function
**You MUST use grep to find the complete definition of this function before writing the fix:**
`<grep_command>grep -rn "removeSession" src/server/ua_session_manager.c</grep_command>`

**Why?** The buggy_code snippet may not show the complete function. You need to see:
- Complete function signature (parameters, return type)
- All local variables used in the function
- The exact location where code should be added
```

### 5. 在迭代反思时强调Grep

当验证反馈指出错误时，在下一轮prompt中明确提示：

```python
## Previous Iteration Issues:
The validation feedback indicates your fix was incorrect. Common causes:
1. **Wrong function**: You may have modified the wrong function
2. **Missing context**: You may not have seen the complete function definition
3. **Wrong variable names**: You may have used incorrect variable names

**ACTION REQUIRED**: Before generating a new fix, use grep to verify:
- The correct function name and location
- The complete function definition
- The correct variable names used in that function
```

## 具体修改建议

### 修改1：强化初始修复Prompt中的Grep说明

在 `utils/prompts.py` 的 `get_initial_fix_prompt` 方法中：

```python
# 检测Fix Point描述中是否提到特定函数
fix_point_location = fix_point.get('location', '')
fix_point_desc = fix_point.get('description', '')

# 提取函数名（简单启发式）
function_mentions = []
if 'function' in fix_point_desc.lower():
    # 尝试提取函数名
    import re
    func_matches = re.findall(r'(\w+)\s+function', fix_point_desc, re.IGNORECASE)
    function_mentions.extend(func_matches)

grep_section = ""
if function_mentions:
    grep_section = f"""
## ⚠️ CRITICAL: This fix point mentions the following function(s): {', '.join(function_mentions)}
**YOU MUST use grep to find the complete definition of these function(s) before writing the fix.**

**Example grep commands:**
{chr(10).join([f'- `<grep_command>grep -rn "{func}" src/</grep_command>`' for func in function_mentions])}

**Why?** The buggy_code snippet may not show the complete function. You need to see:
- Complete function signature (parameters, return type)
- All local variables used in the function
- The exact location where code should be added/modified
- The correct variable names (e.g., `sentry->session` vs `session`)

**DO NOT proceed with the fix until you have grepped for the function definition.**
"""
else:
    grep_section = """
## 🔍 Grep Tool (STRONGLY RECOMMENDED):
Use `<grep_command>grep -rn "pattern" src/</grep_command>` when you need to:
- Verify function names or variable names (prevent typos/encoding issues)
- Find where a function/variable is defined or how it is used
- Locate the correct file/line context before writing the fix

**Note**: If you are uncertain about a definition, signature, or file/line context, you SHOULD issue a grep command to confirm before writing code.
"""
```

### 修改2：在FINAL CHECKLIST中添加Grep检查

```python
**FINAL CHECKLIST:**
✓ Did I quote the vulnerability description with exact terms?
✓ Did I analyze the buggy code and identify what needs to be fixed?
✓ **Did I use grep to verify function definitions when the fix point mentions a specific function?** (If fix point mentions a function name, you MUST grep first)
✓ Did I provide ACTUAL CODE in <fix> section (not text description)?
✓ Did I ensure the fix addresses the vulnerability described?
If ANY answer is NO, my response is INCOMPLETE.
```

## 预期效果

实施这些改进后：
1. **模型会更主动使用grep**：当Fix Point提到特定函数时，模型会被明确要求先grep
2. **减少误解**：模型会看到完整的函数定义，减少对函数签名、变量名的误解
3. **提高修复正确率**：模型会基于完整信息生成修复，而不是基于不完整的代码片段

## 总结

模型未使用grep的根本原因：
1. **Prompt不够强制**：使用了"Optional"等弱化表述
2. **模型没有意识到不确定**：模型可能认为从代码片段中已经足够理解
3. **缺少针对性的提示**：当Fix Point提到特定函数时，没有强制要求grep

改进方向：
1. 强化grep的重要性表述
2. 针对Fix Point描述中提到的函数，自动添加强制grep提示
3. 在检查清单中添加grep相关检查项
4. 在迭代反思时强调使用grep验证



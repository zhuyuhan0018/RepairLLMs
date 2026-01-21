# `get_repair_order_analysis_prompt` 各部分详细说明

## 概述

`get_repair_order_analysis_prompt` 用于生成修复顺序分析提示词，指导模型分析需要修复的位置及其逻辑顺序。该 prompt 的核心目标是：
1. 识别所有修复点（fix points）
2. 确定修复点的执行顺序
3. 分析修复点之间的依赖关系

---

## 第一部分：动态修复点数量检测（代码逻辑部分）

**位置**: 第 31-57 行（代码逻辑，不直接出现在 prompt 中）

**规定**:
- **自动检测**: 从 `bug_location` 中检测 "Vulnerability Details:" 部分
- **计数规则**: 使用正则表达式 `r'^\s*(\d+)\.'` 匹配所有编号项（格式：`1. file:function (lines X-Y)`）
- **生成警告信息**: 如果检测到 N 个修复点，生成一个 "CRITICAL" 警告部分，明确告知模型需要识别 N 个修复点

**作用**: 
- 确保模型知道期望的修复点数量
- 防止模型遗漏修复点
- 提供明确的修复点类型映射（头文件包含、代码添加、代码移除、调用关系改变）

---

## 第二部分：任务标题和核心目标

**位置**: 第 59 行

**规定**:
```
Analyze repair order for a MEMORY ACCESS vulnerability. Identify fix points and their logical order.
```

**规定内容**:
- **漏洞类型**: 明确这是 MEMORY ACCESS 漏洞（use-after-free、buffer overflow 等）
- **核心任务**: 
  1. 识别修复点（fix points）
  2. 确定逻辑顺序（logical order）

---

## 第三部分：Key Understanding（关键理解）

**位置**: 第 63-69 行

**规定**:

1. **语义映射规则**:
   - `"should be added before [X]"` → 代码必须在 X 之前执行
   - `"removed from..."` → 代码位置/时机错误

2. **分析焦点**:
   - **执行顺序**（EXECUTION ORDER）：代码执行的先后顺序
   - **资源依赖**（resource dependencies）：资源之间的依赖关系

3. **修复点定义**:
   - 每个漏洞位置描述 = 一个独立的修复点
   - 不能合并多个位置为一个修复点

**作用**: 帮助模型理解漏洞描述中的关键语义，正确识别修复需求。

---

## 第四部分：Input Information（输入信息）

**位置**: 第 72-80 行

**规定**:

### Bug Location（漏洞位置）
- **内容**: 完整的 `bug_location` 字符串
- **包含信息**: 
  - 文件路径
  - 函数名
  - 行号范围
  - 漏洞类型和描述
  - Root Cause（根本原因）
  - Fix Goal（修复目标）
  - Vulnerability Details（漏洞详情，包含所有修复点位置）

### Buggy Code（有漏洞的代码）
- **格式**: C 语言代码块（```c ... ```）
- **内容**: 完整的 `buggy_code` 字符串

**作用**: 为模型提供分析所需的所有输入信息。

---

## 第五部分：CRITICAL - Expected Fix Point Count（关键 - 期望修复点数量）

**位置**: 第 40-57 行（动态生成，如果检测到 "Vulnerability Details"）

**规定**:

1. **数量要求**:
   - 明确告知模型：Bug Location 中包含 N 个漏洞位置
   - **强制要求**: "YOU MUST identify ALL N fix point(s)"
   - **禁止遗漏**: "Do not miss any of them"

2. **修复点类型映射**:
   - 添加头文件包含 → 一个修复点
   - 添加代码 → 一个修复点
   - 移除代码 → 一个修复点
   - 改变调用关系 → 一个修复点

3. **数量匹配要求**:
   - 必须识别 N 个修复点（或非常接近 N）
   - 如果识别数量显著少于 N，说明遗漏了重要修复

**作用**: 
- 防止模型遗漏修复点
- 确保模型理解每个漏洞位置对应一个修复点
- 提供明确的期望值，减少识别错误

---

## 第六部分：Analysis Task（分析任务）

**位置**: 第 83-101 行

**规定**:

### 任务 1: How many fix points?（有多少修复点？）

**关键要求**:
- **CRITICAL**: 必须识别所有修复点，不能遗漏
- **映射规则**: 每个 "Vulnerability Details" 中的位置 = 一个修复点

**必须包含的修复点类型**:
1. **Header includes**: 添加 #include 指令
2. **Code additions**: 在函数中添加新代码
3. **Code removals**: 从函数中移除代码
4. **Call relationship changes**: 改变函数调用关系
5. **Function modifications**: 修改现有函数实现

**禁止行为**:
- ❌ 不能合并多个不同的修复为一个修复点
- ❌ 不能跳过看似微小的修复（如头文件包含）
- ❌ 如果 "Vulnerability Details" 列出 N 个位置，必须识别约 N 个修复点

### 任务 2: What is the repair order?（修复顺序是什么？）

**要求**:
- 考虑修复点之间的依赖关系
- 遵循修复顺序规则（见下文）
- 确保顺序尊重所有依赖关系

**作用**: 明确告诉模型需要完成的两个核心任务，并提供详细的指导。

---

## 第七部分：Focus Areas（关注领域）

**位置**: 第 105-111 行

**规定**:

模型在分析时应该关注以下方面：

1. **Memory safety（内存安全）**:
   - use-after-free（释放后使用）
   - buffer overflow（缓冲区溢出）
   - null pointer（空指针）

2. **Resource release order（资源释放顺序）**:
   - 什么必须在什么之前清理
   - 资源之间的依赖关系

3. **Dependencies（依赖关系）**:
   - 什么必须在什么之前完成
   - 修复点之间的依赖

4. **Code movement（代码移动）**:
   - 为什么代码从一个位置移动到另一个位置
   - 移动的原因和时机

**作用**: 指导模型关注正确的分析维度，确保分析全面且准确。

---

## 第八部分：Repair Order Rules（修复顺序规则）

**位置**: 第 114-133 行

**规定**: **必须按照以下顺序执行修复**（MUST follow in this order）

### 规则 1: Header includes first（头文件包含优先）
- **时机**: 如果代码使用了某个类型/函数，但文件没有包含其头文件
- **操作**: 首先添加 include 指令
- **原因**: 确保类型和函数定义可用

### 规则 2: Ensure target function is ready（确保目标函数就绪）
- **时机**: 如果调用关系改变涉及调用新/修改的函数
- **操作**: 在改变调用之前，确保目标函数有必要的代码
- **原因**: 避免调用不存在的函数

### 规则 3: Add before remove（先添加后移除）
- **时机**: 需要将代码从旧位置移动到新位置
- **操作**: **必须先添加**到新位置，然后从旧位置移除
- **原因**: 这是正确性的关键，确保代码在移除前已经存在

### 规则 4: Call relationship changes（调用关系改变）
- **时机**: 目标函数已经就绪后
- **操作**: 改变调用关系
- **示例**: 将函数调用从旧函数改为新函数

### 规则 5: Code removal（代码移除）
- **时机**: 新代码已就位，调用已更新后
- **操作**: 最后移除旧代码
- **原因**: 确保所有依赖都已更新

**作用**: 提供明确的修复顺序规则，确保修复过程不会破坏代码的正确性。

---

## 第九部分：Dependency Analysis Guidelines（依赖分析指南）

**位置**: 第 136-147 行

**规定**:

### Header dependencies（头文件依赖）
- **规则**: 如果代码使用其他文件的类型/函数 → 首先包含该头文件
- **原因**: 确保类型和函数定义可用

### Function dependencies（函数依赖）
- **规则**: 如果 "调用 X 而不是 Y"，且 X 需要添加代码 → 首先在 X 中添加代码，然后改变调用
- **原因**: 确保被调用的函数存在且正确

### Resource dependencies（资源依赖）
- **规则**: 什么资源必须在什么资源之前清理
- **示例**: 子资源必须在父资源之前清理
- **原因**: 避免释放后使用等内存安全问题

**作用**: 提供依赖分析的指导原则，帮助模型正确识别和排序修复点。

---

## 第十部分：Grep Tool（Grep 工具）

**位置**: 第 150-180 行

**规定**:

### 重要性
- **主动决策**: 模型应该主动决定是否使用 grep 工具
- **使用场景**: 当需要更多确定性时，应该使用 grep

### 何时使用 grep
1. 验证函数名或变量名（防止拼写错误/编码问题）
2. 查找函数/变量的定义或使用位置
3. 定位正确的文件/行上下文
4. 需要文件/行上下文来编写修复
5. 不确定函数/变量的确切签名或用法

### Grep 结果格式
- **上下文范围**: 匹配行 + 前后 3 行
- **示例**: 如果 grep 在第 50 行找到匹配，会显示第 47-53 行

### 使用方法
1. 在 `<thinking>` 部分，如果需要更多信息，发出 grep 命令
2. 系统执行 grep 并返回带上下文的结果
3. 使用 grep 结果来指导分析
4. 在分析中引用 grep 结果："As shown in the grep results at line X-Y in file.c..."

### 使用格式
```
<grep_command>grep -rn "pattern" src/</grep_command>
```

### 示例命令
- `<grep_command>grep -rn "function_name" src/</grep_command>`
- `<grep_command>grep -rn "variable_name" src/path/to/file.c</grep_command>`
- `<grep_command>grep -rn "type_name" src/</grep_command>`

**作用**: 允许模型主动获取更多代码上下文，提高分析的准确性。

---

## 第十一部分：Response Format（响应格式）

**位置**: 第 184-220 行

**规定**:

### 必需结构

#### 1. `<analysis>` 标签
**必须包含的内容**:
- **Count（计数）**: 识别了多少个修复点，以及为什么
- **Why each fix point is needed（为什么需要每个修复点）**: 解释每个修复点的必要性
- **What dependencies exist（存在什么依赖）**: 分析修复点之间的依赖关系
- **Why the identified order is correct（为什么识别的顺序是正确的）**: 解释修复顺序的合理性
- **数量匹配说明**: 如果 "Vulnerability Details" 列出 N 个位置，解释为什么识别了 M 个修复点（M 应该接近 N）

#### 2. `<fix_points>` 标签
**格式要求**:
- 每个修复点使用编号列表（1, 2, 3, 4, ...）
- 必须包含的信息：
  - 文件路径
  - 函数名（如果适用）
  - 行号范围
  - 操作类型（add/remove/modify/include）

**示例格式**:
1. "Add header include for type_name in src/path/to/file.c (lines X-Y)"
2. "Add cleanup code to target_function in src/path/to/file.c (lines X-Y) - this should execute BEFORE another_function"
3. "Remove old code from source_function in src/path/to/file.c (lines X-Y)"
4. "Change call relationship in caller_function in src/path/to/file.c (lines X-Y) - call new_function instead of old_function"

**重要提醒**:
- **列出所有修复点**: 不要跳过任何修复点
- **继续列出**: 如果还有更多修复点，继续编号
- **完整性**: 确保所有修复点都被列出

**作用**: 确保模型以结构化、完整的方式输出分析结果，便于后续解析和处理。

---

## 第十二部分：IMPORTANT REMINDERS（重要提醒）

**位置**: 第 217-220 行

**规定**:

1. **Count all fix points（计算所有修复点）**: 
   - 头文件包含、代码添加、代码移除、调用关系改变 - 所有都必须包含

2. **Do not merge distinct fixes（不要合并不同的修复）**: 
   - 每个不同的修复位置/操作 = 一个独立的修复点

3. **Match the count（匹配数量）**: 
   - 如果 "Vulnerability Details" 列出 N 个位置，应该识别约 N 个修复点

4. **Be thorough（要彻底）**: 
   - 仔细审查有漏洞的代码和漏洞描述，确保不遗漏任何修复点

**作用**: 在最后再次强调关键要求，确保模型不会遗漏修复点。

---

## 总结

`get_repair_order_analysis_prompt` 通过以下方式确保模型正确识别所有修复点并确定正确的修复顺序：

1. **明确的数量期望**: 通过动态检测和警告，明确告知模型期望的修复点数量
2. **全面的类型覆盖**: 明确列出所有修复点类型，防止遗漏
3. **严格的顺序规则**: 提供明确的修复顺序规则，确保修复过程不会破坏代码
4. **详细的依赖分析**: 指导模型分析修复点之间的依赖关系
5. **结构化的输出格式**: 要求模型以结构化方式输出，便于解析和验证
6. **工具支持**: 允许模型使用 grep 工具获取更多上下文

这些规定共同确保模型能够：
- ✅ 识别所有修复点（不遗漏）
- ✅ 正确排序修复点（遵循依赖关系）
- ✅ 提供详细的分析过程（便于理解和验证）





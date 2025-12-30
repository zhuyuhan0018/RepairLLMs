# P0 改进实施总结

## 实施时间
2025-12-19

## 改进目标
完成立即实施（P0）的三个强制要求：
1. 强制要求引用 grep 结果
2. 强制要求代码对比
3. 强制要求引用漏洞描述

## 修改文件

### 1. `utils/prompts.py`

#### 修改1：`get_initial_fix_prompt()` 函数
- **添加参数**：`fixed_code: Optional[str] = None`
- **添加强制要求1 - 引用 grep 结果**：
  - 当 `context`（grep 结果）存在时，添加 `grep_requirement` 部分
  - 要求模型必须：
    - 明确引用 grep 结果中的具体行号
    - 引用具体的代码内容
    - 分析 grep 结果中的代码上下文
    - 提供示例："As shown in line 41-43..."

- **添加强制要求2 - 代码对比**：
  - 当 `fixed_code` 存在时，添加 `code_comparison_section` 和 `code_comparison_requirement`
  - 要求模型必须：
    - 逐行对比 buggy_code 和 fixed_code
    - 识别被移除的代码（"-" 行）
    - 识别被添加的代码（"+" 行）
    - 识别被移动的代码（相同代码在不同位置）
    - 解释为什么代码被移动
    - 必须明确说明："In the buggy code, I see..." 和 "In the fixed code, I see..."

- **添加强制要求3 - 引用漏洞描述**：
  - 当 `bug_location` 包含漏洞描述时，添加 `vulnerability_requirement`
  - 要求模型必须：
    - 明确引用漏洞描述（使用引号）
    - 使用描述中的特定术语（subscription, SecureChannel, detach, before 等）
    - 解释描述的含义
    - 提供示例："As the description states: 'Subscription cleanup should be added before detaching from SecureChannel'"

#### 修改2：`get_iterative_reflection_prompt()` 函数
- **添加强制要求 - 引用 grep 结果**：
  - 当 `grep_results` 存在时，添加 `grep_requirement`
  - 要求模型在迭代阶段也必须引用 grep 结果的具体内容

### 2. `core/initial_chain_builder.py`

#### 修改：`build_fix_point_chain()` 方法
- **更新调用**：在调用 `get_initial_fix_prompt()` 时，传入 `fixed_code` 参数
- 确保初始分析阶段能够进行代码对比

## 改进效果

### 预期改进
1. **模型必须引用 grep 结果**：
   - 不再只是"看到了 grep 结果"
   - 必须引用具体的行号和代码内容
   - 必须分析 grep 结果中的代码上下文

2. **模型必须进行代码对比**：
   - 不再提供泛泛的分析
   - 必须明确说明 buggy_code 和 fixed_code 的差异
   - 必须理解代码移动的含义

3. **模型必须引用漏洞描述**：
   - 不再忽略漏洞描述中的关键信息
   - 必须使用描述中的特定术语
   - 必须解释术语之间的关系

### 关键改进点

#### 1. 强制要求 vs 建议
- **之前**：提示词只是"建议"或"推荐"使用 grep、对比代码、引用描述
- **现在**：使用 "CRITICAL REQUIREMENT - You MUST" 明确强制要求
- **效果**：模型无法忽略这些要求，必须在思维链中体现

#### 2. 具体示例
- 每个强制要求都提供了具体的示例
- 示例展示了如何正确引用 grep 结果、进行代码对比、引用漏洞描述
- 帮助模型理解期望的输出格式

#### 3. 条件触发
- grep 要求：只在有 grep 结果时触发
- 代码对比要求：只在有 fixed_code 时触发
- 漏洞描述要求：只在有漏洞描述时触发
- 避免在不必要的情况下添加冗余要求

## 测试建议

### 下一步测试
1. 运行 `test2_6_3` 或新的测试用例
2. 检查思维链中是否：
   - ✅ 引用了 grep 结果的具体行号和内容
   - ✅ 明确对比了 buggy_code 和 fixed_code
   - ✅ 引用了漏洞描述中的特定术语
   - ✅ 解释了术语之间的关系

### 验证指标
- **Grep 引用**：思维链中是否包含 "As shown in line X-Y..." 或类似的引用
- **代码对比**：思维链中是否包含 "In the buggy code..." 和 "In the fixed code..." 的对比
- **漏洞描述引用**：思维链中是否包含 "As the description states..." 或类似的引用
- **术语使用**：是否使用了漏洞描述中的特定术语（subscription, SecureChannel, detach, before 等）

## 技术细节

### 提示词结构
```
1. Vulnerability Emphasis (if vulnerability descriptions exist)
2. Vulnerability Requirement (MUST reference descriptions)
3. Buggy Code
4. Fixed Code (if provided)
5. Code Comparison Requirement (MUST compare)
6. Context (grep results, if provided)
7. Grep Requirement (MUST reference grep results)
8. Analysis instructions
```

### 强制要求格式
所有强制要求都使用以下格式：
```
CRITICAL REQUIREMENT - You MUST [action]:
You MUST:
1. **Specific action 1**
2. **Specific action 2**
3. **Specific action 3**

Example of proper reference:
[Concrete example]

DO NOT [negative instruction]
```

## 注意事项

1. **参数兼容性**：
   - `fixed_code` 参数是可选的（`Optional[str]`）
   - 如果未提供 `fixed_code`，代码对比要求不会触发
   - 这确保了向后兼容性

2. **条件触发**：
   - 所有强制要求都是条件触发的
   - 只有在相关信息存在时才添加要求
   - 避免在不必要的情况下添加冗余要求

3. **示例的重要性**：
   - 每个强制要求都提供了具体的示例
   - 示例展示了期望的输出格式
   - 帮助模型理解如何满足要求

## 总结

✅ **已完成**：
- 强制要求引用 grep 结果（初始分析和迭代阶段）
- 强制要求代码对比（初始分析阶段）
- 强制要求引用漏洞描述（初始分析阶段）

✅ **技术实现**：
- 修改了 `get_initial_fix_prompt()` 函数
- 修改了 `get_iterative_reflection_prompt()` 函数
- 更新了 `build_fix_point_chain()` 方法
- 所有修改都通过了语法检查

✅ **预期效果**：
- 模型必须在思维链中引用 grep 结果
- 模型必须进行代码对比
- 模型必须引用漏洞描述
- 提高思维链的质量和准确性

## 下一步

1. **运行测试**：使用新的提示词运行测试用例（如 `test2_6_3`）
2. **验证效果**：检查思维链是否满足三个强制要求
3. **分析结果**：如果效果不理想，进一步优化提示词
4. **迭代改进**：根据测试结果继续优化


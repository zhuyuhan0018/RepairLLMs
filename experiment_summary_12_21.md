# 实验情况总结报告

## 一、项目概述

### 1.1 项目目标
构建一个面向程序修复场景的大语言模型系统，使用逆向工程推理（Reverse-Engineered Reasoning, REER）范式，从已知的修复代码逆向构建思维链。

**核心应用场景**：代码修复，特别是内存访问相关的漏洞修复
- 数组访问问题（buffer overflow, out-of-bounds）
- 指针使用问题（null pointer dereference, invalid pointer）
- 指针释放问题（use-after-free, double free, memory leak）
- 资源释放顺序问题（incorrect cleanup sequence）

### 1.2 技术架构
- **初始思维链构建**：使用阿里云模型（qwen3-coder-plus）构建初始思维链
- **迭代优化**：使用本地模型（qwen2-5-32b-instruct）进行困惑度优化
- **工具集成**：集成 grep 工具，允许模型在代码库中搜索相关代码
- **多阶段处理**：修复顺序分析 → 单点修复 → 思维链合并 → 困惑度优化

---

## 二、系统实现

### 2.1 核心模块

#### **配置模块** (`config.py`)
- 本地模型路径：`/mnt/nvme/quan/LLM-Models/qwen2-5-32b-instruct/`
- 阿里云 API Key：`sk-6f811b7e2654469fb1760b9b87e174c7`
- 默认模型：`qwen3-coder-plus`（可通过环境变量 `ALIYUN_MODEL_NAME` 配置）
- 关键参数：
  - `MAX_ITERATIONS = 3`：每个修复点的最大迭代次数
  - `MAX_GREP_ATTEMPTS = 3`：每个迭代的最大 grep 尝试次数
  - `CLOUD_MAX_TOKENS = 512`：云模型生成的最大 token 数
  - `PERPLEXITY_THRESHOLD = 3.0`：困惑度优化阈值
  - `SKIP_LOCAL`：环境变量，设置为 "1" 可跳过本地模型和优化阶段

#### **模型模块** (`models/`)
- **`aliyun_model.py`**：阿里云模型包装器
  - 使用 `dashscope` SDK
  - 支持流式和非流式生成
  - 超时时间：600秒（10分钟）
  - 自动处理多种响应格式
  
- **`local_model.py`**：本地 Qwen2 模型包装器
  - 主要用于困惑度计算
  - 支持 CUDA 加速

#### **核心处理模块** (`core/`)
- **`initial_chain_builder.py`**：初始思维链构建
  - `analyze_repair_order()`：分析修复顺序，识别修复点
  - `build_fix_point_chain()`：为每个修复点构建思维链
  - `merge_thinking_chains()`：合并多个修复点的思维链
  - 集成 grep 工具，支持模型请求代码库搜索
  
- **`perplexity_optimizer.py`**：困惑度优化
  - `segment_thinking_chain()`：将思维链分段
  - `analyze_perplexity()`：计算每段的困惑度
  - `identify_high_perplexity_segments()`：识别高困惑度片段
  - `optimize_thinking_chain()`：优化高困惑度片段
  - `preserve_critical_parts()`：保护关键部分不被替换
  - `_cleanup_artifacts()`：清理输出中的标记和错误信息

- **`repair_pipeline.py`**：主流程编排
  - `process_repair_case()`：处理单个修复案例
  - `batch_process()`：批量处理
  - 支持跳过本地模型阶段（`SKIP_LOCAL=1`）

#### **工具模块** (`utils/`)
- **`grep_tool.py`**：Grep 工具集成
  - `extract_grep_command()`：从模型响应中提取 grep 命令（只接受 `<grep_command>` 标签中的命令）
  - `execute_grep()`：执行 grep 命令
    - 自动添加 `-C 2` 参数（上下各2行上下文）
    - 在指定的代码库路径中搜索
    - 格式化输出结果
  - `_format_grep_output()`：格式化 grep 输出，按文件组织结果
  
- **`prompts.py`**：提示词模板集合
  - `get_repair_order_analysis_prompt()`：修复顺序分析
  - `get_initial_fix_prompt()`：初始修复生成
  - `get_fix_validation_prompt()`：修复验证
  - `get_iterative_reflection_prompt()`：迭代反思
  - `get_merge_thinking_chain_prompt()`：思维链合并
  - `get_perplexity_optimization_prompt()`：困惑度优化

### 2.2 提示词设计特点

**所有提示词都专门针对内存访问漏洞**：
- 明确说明这是内存访问漏洞修复场景
- 详细列出需要关注的漏洞类型：
  - 数组访问问题（buffer overflow, out-of-bounds）
  - 指针使用问题（null pointer, invalid pointer）
  - 指针释放问题（use-after-free, double free）
  - 资源释放顺序问题
- 强调理解资源依赖和清理顺序
- 解释 patch 格式（`-` 表示删除，`+` 表示添加）

### 2.3 数据流程

1. **输入**：JSON 格式的测试用例
   - `buggy_code`：有漏洞的代码
   - `fixed_code`：修复后的代码
   - `bug_location`：漏洞位置
   - `codebase_path`：代码库路径（可选）
   - `vulnerability_locations`：详细的漏洞定位信息（可选）

2. **处理流程**：
   - 修复顺序分析 → 识别修复点
   - 对每个修复点：
     - 生成初始分析
     - 可选：执行 grep 命令获取上下文
     - 验证修复（与 ground truth 对比）
     - 迭代改进
   - 合并所有修复点的思维链
   - 困惑度优化（如果启用本地模型）

3. **输出**：
   - JSON 格式的思维链（`outputs/thinking_chains/`）
   - TXT 格式的思维链（`\n` 转换为实际换行）
   - 日志文件（`logs/`）

---

## 三、已完成的工作

### 3.1 系统搭建
- ✅ 完成项目结构搭建
- ✅ 实现所有核心模块
- ✅ 集成阿里云和本地模型
- ✅ 实现 grep 工具集成
- ✅ 实现困惑度优化流程

### 3.2 功能改进

#### **Grep 工具改进**
- ✅ 在代码库路径中搜索（而不是当前目录）
- ✅ 自动添加上下文（`-C 2`，上下各2行）
- ✅ 格式化输出（按文件组织，显示行号）
- ✅ 完整日志输出（所有结果完整显示，不再截断）
- ✅ 改进命令提取（只接受明确标记的命令，避免误解析）
- ✅ **修复格式化问题**（test2_6_2）：正确显示上下文行，用 `>>>` 标记匹配行，用 `---` 分隔不同匹配块

#### **提示词改进**
- ✅ 解释 patch 格式（`-` 和 `+` 的含义）
- ✅ 专门针对内存访问漏洞（通用化，不再专门针对 use-after-free）
- ✅ 强调数组访问、指针使用、指针释放
- ✅ 强调资源释放顺序的重要性
- ✅ 明确列出需要关注的漏洞类型
- ✅ **增强 grep 使用提示**（test2_5+）：强烈推荐模型使用 grep 获取代码上下文
- ✅ **通用化改进**（test2_5+）：移除特定漏洞类型检查，支持所有内存访问漏洞类型

#### **输入数据改进**
- ✅ 支持详细的漏洞定位信息（文件、函数、行号）
- ✅ 支持代码库路径配置
- ✅ 创建代码库下载工具（`scripts/download_codebase.py`）
- ✅ **添加漏洞元数据**（test2_5+）：支持 `vulnerability_type`、`root_cause`、`fix_goal` 字段
- ✅ **改进修复点识别**（test2_5+）：从详细的 `bug_location` 字符串中提取多个修复点

#### **日志系统改进**
- ✅ **详细阶段日志**（test2_6+）：每个阶段都有明确的日志输出
  - 修复顺序分析阶段
  - 修复点链构建阶段（初始分析、迭代、grep 执行等）
  - 思维链合并阶段
- ✅ **Grep 结果完整显示**（test2_6_2+）：显示完整的 grep 结果，包括所有上下文行
- ✅ **格式化改进**（test2_6_2+）：用 `>>>` 标记匹配行，用空格标记上下文行，用 `---` 分隔不同匹配块

### 3.3 测试用例

#### **test1**（已删除）
- 使用 `42470093.patch`（harfbuzz buffer overflow）
- 主要用于测试系统基本功能

#### **test2**（已删除）
- 使用 `42470745.patch`（open62541 use-after-free）
- 完整流程测试

#### **test2_2**
- 使用 `42470745.patch`（open62541 use-after-free）
- 完整流程测试（包括本地优化）
- 发现输出质量问题（"Refined segment:" 标记、grep 错误信息）

#### **test2_3**（已测试）
- 使用 `42470745.patch`（open62541 use-after-free）
- 包含详细的漏洞定位信息
- 只运行到初始思维链生成（跳过本地优化）
- 使用改进后的提示词和 grep 工具

#### **test2_5**（已测试）
- 使用 `42470745.patch`（open62541 use-after-free）
- 添加了 `vulnerability_type`、`root_cause`、`fix_goal` 字段
- 通用化提示词（不再专门针对 use-after-free）
- 改进了修复点识别逻辑

#### **test2_6**（已测试）
- 使用 `42470745.patch`（open62541 use-after-free）
- 增强了 grep 使用提示
- 添加了详细的阶段日志输出
- 修复了 grep 格式化问题（显示完整上下文）

#### **test2_6_2**（当前最新测试）
- 使用 `42470745.patch`（open62541 use-after-free）
- 修复了 grep 输出格式化问题（正确显示上下文行）
- 改进了日志输出格式（用 `>>>` 标记匹配行）
- 识别了 4 个修复点（可能略多）

---

## 四、测试结果分析

### 4.1 test2_3 第一轮结果（改进前）

**主要问题**：
1. ❌ **未识别出 use-after-free 漏洞**（0 次提及）
2. ❌ **未理解资源释放顺序**（0 次提及）
3. ❌ **误认为问题是"代码结构混乱"**
4. ❌ **修复代码方向错误**

**成功方面**：
- ✅ 理解了 patch 格式（9 次提及）
- ✅ 提供了修复代码（4 个 Final Fix）
- ✅ 使用了 grep 工具

**评估**：部分成功（60%），但核心问题未解决

### 4.2 test2_3 第二轮结果（改进后）

**改进点**：
- ✅ 理解了 patch 格式
- ✅ 提供了修复代码
- ✅ 使用了 grep 工具
- ✅ 提到了订阅清理（30 次）

**仍然存在的问题**：
- ❌ **未识别出 use-after-free**（0 次提及）
- ❌ **修复代码方向错误**：
  - fix_point_2：错误地把订阅清理放回 `UA_Session_deleteMembersCleanup`
  - fix_point_4：错误地保留了订阅清理代码
- ❌ **未理解资源释放顺序**（0 次提及）
- ❌ **仍认为问题是"代码结构混乱"**

**评估**：部分成功（60%），核心问题仍未解决

### 4.3 test2_5 结果（通用化提示词 + 漏洞元数据）

**改进点**：
- ✅ 识别了 3 个修复点（正确）
- ✅ 模型主动使用 grep 工具
- ✅ 提到了关键术语（subscription、SecureChannel、detach）

**仍然存在的问题**：
- ❌ **未充分利用 grep 结果**：虽然使用了 grep，但思维链中没有引用 grep 结果的具体内容
- ❌ **未理解代码移动**：没有对比 buggy_code 和 fixed_code，没有理解代码移动的含义
- ❌ **未理解关键修复点**：虽然提到了术语，但没有理解"在 detach 之前清理订阅"这个关键点
- ❌ **分析方向错误**：仍然认为问题是"在 free 之前 detach"

**评估**：部分改进（65%），核心问题仍未解决

### 4.4 test2_6 结果（增强 grep 提示 + 详细日志）

**改进点**：
- ✅ 识别了 3 个修复点（正确）
- ✅ 模型主动使用 grep 工具
- ✅ 详细的阶段日志输出，便于监控进度
- ⚠️ Grep 格式化问题：虽然显示了结果，但上下文行显示不完整

**仍然存在的问题**：
- ❌ **Grep 格式化问题**：上下文行显示不完整，模型无法看到完整的代码上下文
- ❌ **未充分利用 grep 结果**：思维链中没有引用 grep 结果的具体内容
- ❌ **未理解代码移动**：没有对比 buggy_code 和 fixed_code
- ❌ **未理解关键修复点**：分析方向仍然错误

**评估**：部分改进（70%），grep 格式化问题需要修复

### 4.5 test2_6_2 结果（修复 grep 格式化）

**成功方面**：
- ✅ **Grep 格式化问题已修复**：现在显示完整的上下文行（前后各2行）
- ✅ 用 `>>>` 标记匹配行，用空格标记上下文行，格式清晰
- ✅ 模型可以看到完整的代码上下文
- ✅ 识别了 4 个修复点（可能略多，但描述更准确）
- ✅ 提到了关键术语（subscription、SecureChannel、detach、before）

**仍然存在的问题**：
- ❌ **未充分利用 grep 结果**：虽然看到了完整的上下文，但思维链中没有引用 grep 结果的具体内容
- ❌ **仍未理解代码移动**：没有对比 buggy_code 和 fixed_code，没有理解代码移动的含义
- ❌ **未理解关键修复点**：虽然提到了术语，但没有理解它们之间的关系
- ❌ **分析方向错误**：仍然认为问题是"在 free 之前 detach"，而不是"在 detach 之前清理订阅"

**评估**：工具层面改进成功（85%），但模型理解层面仍需改进（60%）

### 4.6 关键发现

1. **工具层面改进有效**
   - Grep 格式化问题已修复
   - 详细日志输出有助于调试
   - 模型主动使用 grep 工具

2. **模型理解层面仍有问题**
   - 虽然看到了完整的代码上下文，但没有充分利用
   - 没有对比 buggy_code 和 fixed_code
   - 没有理解代码移动的含义
   - 分析方向仍然错误

3. **根本原因：缺乏强制要求**
   - 虽然提供了完整的工具和信息
   - 但模型没有被强制要求使用这些信息
   - 提示词只是"建议"或"推荐"，不是"要求"

---

## 五、当前系统状态

### 5.1 代码库下载
- ✅ 已下载 open62541 代码库（修复前版本）
- ✅ 位置：`datasets/codebases/open62541`
- ✅ 提供了下载工具：`scripts/download_codebase.py`

### 5.2 配置文件
- ✅ `config.py`：集中配置
- ✅ 支持环境变量覆盖
- ✅ 支持跳过本地模型阶段

### 5.3 输出目录结构
```
outputs/
├── thinking_chains/     # 初始思维链（JSON + TXT）
├── optimized_chains/    # 优化后的思维链（JSON + TXT）
└── analysis/            # 分析报告

logs/                    # 日志文件
test/                    # 测试用例
  ├── test2_2/
  └── test2_3/
```

### 5.4 关键文件
- `run_test2_5.py`、`run_test2_6.py`、`run_test2_6_2.py`：运行测试的脚本
- `scripts/download_codebase.py`：代码库下载工具
- `core/initial_chain_builder.py`：初始思维链构建
  - 已添加详细的阶段日志输出
  - 改进了修复点识别逻辑（从 `bug_location` 字符串中提取）
  - 改进了 grep 结果日志格式
- `utils/prompts.py`：提示词模板
  - 已通用化为所有内存访问漏洞类型
  - 增强了 grep 使用提示
  - 添加了 `vulnerability_type`、`root_cause`、`fix_goal` 参数支持
- `utils/grep_tool.py`：Grep 工具
  - 修复了格式化问题（正确显示上下文行）
  - 用 `>>>` 标记匹配行，用 `---` 分隔不同匹配块

---

## 六、已知问题和限制

### 6.1 核心问题

#### **问题1：未充分利用 grep 结果**（P0）
- **表现**：虽然模型使用了 grep 并看到了完整的代码上下文，但思维链中没有引用 grep 结果的具体内容
- **原因**：提示词只是"推荐"使用 grep，没有强制要求引用 grep 结果
- **影响**：模型看到了信息但没有在思维链中体现，无法验证是否真正理解

#### **问题2：未理解代码移动的含义**（P0）
- **表现**：没有对比 buggy_code 和 fixed_code，没有理解代码移动的含义
- **原因**：提示词没有强制要求代码对比，模型没有理解 patch 格式中代码移动的含义
- **影响**：无法理解修复的真正目标，分析方向错误

#### **问题3：未理解关键修复点**（P0）
- **表现**：虽然提到了关键术语（subscription、SecureChannel、detach），但没有理解它们之间的关系
- **原因**：提示词没有强制要求引用漏洞描述，没有强制要求解释关键术语之间的关系
- **影响**：分析方向错误（认为问题是"在 free 之前 detach"，而不是"在 detach 之前清理订阅"）

#### **问题4：修复点识别可能过多**（P1）
- **表现**：test2_6_2 识别了 4 个修复点（实际应该是 3 个）
- **原因**：可能将同一个修复点拆分成了多个
- **影响**：修复点描述可能不够准确

### 6.2 技术限制

1. **Grep 工具限制**
   - 只能搜索代码库中的代码
   - 无法执行复杂的代码分析
   - 上下文只有2行，可能不够

2. **模型能力限制**
   - 对内存安全问题敏感度不足
   - 推理深度有限
   - 容易停留在表面问题

3. **提示词限制**
   - 虽然已改进，但可能还需要更明确的指导
   - 需要更多示例和场景说明

---

## 七、改进方向

### 7.1 短期改进（P0 - 立即实施）

#### **改进1：强制要求引用 grep 结果**
```python
"""
CRITICAL: When you use grep and receive results, you MUST:
1. Explicitly reference the grep results in your thinking
2. Quote specific lines from the grep results (e.g., "As shown in line 41-43...")
3. Analyze the code context shown in the grep results
4. Use the information from grep results to understand the code structure

Example:
"As shown in the grep results, `UA_Session_deleteSubscription` is called at line 43 
in `ua_session.c`, within a loop that iterates through `session->serverSubscriptions`. 
The context shows that this is part of a cleanup process..."
"""
```

#### **改进2：强制要求代码对比**
```python
"""
CRITICAL: Before providing your analysis, you MUST:
1. Compare buggy_code and fixed_code line by line
2. Identify what code is REMOVED (lines with "-")
3. Identify what code is ADDED (lines with "+")
4. Identify what code is MOVED (same code in different locations)
5. Explain WHY the code is moved (what problem does this fix?)

You MUST explicitly state:
- "In the buggy code, I see subscription cleanup code at..."
- "In the fixed code, I see the same code moved to..."
- "The code is moved from X to Y because..."
"""
```

#### **改进3：强制要求引用漏洞描述**
```python
"""
CRITICAL: You MUST explicitly reference the vulnerability descriptions:
1. Quote the description: "As the description states: 'Subscription cleanup should be added before detaching from SecureChannel'"
2. Use the specific terms mentioned (subscription, SecureChannel, detach, etc.)
3. Explain what the description means: "This means subscriptions must be cleaned up BEFORE the SecureChannel is detached"
4. DO NOT provide generic analysis without mentioning these specific terms and their relationships
"""
```

### 7.2 中期改进（P1）

1. **改进验证机制**
   - 在验证时，检查是否引用了 grep 结果
   - 检查是否使用了漏洞描述中的关键术语
   - 检查是否理解了代码移动
   - 检查分析方向是否正确

2. **增加迭代次数**
   - 将 `MAX_ITERATIONS` 从 3 增加到 5
   - 给模型更多机会深入分析

3. **改进修复点识别**
   - 优化 `_parse_fix_points` 逻辑，避免识别过多修复点
   - 确保每个修复点都是独立的、非重复的

### 7.3 长期改进（P2）

1. **建立漏洞知识库**
   - 常见漏洞模式
   - 修复模式库
   - 成功案例库

2. **改进模型训练**
   - 针对代码修复任务专门训练
   - 提高对内存安全问题的敏感度
   - 提高推理能力

---

## 八、使用指南

### 8.1 运行测试

```bash
# 基本运行
cd /home/yuhan/work/RepairLLMs
python3 run_test2_3.py

# 带环境变量（推荐）
SKIP_LOCAL=1 ALIYUN_MODEL_NAME=qwen3-coder-plus MAX_ITERATIONS=2 CLOUD_MAX_TOKENS=512 python3 run_test2_3.py

# 保存日志
SKIP_LOCAL=1 python3 -u run_test2_3.py 2>&1 | tee logs/run_test2_3.log
```

### 8.2 下载代码库

```bash
python3 scripts/download_codebase.py <patch_file> [output_dir]
```

### 8.3 环境变量

- `SKIP_LOCAL=1`：跳过本地模型和困惑度优化
- `ALIYUN_MODEL_NAME=qwen3-coder-plus`：指定阿里云模型
- `MAX_ITERATIONS=2`：每个修复点的最大迭代次数
- `CLOUD_MAX_TOKENS=512`：云模型生成的最大 token 数

---

## 九、当前进度总结

### 9.1 已完成的工作

#### **工具层面** ✅
- ✅ Grep 工具格式化问题已修复（test2_6_2）
- ✅ 详细阶段日志输出已实现（test2_6+）
- ✅ 模型主动使用 grep 工具（test2_5+）
- ✅ 修复点识别逻辑已改进（test2_5+）

#### **提示词层面** ✅
- ✅ 提示词已通用化为所有内存访问漏洞类型（test2_5+）
- ✅ 增强了 grep 使用提示（test2_5+）
- ✅ 添加了漏洞元数据支持（test2_5+）

#### **数据层面** ✅
- ✅ 测试用例添加了 `vulnerability_type`、`root_cause`、`fix_goal` 字段（test2_5+）
- ✅ 改进了 `bug_location` 字符串的构建，包含详细的漏洞描述信息

### 9.2 当前状态

#### **成功方面** ✅
1. **工具层面改进成功**（85%）
   - Grep 格式化问题已修复
   - 详细日志输出有助于调试
   - 模型主动使用 grep 工具

2. **修复点识别改进**（80%）
   - 能够识别多个修复点
   - 修复点描述更准确

3. **关键术语使用改进**（60%）
   - 提到了关键术语（subscription、SecureChannel、detach）
   - 但未理解它们之间的关系

#### **仍然存在的问题** ❌
1. **未充分利用 grep 结果**（P0）
   - 虽然看到了完整的代码上下文，但思维链中没有引用
   - 需要强制要求引用 grep 结果

2. **未理解代码移动**（P0）
   - 没有对比 buggy_code 和 fixed_code
   - 需要强制要求代码对比

3. **未理解关键修复点**（P0）
   - 虽然提到了术语，但没有理解关系
   - 需要强制要求引用漏洞描述

4. **分析方向错误**（P0）
   - 仍然认为问题是"在 free 之前 detach"
   - 实际问题是"在 detach 之前清理订阅"

### 9.3 下一步计划

#### **立即实施**（P0）
1. 在提示词中强制要求引用 grep 结果
2. 在提示词中强制要求代码对比
3. 在提示词中强制要求引用漏洞描述

#### **测试验证**
1. 运行修复后的 test2_6_3，验证改进效果
2. 检查模型是否引用了 grep 结果
3. 检查是否理解了代码移动
4. 检查分析方向是否正确

---

## 十、关键文件位置

### 10.1 核心代码
- `core/initial_chain_builder.py`：初始思维链构建
- `core/perplexity_optimizer.py`：困惑度优化
- `core/repair_pipeline.py`：主流程
- `utils/prompts.py`：提示词模板
- `utils/grep_tool.py`：Grep 工具
- `models/aliyun_model.py`：阿里云模型
- `models/local_model.py`：本地模型

### 10.2 配置文件
- `config.py`：系统配置
- `test/test2_3/test2_3.json`：测试用例（test2_3）
- `test/test2_5/test2_5.json`：测试用例（test2_5，添加了漏洞元数据）
- `test/test2_6/test2_6.json`：测试用例（test2_6，增强 grep 提示）
- `test/test2_6_2/test2_6_2.json`：测试用例（test2_6_2，修复 grep 格式化）

### 10.3 输出文件
- `outputs/thinking_chains/`：初始思维链（JSON + TXT）
  - `test2_3_initial.json/txt`
  - `test2_5_initial.json/txt`
  - `test2_6_initial.json/txt`
  - `test2_6_2_initial.json/txt`
- `outputs/analysis/`：分析报告
  - `test2_6_2_analysis.md`：test2_6_2 详细分析报告
- `logs/`：运行日志
  - `run_test2_3.log`、`run_test2_3_2.log`
  - `run_test2_5.log`、`run_test2_5_2.log`
  - `run_test2_6.log`
  - `run_test2_6_2.log`

### 10.4 工具脚本
- `scripts/download_codebase.py`：代码库下载工具
- `run_test2_5.py`、`run_test2_6.py`、`run_test2_6_2.py`：运行测试的脚本


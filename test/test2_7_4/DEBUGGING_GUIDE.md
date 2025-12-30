# 分步骤调试指南

本指南说明如何使用分步骤调试功能来调试修复流程。

## 环境变量控制

通过设置环境变量，可以跳过特定的执行步骤：

### 1. SKIP_REPAIR_ORDER
跳过修复顺序分析阶段。如果设置，系统会：
- 尝试从已有的输出文件中加载修复点
- 如果文件不存在，则从bug_location中提取修复点

**使用场景**: 当你已经知道修复顺序，或者想重用之前的修复点分析结果时。

### 2. SKIP_INITIAL_FIX
跳过初始修复生成阶段。如果设置，系统会：
- 跳过第一次迭代的初始修复生成
- 直接进入验证和迭代阶段（如果验证未跳过）

**使用场景**: 当你已经有初始修复代码，只想测试验证和迭代环节时。

### 3. SKIP_VALIDATION
跳过验证和迭代阶段。如果设置，系统会：
- 生成初始修复后直接结束
- 不进行验证和后续迭代

**使用场景**: 当你只想测试初始修复生成，不需要验证时。

### 4. SKIP_MERGE
跳过合并思维链阶段。如果设置，系统会：
- 使用简单的字符串连接方式合并各个修复点的思维链
- 不调用模型进行智能合并

**使用场景**: 当你只想查看各个修复点的独立思维链，或者想测试合并环节时。

## 使用示例

### 示例1: 只执行修复顺序分析
```bash
SKIP_INITIAL_FIX=1 SKIP_VALIDATION=1 python3 test/test2_7_4/run_test2_7_4.py
```
**用途**: 只分析修复顺序，不生成修复代码

### 示例2: 只生成初始修复（不验证）
```bash
SKIP_REPAIR_ORDER=1 SKIP_VALIDATION=1 python3 test/test2_7_4/run_test2_7_4.py
```
**用途**: 只生成初始修复代码，不进行验证和迭代

### 示例3: 只执行验证和迭代（跳过初始修复生成）
```bash
SKIP_REPAIR_ORDER=1 SKIP_INITIAL_FIX=1 python3 test/test2_7_4/run_test2_7_4.py
```
**用途**: 基于已有的初始修复，只测试验证和迭代环节

**注意**: 这个模式需要先有初始修复代码。系统会尝试从已有的输出文件中加载。

### 示例4: 只执行合并思维链
```bash
SKIP_REPAIR_ORDER=1 SKIP_INITIAL_FIX=1 SKIP_VALIDATION=1 python3 test/test2_7_4/run_test2_7_4.py
```
**用途**: 只执行合并思维链环节（需要先有各个修复点的思维链）

### 示例5: 完整流程（默认）
```bash
python3 test/test2_7_4/run_test2_7_4.py
```
**用途**: 执行完整的修复流程

## 调试工作流建议

### 工作流1: 逐步调试修复顺序分析
1. **第一步**: 只执行修复顺序分析
   ```bash
   SKIP_INITIAL_FIX=1 SKIP_VALIDATION=1 python3 test/test2_7_4/run_test2_7_4.py
   ```
2. **检查结果**: 查看生成的修复点是否正确
3. **如果正确**: 继续下一步；如果错误，调整prompt或重新运行

### 工作流2: 逐步调试初始修复生成
1. **第一步**: 只生成初始修复（使用已有的修复点）
   ```bash
   SKIP_REPAIR_ORDER=1 SKIP_VALIDATION=1 python3 test/test2_7_4/run_test2_7_4.py
   ```
2. **检查结果**: 查看生成的初始修复代码是否正确
3. **如果正确**: 继续下一步；如果错误，调整prompt或重新运行

### 工作流3: 逐步调试验证和迭代
1. **前提**: 确保已有初始修复代码（通过完整运行或工作流2生成）
2. **第一步**: 只执行验证和迭代
   ```bash
   SKIP_REPAIR_ORDER=1 SKIP_INITIAL_FIX=1 SKIP_MERGE=1 python3 test/test2_7_4/run_test2_7_4.py
   ```
3. **检查结果**: 查看验证反馈和迭代改进是否有效
4. **如果有效**: 完整运行；如果无效，调整验证prompt或迭代prompt

### 工作流4: 逐步调试合并思维链
1. **前提**: 确保已有各个修复点的思维链（通过完整运行生成）
2. **第一步**: 只执行合并思维链
   ```bash
   SKIP_REPAIR_ORDER=1 SKIP_INITIAL_FIX=1 SKIP_VALIDATION=1 python3 test/test2_7_4/run_test2_7_4.py
   ```
3. **检查结果**: 查看合并后的思维链是否连贯、完整
4. **如果有效**: 完整运行；如果无效，调整合并prompt

### 工作流5: 测试简单合并（不使用模型）
1. **前提**: 确保已有各个修复点的思维链
2. **第一步**: 使用简单连接方式合并（跳过模型合并）
   ```bash
   SKIP_REPAIR_ORDER=1 SKIP_INITIAL_FIX=1 SKIP_VALIDATION=1 SKIP_MERGE=1 python3 test/test2_7_4/run_test2_7_4.py
   ```
3. **检查结果**: 查看简单连接的结果，对比模型合并的效果

## 输出文件位置

所有输出文件保存在：
- `test/test2_7_4/outputs/thinking_chains/test2_7_4_initial.json`
- `test/test2_7_4/outputs/thinking_chains/test2_7_4_initial.txt`

当使用`SKIP_REPAIR_ORDER=1`时，系统会尝试从这些文件中加载已有的修复点。

## 注意事项

1. **文件依赖**: 使用`SKIP_REPAIR_ORDER=1`时，确保已有输出文件存在，否则系统会从bug_location提取修复点。

2. **数据一致性**: 如果修改了测试用例（test2_7_4.json），建议删除旧的输出文件，重新运行完整流程。

3. **日志输出**: 所有步骤都会在控制台输出详细的日志信息，包括：
   - 每个阶段的进入/完成标记
   - API调用耗时
   - 模型响应长度
   - 验证结果和反馈

4. **组合使用**: 可以同时设置多个SKIP标志，例如：
   ```bash
   SKIP_REPAIR_ORDER=1 SKIP_INITIAL_FIX=1 SKIP_VALIDATION=1 python3 test/test2_7_4/run_test2_7_4.py
   ```
   这种情况下，系统会尝试加载已有的所有数据，主要用于查看已有结果。

## 常见问题

### Q: 如何查看某个步骤的详细输出？
A: 使用相应的SKIP标志跳过其他步骤，只执行你关心的步骤。

### Q: 如何重用之前的修复点分析？
A: 设置`SKIP_REPAIR_ORDER=1`，系统会自动从输出文件中加载。

### Q: 如何只测试验证环节？
A: 设置`SKIP_REPAIR_ORDER=1 SKIP_INITIAL_FIX=1`，但需要确保已有初始修复代码。

### Q: 如何重新开始？
A: 删除输出文件，然后运行完整流程。

### Q: 如何只测试合并环节？
A: 设置`SKIP_REPAIR_ORDER=1 SKIP_INITIAL_FIX=1 SKIP_VALIDATION=1`，系统会从已有输出文件中加载思维链并执行合并。

### Q: SKIP_MERGE和正常合并有什么区别？
A: 
- **正常合并**: 使用模型智能合并，生成连贯的完整思维链
- **SKIP_MERGE**: 使用简单字符串连接，保留各个修复点的独立思维链结构


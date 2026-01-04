# Test6: 修复顺序分析（仅从JSON提取）

## 目标

测试直接从JSON的 `fix_points` 字段提取修复位点，跳过模型推理、验证、优化和思维链融合。

## JSON格式设计原则

### 核心原则

1. **与patch文件信息基本一致**：提供明确的定位和完整的整体修复方式
2. **不告诉最终修改结果**：正确的修改方法只在 `fixed_code` 中给出
3. **fix_points只包含定位信息**：帮助模型完成前置的定位任务
4. **fixed_code包含完整修复方法**：以文件为单位，diff格式，带行号

### fix_points字段（仅定位信息）

**包含**：
- `id`: Fix point唯一ID
- `file`: 文件路径
- `function`: 函数名（如果适用，否则为null）
- `line_start`: 起始行号
- `line_end`: 结束行号

**不包含**：
- ❌ `description`: 描述信息
- ❌ `code_to_add`: 要添加的代码
- ❌ `code_to_remove`: 要移除的代码
- ❌ `dependencies`: 依赖关系
- ❌ `reasons`: 修复原因
- ❌ `operation_type`: 操作类型

### fixed_code字段（完整修复方法）

**结构**：以文件路径为key的字典

```json
{
  "fixed_code": {
    "src/server/ua_session.c": {
      "file_path": "src/server/ua_session.c",
      "diff": "@@ -36,19 +36,6 @@ void UA_Session_deleteMembersCleanup...",
      "changes": [
        {
          "line_start": 21,
          "line_end": 32,
          "operation": "remove",
          "context": "Remove subscription cleanup code..."
        }
      ]
    },
    "src/server/ua_session_manager.c": {
      "file_path": "src/server/ua_session_manager.c",
      "diff": "@@ -11,6 +11,7 @@\n...",
      "changes": [...]
    }
  }
}
```

**每个文件包含**：
- `file_path`: 文件路径
- `diff`: 完整的diff格式修复方法（与patch文件一致）
- `changes`: 变更列表，每个变更包含：
  - `line_start`/`line_end`: 行号范围
  - `operation`: 操作类型（add/remove）
  - `context`: 上下文说明（可选）

## 运行方式

```bash
# 从项目根目录运行
python3 test/test6/run_test6.py
```

## 输出

- `test/test6/outputs/thinking_chains/test6_order_analysis.json`: JSON格式的修复顺序分析结果
- `test/test6/outputs/thinking_chains/test6_order_analysis.txt`: 文本格式的修复顺序分析结果

## 配置

test6默认配置：
- ✓ 从JSON直接提取fix points（仅定位信息）
- ✗ 跳过fix point处理（SKIP_INITIAL_FIX=1）
- ✗ 跳过验证（SKIP_VALIDATION=1）
- ✗ 跳过思维链融合（SKIP_MERGE=1）
- ✗ 跳过本地模型（SKIP_LOCAL=1）

## 与Patch的对应关系

### Patch中的变更

1. **ua_session.c**:
   - 移除订阅清理代码（lines 21-32）

2. **ua_session_manager.c**:
   - 添加 `#include "ua_subscription.h"` (line 44)
   - 移除旧的 `UA_SessionManager_deleteMembers` (lines 52-59)
   - 在 `removeSession` 中添加订阅清理代码 (lines 68-80)
   - 重新添加修改后的 `UA_SessionManager_deleteMembers` (lines 89-94)

### JSON中的Fix Points（仅定位）

1. **Fix Point 1**: `ua_session.c:UA_Session_deleteMembersCleanup` (lines 21-32)
2. **Fix Point 2**: `ua_session_manager.c:removeSession` (lines 68-80)
3. **Fix Point 3**: `ua_session_manager.c` (line 44, function=null)
4. **Fix Point 4**: `ua_session_manager.c:UA_SessionManager_deleteMembers` (lines 52-59)
5. **Fix Point 5**: `ua_session_manager.c:UA_SessionManager_deleteMembers` (lines 89-94)

### JSON中的Fixed Code（完整修复方法）

- `fixed_code["src/server/ua_session.c"]`: 包含该文件的完整diff
- `fixed_code["src/server/ua_session_manager.c"]`: 包含该文件的完整diff

## 优势

1. **职责分离**：
   - `fix_points`: 仅提供定位信息，帮助模型找到需要修改的位置
   - `fixed_code`: 提供完整的修复方法，但不告诉模型具体如何修改

2. **与patch一致**：`fixed_code` 中的diff格式与patch文件完全一致

3. **完整性**：每个文件的修复方法都完整呈现，包括上下文和行号

4. **可验证性**：可以验证修复顺序是否正确，但不泄露具体的修改方法

# 代码库下载工具使用说明

## 功能说明

`download_codebase.py` 脚本用于从 patch 文件中提取项目信息，并自动下载对应的代码库（修复前的版本），以便模型能够分析完整的代码上下文。

## 使用方法

### 基本用法

```bash
python scripts/download_codebase.py <patch_file> [output_dir]
```

### 参数说明

- `patch_file`: patch 文件路径（必需）
- `output_dir`: 输出目录（可选），默认为 `datasets/codebases/{项目名}/`

### 示例

```bash
# 下载 open62541 项目代码（修复前版本）
python scripts/download_codebase.py datasets/testdata/patches/use_after_free/42470745.patch

# 指定输出目录
python scripts/download_codebase.py datasets/testdata/patches/use_after_free/42470745.patch datasets/codebases/my_open62541
```

## 工作原理

1. **解析 patch 文件**：
   - 提取 commit hash
   - 根据代码特征识别项目（如 open62541, harfbuzz 等）

2. **下载代码库**：
   - 克隆项目的 GitHub 仓库
   - 切换到修复前的版本（commit 的父 commit）

3. **输出**：
   - 代码库保存在 `datasets/codebases/{项目名}/` 目录
   - 返回代码库路径，可用于 `RepairPipeline` 的 `codebase_path` 参数

## 在修复流程中使用

下载代码库后，可以在 `RepairPipeline` 中使用：

```python
from core.repair_pipeline import RepairPipeline

# 使用下载的代码库路径
pipeline = RepairPipeline(codebase_path="datasets/codebases/open62541")

# 处理修复案例
result = pipeline.process_repair_case(
    buggy_code=buggy_code,
    fixed_code=fixed_code,
    bug_location="src/server/ua_session.c",
    case_id="test2_2"
)
```

这样，当模型需要使用 `grep` 命令查找相关代码时，就能在完整的代码库中搜索了。

## 注意事项

1. **首次下载**：会完整克隆仓库，可能需要一些时间
2. **已存在代码库**：如果目录已存在，脚本会询问是否重新克隆
3. **网络要求**：需要能够访问 GitHub
4. **存储空间**：确保有足够的磁盘空间（通常几百MB到几GB）

## 支持的项目

目前自动识别以下项目：
- **open62541**: OPC UA 服务器实现
- **harfbuzz**: 文本渲染引擎

如需支持其他项目，可以在 `download_codebase.py` 的 `project_info` 字典中添加。

## 故障排除

### 问题：无法获取父 commit

如果无法获取父 commit，脚本会直接 checkout 到 patch 中的 commit（这是修复后的版本）。这种情况下，你需要手动切换到修复前的版本：

```bash
cd datasets/codebases/open62541
git log --oneline | grep -A 5 "21771329dd"  # 查找修复 commit
git checkout <修复前的 commit hash>
```

### 问题：网络连接失败

确保能够访问 GitHub，或者配置 Git 代理：

```bash
git config --global http.proxy http://proxy.example.com:8080
```

### 问题：磁盘空间不足

清理不需要的代码库：

```bash
rm -rf datasets/codebases/open62541
```


# 模型选择机制说明

## 一、模型选择逻辑

当前使用的模型由以下优先级决定（从高到低）：

### 优先级顺序

1. **构造函数参数** `model_name`（最高优先级）
   - 如果调用 `AliyunModel(api_key, model_name="qwen3-coder-plus")`，使用传入的模型名
   - **当前代码中未使用此方式**

2. **环境变量** `ALIYUN_MODEL_NAME`（中等优先级）
   - 如果设置了环境变量 `ALIYUN_MODEL_NAME`，使用环境变量的值
   - **这是当前推荐的方式**

3. **默认值** `qwen3-coder-plus`（最低优先级）
   - 如果以上都没有设置，使用默认值 `qwen3-coder-plus`

### 代码实现

```python
# models/aliyun_model.py
def __init__(self, api_key: str, model_name: str = None):
    # ...
    self.model_name = model_name or os.getenv("ALIYUN_MODEL_NAME", "qwen-turbo")
```

## 二、当前代码中的使用情况

### 所有调用位置

从代码搜索结果看，所有地方都是这样调用的：

```python
aliyun_model = AliyunModel(ALIYUN_API_KEY)
```

**没有传入 `model_name` 参数**，所以模型选择完全依赖于：
- 环境变量 `ALIYUN_MODEL_NAME`（如果设置了）
- 默认值 `qwen-turbo`（如果没有设置环境变量）

### 调用位置列表

- `core/repair_pipeline.py`
- `test/test4/run_test4.py`
- `test/test5/run_test5.py`
- `test/test3/run_test3.py`
- `test/test3_2/run_test3_2.py`
- `test/test2_7_4/run_test2_7_4.py`
- ...（其他测试脚本）

## 三、如何设置模型

### 方法1：通过环境变量设置（推荐）

```bash
# 设置环境变量
export ALIYUN_MODEL_NAME=qwen3-coder-plus

# 运行脚本
python3 test/test4/run_test4.py
```

### 方法2：在运行命令中设置

```bash
# 在运行命令中设置环境变量
ALIYUN_MODEL_NAME=qwen3-coder-plus python3 test/test4/run_test4.py
```

### 方法3：修改代码（不推荐）

如果需要永久修改，可以修改所有调用 `AliyunModel` 的地方：

```python
# 修改前
aliyun_model = AliyunModel(ALIYUN_API_KEY)

# 修改后
aliyun_model = AliyunModel(ALIYUN_API_KEY, model_name="qwen3-coder-plus")
```

**不推荐**：因为需要修改多个文件，而且不够灵活。

### 方法4：修改默认值（不推荐）

修改 `models/aliyun_model.py`：

```python
# 修改前
self.model_name = model_name or os.getenv("ALIYUN_MODEL_NAME", "qwen-turbo")

# 修改后
self.model_name = model_name or os.getenv("ALIYUN_MODEL_NAME", "qwen3-coder-plus")
```

**不推荐**：会改变所有没有设置环境变量的情况下的默认行为。

## 四、检查当前使用的模型

### 方法1：检查环境变量

```bash
echo $ALIYUN_MODEL_NAME
```

如果输出为空，说明没有设置环境变量，将使用默认值 `qwen3-coder-plus`。

### 方法2：在代码中打印

可以在 `models/aliyun_model.py` 的 `__init__` 方法中添加打印：

```python
def __init__(self, api_key: str, model_name: str = None):
    # ...
    self.model_name = model_name or os.getenv("ALIYUN_MODEL_NAME", "qwen3-coder-plus")
    print(f"[Model] Using model: {self.model_name}")  # 添加这行
```

### 方法3：查看日志

如果代码中有打印模型信息，可以在日志中查看。

## 五、推荐的配置方式

### 对于 `qwen3-coder-plus`

**当前状态**：`qwen3-coder-plus` 已设置为默认模型，无需额外配置即可使用。

**如果需要使用其他模型**，可以通过环境变量覆盖：

```bash
# 方式1：在运行命令中设置（临时）
ALIYUN_MODEL_NAME=qwen-turbo python3 test/test4/run_test4.py

# 方式2：在shell配置文件中设置（永久）
echo 'export ALIYUN_MODEL_NAME=qwen-turbo' >> ~/.bashrc
source ~/.bashrc

# 方式3：在脚本中设置（针对特定脚本）
# 在 run_test4.py 开头添加：
import os
os.environ['ALIYUN_MODEL_NAME'] = 'qwen-turbo'
```

### 验证设置

运行以下命令验证：

```bash
# 检查环境变量
echo "ALIYUN_MODEL_NAME: ${ALIYUN_MODEL_NAME:-未设置，将使用默认值 qwen-turbo}"

# 或者运行一个简单的Python脚本
python3 -c "import os; print('使用的模型:', os.getenv('ALIYUN_MODEL_NAME', 'qwen3-coder-plus (默认值)'))"
```

## 六、总结

### 当前情况

- **代码中**：所有调用都没有传入 `model_name` 参数
- **模型选择**：完全依赖于环境变量 `ALIYUN_MODEL_NAME` 或默认值 `qwen3-coder-plus`
- **默认模型**：`qwen3-coder-plus`（已设置为默认值，无需环境变量）

### 最佳实践

1. **使用环境变量**：最灵活，不需要修改代码
2. **在运行命令中设置**：适合临时测试不同模型
3. **在shell配置文件中设置**：适合长期使用特定模型

### 注意事项

- 环境变量只在当前shell会话中有效
- 如果使用 `tmux` 或 `screen`，需要在每个会话中设置
- 如果使用IDE运行，需要在IDE的环境变量设置中配置


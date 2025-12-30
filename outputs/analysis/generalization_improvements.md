# 提示词通用化改进总结

## 改进日期
2025-12-19

## 改进目标

将提示词从针对特定漏洞类型（如 use-after-free）的特殊处理，改为通用的内存访问漏洞处理方式，提高系统的泛化能力。

## 问题分析

### 原有问题
1. **过度特化**：提示词中针对 use-after-free 做了大量特殊处理
2. **泛化能力不足**：系统只能很好地处理 use-after-free，对其他内存访问漏洞类型可能效果不佳
3. **维护成本高**：每增加一种漏洞类型，都需要添加特殊处理逻辑

### 改进方向
- 移除对特定漏洞类型的特殊判断和处理
- 强调通用的内存安全分析原则
- 让模型自己识别漏洞类型，而不是预先判断
- 关注通用的概念：资源释放顺序、内存生命周期、依赖关系等

## 已实施的改进

### 1. 移除特定漏洞类型判断

**之前**：
```python
# Check if this is a use-after-free vulnerability
is_uaf = "use-after-free" in bug_location.lower() or ...
if is_uaf:
    uaf_context = """CRITICAL: This is a USE-AFTER-FREE vulnerability..."""
```

**现在**：
- 完全移除 `is_uaf` 判断
- 移除 `uaf_context` 和 `uaf_emphasis`
- 不再针对特定漏洞类型做特殊处理

### 2. 强调通用的内存安全原则

**改进后的提示词强调**：

1. **资源释放顺序**：
   - 什么必须在什么之前清理
   - 理解依赖关系
   - 执行顺序的重要性

2. **内存生命周期**：
   - 指针何时变为无效
   - 资源何时可以被安全访问
   - 资源何时必须被清理

3. **代码执行顺序**：
   - 操作的时序关系
   - 代码移动的含义（从错误位置移到正确位置）
   - 执行顺序对内存安全的影响

4. **依赖关系**：
   - 资源之间的依赖链
   - 父资源与子资源的关系
   - 清理顺序必须遵循依赖关系

### 3. 通用的漏洞描述解析

**改进后的提示词**：
```
When you see descriptions like:
- "should be added before [operation]" → Move code to execute BEFORE that operation
- "removed from..." → Code is being removed from wrong location/timing
- Any mention of order, timing, sequence → Pay attention to EXECUTION ORDER
```

不再针对特定漏洞类型举例，而是提供通用的解析原则。

### 4. 让模型自己识别漏洞类型

**改进后的提示词**：
```
Your task is to understand:
1. What is the underlying MEMORY ACCESS vulnerability?
   - Use-after-free: accessing memory after it's been freed
   - Buffer overflow/underflow: accessing array out of bounds
   - Null pointer dereference: dereferencing a null pointer
   - Double free: freeing the same memory twice
   - Memory leak: not freeing allocated memory
   - Incorrect resource release order: accessing resources after they're released
```

列出所有可能的内存访问漏洞类型，让模型自己识别，而不是我们预先判断。

## 改进效果

### 优势
1. ✅ **更好的泛化能力**：可以处理所有内存访问相关的漏洞，不局限于特定类型
2. ✅ **更易维护**：不需要为每种漏洞类型添加特殊处理
3. ✅ **更灵活**：模型可以根据具体情况识别漏洞类型
4. ✅ **更通用**：强调通用的内存安全原则，适用于各种场景

### 保持的核心能力
1. ✅ **资源释放顺序分析**：仍然强调执行顺序的重要性
2. ✅ **代码移动理解**：仍然强调代码从错误位置移到正确位置的含义
3. ✅ **依赖关系分析**：仍然强调资源之间的依赖关系
4. ✅ **漏洞描述解析**：仍然强调从描述中提取关键信息

## 关键改进点对比

### 之前（特化处理）
```
if is_uaf:
    uaf_context = """
    CRITICAL: This is a USE-AFTER-FREE vulnerability.
    Use-after-free occurs when:
    1. A resource is accessed AFTER its parent resource has been detached/freed
    2. The fix requires MOVING cleanup code to execute BEFORE...
    3. Child resources must be cleaned up BEFORE parent resources
    """
```

### 现在（通用处理）
```
vulnerability_emphasis = """
CRITICAL: Pay attention to the vulnerability descriptions.
Key principle: Understand the dependency relationships between resources.
Child resources typically must be cleaned up BEFORE parent resources are detached/freed.

When you see code being MOVED, analyze:
- Why is the code in the wrong location? (What memory access issue does this cause?)
- What is the correct location? (What is the proper execution order?)
- What dependencies exist between resources? (What must happen before what?)
"""
```

## 适用场景

改进后的系统可以处理所有内存访问相关的漏洞：

1. **Use-after-free**：资源在释放后仍被访问
2. **Buffer overflow/underflow**：数组越界访问
3. **Null pointer dereference**：空指针解引用
4. **Double free**：重复释放内存
5. **Memory leak**：内存泄漏
6. **Incorrect resource release order**：资源释放顺序错误
7. **其他内存访问问题**：通过通用的内存安全原则分析

## 文件修改清单

1. `utils/prompts.py` - 移除特定漏洞类型判断，改为通用处理
2. `outputs/analysis/improvements_summary.md` - 更新改进总结

## 相关文档

- `outputs/analysis/improvements_summary.md` - 思维链生成改进总结
- `experiment_summary_12_18.md` - 项目概述和当前状态



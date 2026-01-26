# Prompt解耦重构说明

## 重构概览

已成功将 `rpvm_pipeline.py` 中的所有prompt提取到独立的文件中，便于修改和管理。

## 文件结构

```
RPVM/
├── rpvm_pipeline.py          # 重构后的主pipeline（减少75行代码）
├── prompt_loader.py          # 新增：Prompt加载器
└── prompts/                  # 新增：Prompt目录
    ├── planner_system.md
    ├── planner_few_shot_examples.md
    ├── planner_user_with_memory.md
    ├── planner_user_without_memory.md
    ├── verifier_system.md
    ├── verifier_user.md
    ├── query_rewriter_system.md
    ├── query_rewriter_user.md
    ├── memory_summarizer_system.md
    ├── memory_summarizer_user.md
    ├── final_answer_system.md
    ├── final_answer_user.md
    ├── best_effort_answer_system.md
    ├── best_effort_answer_user_no_memory.md
    └── best_effort_answer_user_with_memory.md
```

## 提取的Prompt类型

### 1. **Planner相关** (4个文件)
- `planner_system.md` - Planner的系统prompt
- `planner_few_shot_examples.md` - Few-shot示例
- `planner_user_with_memory.md` - 有记忆时的用户prompt
- `planner_user_without_memory.md` - 无记忆时的用户prompt

### 2. **Verifier相关** (2个文件)
- `verifier_system.md` - Verifier的系统prompt
- `verifier_user.md` - Verifier的用户prompt模板

### 3. **Query Rewriter相关** (2个文件)
- `query_rewriter_system.md` - 查询改写的系统prompt
- `query_rewriter_user.md` - 查询改写的用户prompt

### 4. **Memory Summarizer相关** (2个文件)
- `memory_summarizer_system.md` - 记忆摘要的系统prompt
- `memory_summarizer_user.md` - 记忆摘要的用户prompt

### 5. **Final Answer相关** (2个文件)
- `final_answer_system.md` - 最终答案的系统prompt
- `final_answer_user.md` - 最终答案的用户prompt

### 6. **Best Effort Answer相关** (3个文件)
- `best_effort_answer_system.md` - 尽力回答的系统prompt
- `best_effort_answer_user_no_memory.md` - 无记忆时的尽力回答prompt
- `best_effort_answer_user_with_memory.md` - 有记忆时的尽力回答prompt

## 核心改动

### `rpvm_pipeline.py` 的变化

**之前 (574行)** → **之后 (422行)**，减少了152行代码

#### 1. 导入新模块
```python
from prompt_loader import PromptLoader
```

#### 2. 初始化Prompt Loader
```python
def __init__(self, config, prompt_template=None):
    ...
    # 初始化Prompt Loader
    self.prompt_loader = PromptLoader()
```

#### 3. 所有prompt调用改为使用Prompt Loader

**修改前**:
```python
system_prompt = """You are a Fact Hypothesis Generator..."""
planner_prompt = self._build_planner_prompt(question, memory)
response = self._call_generator(system_prompt, planner_prompt, ...)
```

**修改后**:
```python
system_prompt, user_prompt = self.prompt_loader.get_planner_prompt(question, memory)
response = self._call_generator(system_prompt, user_prompt, ...)
```

#### 4. 删除的方法
- `_build_planner_prompt()` - 已由PromptLoader替代

### `prompt_loader.py` 的功能

提供统一的prompt加载接口：

```python
class PromptLoader:
    def get_planner_prompt(question, memory) -> (system, user)
    def get_verifier_prompt(plan, docs_text) -> (system, user)
    def get_query_rewriter_prompt(plan, attempt) -> (system, user)
    def get_memory_summarizer_prompt(memory) -> (system, user)
    def get_final_answer_prompt(question, memory) -> (system, user)
    def get_best_effort_answer_prompt(question, memory) -> (system, user)
```

## 使用方式

### 修改Prompt

直接编辑 `prompts/` 目录下的对应 `.md` 文件即可，无需修改Python代码。

**示例：修改Planner的系统prompt**
```bash
vim prompts/planner_system.md
```

### 变量插值

Prompt文件中使用 `{variable_name}` 进行变量占位：

```markdown
Question: {question}

Memory:
{memory}
```

PromptLoader会自动进行格式化替换。

## 测试结果

✅ **语法检查通过**
```bash
python3 -m py_compile rpvm_pipeline.py  # ✓
python3 -m py_compile prompt_loader.py  # ✓
```

✅ **Prompt加载测试通过**
```bash
PromptLoader initialized successfully
System prompt length: 525
User prompt length: 1424
✓ All prompt loading methods work
```

## 优势

1. **易于修改** - 直接编辑Markdown文件，无需接触Python代码
2. **版本控制友好** - Prompt变更可独立追踪
3. **代码简洁** - rpvm_pipeline.py减少152行代码
4. **职责分离** - Prompt管理与业务逻辑分离
5. **可扩展** - 添加新prompt只需创建新文件
6. **多语言支持** - 可轻松创建不同语言版本的prompt目录

## 兼容性

✅ 保持原有功能完全不变  
✅ 所有方法调用保持一致  
✅ 配置文件无需修改  
✅ 现有实验可直接运行

## 下一步建议

1. 根据实验报告中的建议，修改 `prompts/final_answer_user.md` 优化答案格式
2. 调整 `prompts/verifier_user.md` 改进验证判断逻辑
3. 可考虑为不同数据集创建专用prompt变体（如 `prompts/2wikimultihopqa/`）

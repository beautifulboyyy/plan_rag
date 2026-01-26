# PlanRAG 实验方法构建方案

## 1. 方法概述

### 1.1 核心思想
在ReSP方法基础上增加两个模块：
- **Planner模块**：生成多跳问题的全局规划蓝图
- **Check模块**：检查规划完成度，辅助判断

### 1.2 整体流程

```
输入问题 Q
    ↓
Planner 生成全局规划 P (纯文本列表格式)
    ↓
进入迭代循环 (max_iter=3):
    ├─ Retriever 检索 top-k 相关文档
    ├─ Summarizer 双路摘要:
    │   ├─ Global Evidence: 与主问题相关的证据摘要
    │   └─ Local Pathway: 子问题+答案对
    ├─ Checker: 检查规划完成度 → P_checked
    └─ Judge: 输入=已知信息+P+P_checked → 判断/生成子问题
    ↓
Generator 生成最终答案
```

---

## 2. 现有资源

### 2.1 已准备好的资源
| 资源 | 路径 | 说明 |
|------|------|------|
| 数据集 | `method/datasets/2wikimultihopqa/` | dev.jsonl, train.jsonl |
| 生成模型 | `method/llama3-8b-instruct/` | Llama3-8B-Instruct |
| 检索模型 | `method/e5-base-v2/` | E5 嵌入模型 |
| 索引 | `method/indexes/` | Wiki18 索引 |

### 2.2 已有参考文件
- `method/ReSP.md` - ReSP论文核心内容
- `method/ReSPprompt.md` - ReSP各模块prompt
- `method/example.md` - PlanRAG具体例子
- `method/experiments/plan_evaluation/` - Planner模块实验

---

## 3. 实验配置（参考ReSP论文5.2节）

### 3.1 核心参数
| 参数 | 值 | 说明 |
|------|-----|------|
| generator_model | Llama3-8B-instruct | 生成模型 |
| retriever_model | E5-base-v2 | 检索模型 |
| corpus | Wikipedia (2018, ~20M passages) | 检索语料 |
| max_input_length | 12,000 | 模型最大输入长度 |
| max_output_length | 200 | 模型最大输出长度 |
| top_k | 5 | 检索文档数量 |
| max_iter | 3 | 最大迭代次数 |
| seed | 2024 | 随机种子 |

### 3.2 迭代停止条件
- 达到max_iter=3次迭代后，直接进入最终答案生成
- 或在任意迭代中，Judge判断信息足够时提前停止

---

## 4. 命令行参数设计

### 4.1 运行参数
```bash
python run_plan_rag.py \
    --split dev \          # 数据集划分: train/dev/test
    --num_samples 5 \      # 测试样本数，None表示全部
    --max_iter 3 \         # 最大迭代次数
    --top_k 5 \            # 检索文档数量
    --gpu_id 0 \           # GPU设备号
    --output_dir method/outputs/plan_rag_$(date +%Y%m%d_%H%M%S)
```

### 4.2 配置优先级
```
命令行参数 > 配置文件 > 默认值
```

---

## 5. 文件与目录结构

```
method/
├── plan_rag_pipeline.py       # PlanRAG Pipeline 实现
├── plan_rag_config.yaml       # 基础配置文件
├── run_plan_rag.py            # 运行入口脚本
├── plan_rag_design.md         # 本设计文档
│
├── prompts/                   # Prompt模板目录
│   ├── planner_prompt.md      # Planner prompt
│   ├── check_prompt.md        # Check prompt
│   ├── judge_prompt.md        # Judge prompt (含plan扩展)
│   ├── reasoner_prompt.md     # Reasoner prompt (含plan扩展)
│   ├── summarizer_global.md   # Summarizer Global Evidence prompt
│   └── summarizer_local.md    # Summarizer Local Pathway prompt
│
├── outputs/                   # 实验输出目录 (运行时生成)
│   └── plan_rag_YYYYMMDD_HHMMSS/
│       ├── config.yaml        # 本次实验配置
│       ├── results.jsonl      # 预测结果
│       ├── metrics.txt        # 评估指标
│       └── logs/              # 训练日志
│           └── plan_rag.log
│
└── (其他资源)
    ├── datasets/
    ├── llama3-8b-instruct/
    ├── e5-base-v2/
    └── indexes/
```

---

## 6. 模块详细设计

### 6.1 Planner模块

**作用**：生成多跳问题的全局处理规划。

**输入**：主问题 Q

**输出**：纯文本列表格式
```
**Plan**:
1. First, identify the director of the film Polish-Russian War.
2. Then, find out who the mother of that director is.
```

**Prompt文件**：`prompts/planner_prompt.md`
```markdown
# Role
You are a master of multi-hop task planning...

# Output Format
**Plan**: A numbered list of search intents.

# Examples
...

# Now Begin
Question: {question}
```

---

### 6.2 Check模块

**作用**：在每轮迭代结束时，检查规划完成度。

**输出格式**：
```
**Completed Steps**: [1, 2]
**Remaining Steps**: [3]
```

**Prompt文件**：`prompts/check_prompt.md`
```markdown
# Task
Based on the information collected, check which planning steps have been completed.

# Original Question
{question}

# Global Plan
{plan}

# Information Collected (Global Evidence + Local Pathway)
{combined_memory}

# Instructions
Review the information collected and determine which plan steps have been COMPLETED.

Output Format:
**Completed Steps**: [step numbers]
**Remaining Steps**: [step numbers]

# Check Result:
```

---

### 6.3 扩展的Judge模块

**修改策略**：简单扩展，将确认后的plans作为额外输入。

**Prompt文件**：`prompts/judge_prompt.md`
```markdown
Judging based solely on the current known information and without allowing for inference,
are you able to completely and accurately respond to the question {question}?

Known information: {combined_memory}

Global Plan: {plan}
Plan Progress: {plan_progress}

If you can, please reply with "Yes" directly; if you cannot and need more information,
please reply with "No" directly.
```

---

### 6.4 扩展的Reasoner模块

**Prompt文件**：`prompts/reasoner_prompt.md`
```markdown
You serve as an intelligent assistant, adept at facilitating users through complex,
multi-hop reasoning across multiple documents.
Please understand the information gap between the currently known information and the
target problem.
Your task is to generate one thought in the form of question for next retrieval step
directly. DON'T generate the whole thoughts at once!
DON'T generate thought which has been retrieved.

[Known information]: {combined_memory}
[Target question]: {question}
[Global Plan]: {plan}
[Plan Progress]: {plan_progress}
[You Thought]:
```

---

### 6.5 Summarizer模块（复用ReSP）

**Global Evidence Prompt** (`prompts/summarizer_global.md`):
```markdown
Passages: {docs}

Your job is to act as a professional writer. You will write a good quality passage
that can support the given prediction about the question only based on the information
in the provided supporting passages. Now, let's start.
After you write, please write [DONE] to indicate you are done.

Question: {question}
Passage:
```

**Local Pathway Prompt** (`prompts/summarizer_local.md`):
```markdown
Judging based solely on the current known information and without allowing for inference,
are you able to respond completely and accurately to the question {sub_question}?
Known information: {combined_memory}
If yes, please reply with "Yes", followed by an accurate response...
```

---

## 7. 数据结构设计

```python
# 数据集扩展字段
dataset.global_plan: List[str]                    # 每个问题的全局规划
dataset.plan_history: List[List[Dict]]            # 每轮Check结果
dataset.plan_status: List[List[str]]              # 每轮规划状态: ['pending', 'completed', ...]
dataset.global_evidence_memory: List[List[str]]   # 全局证据记忆
dataset.local_pathway_memory: List[List[Dict]]    # 局部路径记忆
dataset.sub_questions: List[List[str]]            # 每轮子问题

# 单个样本示例
{
    'id': '...',
    'question': 'Who is the mother of the director of film The Fascist?',
    'global_plan': '1. Identify the director of the film The Fascist.\n2. Find out where the director was born.',
    'plan_history': [
        {'completed_steps': [1], 'remaining_steps': [2]},
        {'completed_steps': [1, 2], 'remaining_steps': []}
    ],
    'global_evidence_memory': [
        'The Fascist is a 1964 film directed by Luciano Salce...',
        'Luciano Salce was born in Rome, Italy...'
    ],
    'local_pathway_memory': [
        {'sub_question': 'Who directed The Fascist?', 'answer': 'Luciano Salce', 'can_answer': True}
    ],
    'sub_questions': ['Who directed The Fascist?', 'Where was Luciano Salce born?']
}
```

---

## 8. 实现步骤

### Phase 1: 实现ReSP基础
1. 实现Retriever检索（复用FlashRAG框架）
2. 实现双路Summarizer（Global Evidence + Local Pathway）
3. 实现Judge/Reasoner循环
4. 实现Generator输出

### Phase 2: 集成PlanRAG
1. 集成Planner模块（加载prompts/planner_prompt.md）
2. 集成Check模块（加载prompts/check_prompt.md）
3. 扩展Judge/Reasoner prompt（加载扩展后的prompt）
4. 端到端测试

### Phase 3: 实验验证
1. 在2WikiMultiHopQA验证
2. 在HotpotQA验证
3. 消融实验（Planner影响、Check影响）

---


## 9. 参考资料

- ReSP论文：`method/ReSP.md`
- ReSP Prompt：`method/ReSPprompt.md`
- Planner实验：`method/experiments/plan_evaluation/`
- 示例：`method/example.md`
- FlashRAG框架：`/home/algroup/lsw/planRAG/flashrag/`

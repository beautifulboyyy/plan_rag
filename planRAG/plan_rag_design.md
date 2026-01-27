# ReSP with Planner-Guided Reasoning: Workflow & Prompt Templates

## 0. 全局变量定义 (Global Variables)

整个流程中流转的核心数据变量：

* **`{question}`**: 原始的多跳问题 (Overarching question)。
* **`{plan}`**: 由 Planner 生成的当前规划蓝图（随 Checker 更新状态）。
* **`{memory}`**: 当前累积的已知信息 (Combined memory queues: Global Evidence + Local QA)。
* **`{docs}`**: Retriever 检索到的 Top-N 文档片段。
* **`{sub_question}`**: Reasoner 生成的下一步检索子问题。

---

## 1. Planner 模块 (全局规划)

**功能**：在迭代开始前，生成整体的逻辑蓝图。
**输入**：`{question}`
**输出**：初始 `{plan}`

**Prompt Template:**

```markdown
# Role
You are a master of multi-hop task planning, capable of efficiently breaking down a multi-hop logical problem into step-by-step processing and planning.
Do not generate explanations other than those related to planning.

# Input
- A multi-hop question.

# Output Format
**Plan**: A numbered list of search intents.

# Examples

## Example 1 (Bridge Type)
Question: Who is the mother of the director of film Polish-Russian War?
Plan:
1. First, identify the director of the film Polish-Russian War.
2. Then, find out who the mother of that director is.

## Example 2 (Comparison Type)
Question: Which film came out first, Blind Shaft or The Mask Of Fu Manchu?
Plan:
1. Determine the release date of Blind Shaft.
2. Determine the release date of The Mask of Fu Manchu.
3. Compare the two release dates to identify which film was released earlier.

# Now Begin
Question: {question}

```

---

## 2. ReSP Iteration Loop (推理迭代循环)

### 2.a. Reasoner - Judge Sub-module (判断与终止控制)

**功能**：判断当前记忆是否足以回答原始问题。**此处加入了 `{plan}` 作为辅助上下文。**
**输入**：`{question}`, `{memory}`, `{plan}`
**输出**：Yes / No

**Prompt Template:**

```text
Judging based solely on the current known information and the guidance of the global plan, without allowing for inference, are you able to completely and accurately respond to the question "{question}"?

[Global Plan]:
{plan}

[Known information]:
{memory}

If you can, please reply with "Yes" directly; if you cannot and need more information, please reply with "No" directly.

```

*(Logic: If Output == "Yes" -> Go to Generator; If Output == "No" -> Continue to Reasoner)*

### 2.b. Reasoner - Thought Sub-module (子问题生成)

**功能**：基于差距分析生成下一个检索意图。
**输入**：`{question}`, `{memory}`
**输出**：`{sub_question}`

**Prompt Template:**

```text
You serve as an intelligent assistant, adept at facilitating users through complex, multi-hop reasoning across multiple documents. Please understand the information gap between the currently known information and the target problem.

Your task is to generate one thought in the form of question for next retrieval step directly.
DON’T generate the whole thoughts at once!
DON’T generate thought which has been retrieved.

[Known information]:
{memory}

[Target question]:
{question}

[YouThought]:

```

*(注意：第一轮迭代时，默认 Judge 为 No，且不经过 Reasoner 生成，直接令 `{sub_question}` = `{question}`)*

### 2.c. Retriever (检索模块)

**功能**：获取外部知识。
**输入**：`{sub_question}`
**输出**：`{docs}` (Top-3 passages)

**Action:** `Retriever({sub_question}) -> {docs}`

### 2.d. Dual-Pathway Summarizer (双路记忆摘要)

**路径 1: Global Evidence Memory (全局证据)**
**功能**：提取文档中支持回答原始问题 `{question}` 的证据。
**输入**：`{question}`, `{docs}`
**输出**：`{global_evidence}`

**Prompt Template:**

```text
Passages:
{docs}

Your job is to act as a professional writer. You will write a good quality passage that can support the given prediction about the question only based on the information in the provided supporting passages. Now, let’s start. After you write, please write [DONE] to indicate you are done. Do not write a prefix (e.g., "Response:") while writing a passage.

Question: {question}
Passage:

```

**路径 2: Local Pathway (局部问答)**
**功能**：直接回答子问题 `{sub_question}`。
**输入**：`{sub_question}`, `{docs}`, `{memory}` (作为背景)
**输出**：`{local_answer}`

**Prompt Template:**

```text
Judging based solely on the current known information and without allowing for inference, are you able to respond completely and accurately to the question "{sub_question}"?

[Known information]:
{memory}

Passages:
{docs}

If yes, please reply with "Yes", followed by an accurate response to the question "{sub_question}", without restating the question; if no, please reply with "No" directly.

```

**更新记忆 (Memory Update):**
`{memory} = {memory} + {global_evidence} + {local_answer}`

### 2.e. Checker (规划状态更新)

**功能**：根据 Local Pathway 得到的 `{local_answer}`，检查 `{plan}` 中哪一步已完成，并标记状态。
**输入**：当前 `{plan}`, `{sub_question}`, `{local_answer}`
**输出**：更新后的 `{plan}`

*(Internal Logic/Prompt: Match the sub-question answered to the plan items and mark as "finished".)*

**Example Update:**
Original Plan:

1. Identify the director...
2. Find out where...

Updated `{plan}`:

1. Identify the director... (finished)
2. Find out where...

---

## 3. Generator (最终回答)

**功能**：当 Judge 返回 "Yes" 时，生成最终答案。
**输入**：`{question}`, `{memory}`
**输出**：Final Answer

**Prompt Template:**

```text
Answer the question based on the given reference.
Only give me the answer and do not output any other words.

The following are given reference:
{memory}

Question: {question}

```
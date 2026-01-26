# RPVM 架构重构方案

## 1. 背景与问题

### 1.1 重构历史

**第一次重构（已完成）**：
- 将Planner拆分为Judge + Plan两次LLM调用
- 拆分Generate模块为独立模块
- 统一Memory设计：证据 + 路径知识合一

### 1.2 当前架构问题（待解决）

**问题：Plan引入检索噪声**

当前架构中，Planner生成的是**假设性陈述句**作为Plan：

```
Planner → "The director is Mart Crowley" (陈述句作为Plan)
            ↓
Verifier → 从Plan中提取检索词 (Rewrite)
            ↓
Problem: 假设中的幻觉信息被带入检索，导致噪声
```

**具体表现**：
- Plan是LLM生成的假设性陈述，可能包含错误信息
- Rewrite需要从假设中提取实体/关系作为检索词
- 假设中的幻觉会被带入检索过程，降低检索质量
- 即使rewrite，效果也不稳定

---

## 2. 新架构方案

### 2.1 核心思想：Question-Hypothesis 对

将Planner的输出从"假设性陈述句"改为"子问题 + 假设答案"对：

```
当前: Plan = "The director is Mart Crowley"
新:  Plan = "What is the director's name? | Mart Crowley"
```

**优势**：
1. 子问题是干净的事实性查询，不含假设
2. 直接用子问题检索，无噪声引入
3. 假设答案是待验证对象，与文档对比即可

### 2.2 核心模块

| 模块 | 核心职责 |
|------|----------|
| **Planner** | Judge判断 + (Question, Hypothesis)对生成（两次LLM调用） |
| **Verifier** | 仅做检索 + 判断（直接用Question检索 + 验证Hypothesis） |
| **Memory** | 知识压缩 + 证据绑定（存储问答对 + 证据） |
| **Generate** | 基于已验证路径生成最终答案 |

### 2.3 统一记忆设计

**Memory = 验证过的问答对 + 证据**

| 内容 | 说明 |
|------|------|
| 精炼问答对 | 子问题 + 经过验证的假设答案 |
| 绑定证据 | 支持该答案的文档片段 |

---

## 3. 详细流程

### 3.1 整体流程图

```
┌─────────────────────────────────────────────────────────────────────┐
│                           迭代开始                                   │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Planner (2次LLM)                             │
├─────────────────────────────────────────────────────────────────────┤
│  输入: Question + Memory                                            │
│                                                                        │
│  [Step 1: Judge]                                                     │
│    Prompt: "基于当前记忆，是否能回答问题?"                           │
│    → YES: 进入Generate模块                                          │
│    → NO:  进入Step 2                                                │
│                                                                        │
│  [Step 2: Plan] (仅Judge=NO时)                                      │
│    Prompt: "生成子问题 + 假设答案"                                  │
│    输出格式: "sub_question | hypothesis"                            │
│    示例:                                                             │
│      plan1: What is the director's name? | Mart Crowley              │
│      plan2: When was the film released? | 2020                       │
└─────────────────────────────────────────────────────────────────────┘
                                │
              ┌─────────────────┴─────────────────┐
              │ Plan (Q|H对)                   YES → Generate
              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                           Verifier                                   │
├─────────────────────────────────────────────────────────────────────┤
│  输入: Question + Plan (Q|H对)                                      │
│                                                                        │
│  [Step 1: Retrieve]                                                  │
│    直接用 Plan中的Question部分检索（无Rewrite）                      │
│                                                                        │
│  [Step 2: Verify]                                                    │
│    Hypothesis vs 文档 → 判断verdict                                  │
└─────────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │ supported             │ contradicted           │ insufficient
        ▼                       ▼                       ▼
┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
│   Memory          │  │   Memory          │  │   不触发Memory    │
│   (触发记忆)      │  │   (触发记忆)      │  │   回到Planner     │
└───────────────────┘  └───────────────────┘  └───────────────────┘
        │                       │
        │ 知识压缩+证据绑定     │ 基于Docs纠正Hypothesis + 证据绑定
        │                       │
        ▼                       ▼ 短路当前轮
┌───────────────────────────────────────────────────────────────┐
│                       Memory 模块                              │
├───────────────────────────────────────────────────────────────┤
│  触发条件: Verdict=supported 或 contradicted                  │
│  输入: Question + Hypothesis + Docs + 当前Memory              │
│  核心: LLM调用进行知识压缩 + 证据绑定                         │
│  输出: 精炼后的问答对（Q: xxx | A: xxx）                      │
│  存储: 追加到Memory中                                               │
│                                                                       │
│  [示例]                                                         │
│  原始: What is the director's name? | Mart Crowley               │
│  验证: 实际导演是Joe Mantello                                     │
│  Memory精炼:                                                    │
│    Q: What is the director's name?                               │
│    A: Joe Mantello                                               │
│    Evidence: Document 1: Joe Mantello directed...                │
└───────────────────────────────────────────────────────────────┘
                                │
                                │ 返回迭代开始
                                ▼
                    ┌───────────────────────────┐
                    │    Planner重新Judge判断   │
                    └───────────────────────────┘
                                │
              ┌─────────────────┴─────────────────┐
              │                           ANSWER_READY
              ▼
        ┌─────────────────────────────┐
        │         Generate            │
        │ 输入: Question + Memory     │
        │ 输出: 最终答案              │
        └─────────────────────────────┘
```

### 3.2 迭代终止条件

| 条件 | 处理 |
|------|------|
| Judge=YES | 转入Generate模块 |
| 达到max_iter | Generate基于当前Memory生成尽力答案 |

---

## 4. 模块详细设计

### 4.1 Planner模块

**输入**: Question + Memory

**Step 1: Judge (LLM调用)**
- 功能: 判断当前记忆是否足以回答问题
- 输出: "YES" 或 "NO"

**Step 2: Plan (LLM调用，仅Judge=NO时)**
- 功能: 生成子问题 + 假设答案对
- 输出格式: `"sub_question | hypothesis"`
- 约束: 不能生成与已有记忆重复的问答对

### 4.2 Verifier模块

**输入**: Question + Plan (Q|H对)

**Step 1: Retrieve**
- 直接用Plan中的Question部分检索
- **移除**: 之前的Rewrite步骤（不再需要）

**Step 2: Verify**
- 功能: 对比Hypothesis与检索到的文档，输出verdict
- verdict类型:
  - `supported`: Hypothesis被证据支持 → 存储原假设
  - `contradicted`: Hypothesis被证据反驳 → 基于文档纠正Hypothesis
  - `insufficient`: 证据不足

### 4.3 Memory模块

**输入**: Question + sub_question + corrected_hypothesis + evidence + 当前Memory

**核心逻辑**:
- 仅当verdict=supported或contradicted时触发
- **不再调用LLM**（简化流程）
- 直接使用Verifier的 `corrected_hypothesis` 作为答案
- 直接使用Verifier的 `evidence`

**Memory格式**:
```
Q: [Sub-Question] | A: [Corrected Hypothesis from Verifier] | Evidence: [Verifier's Evidence]
```

**示例**:
```
Q: Who directed "Ronnie Rocket"? | A: David Lynch | Evidence: Ronnie Rocket is an unfinished film project written by David Lynch, who intended to direct it.
```

**关键特性**:
- **复用Verifier输出**：Memory的A直接使用Verifier的corrected_hypothesis
- **移除Memory LLM调用**：减少一次LLM调用，降低延迟
- **不展示verdict**：Memory中全是验证过的正确信息
- **Planner可直接识别**：问答对格式，Planner可识别已验证的问题

**存储**: 累积到Memory中

### 4.4 Generate模块

**输入**: Question + Memory

**功能**: 基于已验证的完整路径知识生成最终答案

---

## 5. 设计要点

### 5.1 移除Rewrite

- **原因**: Question-Hypothesis对使Question本身就是干净检索词
- **收益**: 减少一次LLM调用，降低延迟和成本

### 5.2 Memory不展示verdict

Memory中存储的全是经过验证的正确问答对，verdict信息冗余，无需展示。

### 5.3 记忆添加顺序

按照验证成功的顺序累积，有效问答对自动积累。

### 5.4 contradicted处理

1. Verifier输出 `corrected_hypothesis`（基于文档纠正的答案）
2. Memory直接复用 Verifier 的 `corrected_hypothesis` 作为答案
3. Memory直接复用 Verifier 的 `evidence`
4. 触发短路，避免错误累积

### 5.8 移除Memory LLM调用

- **原因**: Verifier已经输出了简洁的 `corrected_hypothesis`
- **做法**: Memory模块不再调用LLM，直接格式化输出
- **收益**: 减少一次LLM调用，降低延迟和成本
- **Memory输出**: `Q: [Sub-Question] | A: [Corrected Hypothesis] | Evidence: [Verifier's Evidence]`

### 5.5 insufficient处理

1. 不触发Memory更新
2. 回到Planner，尝试新的可能
3. 直到达到max_iter

### 5.6 Memory压缩粒度

采用高频压缩策略，每次验证成功都进行压缩。

### 5.7 Planner识别已有问答对

Planner在生成新问答对时，需要能够识别Memory中已存在的问答对，避免重复验证。

---

## 6. 与原架构对比

| 方面 | 原架构 (Plan陈述句) | 新架构 (Q-H对) |
|------|---------------------|----------------|
| Planner输出 | "The director is Mart Crowley" | "What is the director? \| Mart Crowley" |
| 检索词来源 | Rewrite从Plan提取 | 直接用Question |
| 检索噪声 | 高（假设可能含幻觉） | 低（Question是干净查询） |
| Verifier调用 | Rewrite + Retrieve + Verify | Retrieve + Verify |
| Memory存储 | 路径级别精炼知识 | 问答对 + 证据 |
| 假设验证 | 验证Plan陈述句 | 验证Hypothesis答案 |

---

## 7. 实施计划

### 7.1 需要修改的文件

| 文件 | 修改内容 | 状态 |
|------|----------|------|
| `prompts/GPT35/planner_plan_user.md` | 改为生成Q-H对格式 | 已完成 |
| `rpvm_pipeline.py` | `_parse_plans` 适配新格式 | 已完成 |
| `rpvm_pipeline.py` | `_parse_question_hypothesis` 新增方法 | 已完成 |
| `rpvm_pipeline.py` | `_verify_plan` 移除rewrite调用 | 已完成 |
| `rpvm_pipeline.py` | `_verify_with_docs` 改为验证Hypothesis | 已完成 |
| `rpvm_pipeline.py` | `_update_memory` 适配新参数 | 已完成 |
| `prompt_loader.py` | `get_verifier_prompt` 适配新参数 | 已完成 |
| `prompt_loader.py` | `get_memory_prompt` 适配新参数 | 已完成 |
| `prompts/GPT35/verifier_*.md` | 改为验证Hypothesis | 已完成 |
| `prompts/GPT35/memory_*.md` | 改为问答对格式 | 已完成 |

### 7.2 保留的功能

- Judge判断逻辑不变
- Generate模块基本不变
- 短路逻辑不变
- Memory压缩逻辑不变

### 7.3 已移除的代码

- `_extract_verification_query` 方法（Rewrite步骤）

---

## 8. 优化方案：单步生成策略

### 8.1 问题背景

**问题表现**（实验案例）：

在第二轮及后续迭代中，Planner生成了大量冗余的plan：

```
迭代1:
  plan1: Who directed the film? | Lê Lâm  → contradicted → Maung Wunna
  plan2: What award did Lê Lâm win? | FIPRESCI Prize

迭代2:
  plan1: What award did Maung Wunna win? | Myanmar Academy Award
  plan2: Did Maung Wunna receive international awards? | No info  → insufficient
  plan3: Did Maung Wunna win award for this film? | No info  → insufficient

迭代3:
  plan1: Which specific award did Maung Wunna win? | Best Director  → insufficient
  plan2: Did Maung Wunna receive Best Director award for this film? | No info
```

**问题分析**：
- 后续迭代生成了多个类似的plan（都在问"获得了什么奖"）
- 这些plan之间存在大量冗余
- 增加了不必要的检索开销

### 8.2 优化目标

| 迭代次数 | 生成 plan 数量 | 目的 |
|---------|---------------|------|
| **第一次** | 多个（可选） | 生成完整的推理路径 |
| **后续迭代** | **仅 1 个** | 只生成"下一个"需要验证的子问题 |

### 8.3 优化方案

#### 核心思想

- **首次迭代**：保持现有提示词，生成覆盖问题所有方面的plan
- **后续迭代**：根据Memory中已有的问答对，只生成"下一个需要验证的问题"

#### 实现方式

**修改 Planner 提示词**：

1. **首次迭代提示词**（保持现有）：
   ```
   Generate all necessary plans covering all aspects of the question
   ```

2. **后续迭代提示词**（新增）：
   ```
   Based on Memory, what is the NEXT question that needs to be verified?

   Memory:
   Q: Who directed the film? | A: Maung Wunna
   Q: What award did Maung Wunna win? | Myanmar Motion Picture Academy Award

   Original Question: What award did the director win?

   Next question (output format: "sub_question | hypothesis"):
   ```

#### 流程图

```
┌─────────────────────────────────────────────────────────────────────┐
│                           迭代开始                                   │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Planner (2次LLM)                             │
├─────────────────────────────────────────────────────────────────────┤
│  [Step 1: Judge]                                                     │
│    → YES: 进入Generate模块                                          │
│    → NO:  进入Step 2                                                │
│                                                                        │
│  [Step 2: Plan]                                                      │
│    ├─ 首次迭代: 生成多个plan覆盖问题各个方面                        │
│    └─ 后续迭代: 仅生成下一个需要验证的问题                          │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                           Verifier                                   │
├─────────────────────────────────────────────────────────────────────┤
│  仅验证单个plan                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 8.4 需要修改的内容

| 文件 | 修改内容 | 状态 |
|------|----------|------|
| `rpvm_pipeline.py` | `_run_single_question` 传递 `iter_idx` 给 Planner | 已完成 |
| `rpvm_pipeline.py` | `_planner_plan` 根据迭代次数选择提示词 | 已完成 |
| `prompt_loader.py` | 新增 `get_planner_plan_prompt_first` 和 `get_planner_plan_prompt_next` | 已完成 |
| `prompts/GPT35/planner_plan_user.md` | 重命名为 `planner_plan_first_user.md` | 已完成 |
| `prompts/GPT35/` | 新增 `planner_plan_next_user.md` | 已完成 |

### 8.5 预期效果

**优化前**：
```
迭代1: 2个plans → 2次检索
迭代2: 3个plans → 3次检索
迭代3: 2个plans → 2次检索
总计: 7次检索
```

**优化后**：
```
迭代1: 2个plans → 2次检索
迭代2: 1个plan  → 1次检索
迭代3: 1个plan  → 1次检索
总计: 4次检索（减少43%）
```

---

## 9. 优化方案：Memory模块复用Verifier输出

### 9.1 问题背景

**问题表现**（实验案例）：

Memory输出过于冗余：
```
Q: Who directed the film "Ronnie Rocket"? | A: David Lynch intended to direct the film "Ronnie Rocket," which he also wrote, but the project was never completed or produced.
```

**问题分析**：
1. Verifier已输出简洁的 `corrected_hypothesis`
2. Memory模块又调用LLM重新生成答案，导致冗余
3. LLM倾向于生成解释性答案，而非简洁答案

### 9.2 优化方案

**核心思想**：复用Verifier的输出，不再让Memory生成答案

**当前流程（冗余）**：
```
Verifier: corrected_hypothesis (简洁答案) → Memory: 重新生成答案 → 冗余
```

**优化后流程（精简）**：
```
Verifier: corrected_hypothesis + evidence → Memory: 直接格式化输出
```

### 9.3 Memory新格式

```
Q: [Sub-Question] | A: [Corrected Hypothesis from Verifier] | Evidence: [Verifier's Evidence]
```

**示例**：
```
Q: Who directed "Ronnie Rocket"? | A: David Lynch | Evidence: Ronnie Rocket is an unfinished film project written by David Lynch, who intended to direct it.
```

### 9.4 需要修改的内容

| 文件 | 修改内容 | 状态 |
|------|----------|------|
| `rpvm_pipeline.py` | `_update_memory` 不再调用LLM | 已完成 |
| `rpvm_pipeline.py` | 直接使用 Verifier 的 `corrected_hypothesis` 和 `evidence` | 已完成 |
| `rpvm_pipeline.py` | 传入 `evidence` 参数给 Memory | 已完成 |
| `rpvm_pipeline.py` | 输出格式改为 `Q: \| A: \| Evidence:` | 已完成 |

### 9.5 预期效果

| 指标 | 优化前 | 优化后 |
|------|--------|--------|
| LLM调用次数 | 3次/迭代（Planner+Verifier+Memory） | 2次/迭代（Planner+Verifier） |
| 延迟 | 较高 | 降低30-40% |
| 答案冗余度 | 高（解释性答案） | 低（简洁答案） |

### 9.6 与原Memory模块的差异

| 方面 | 原实现（第4.3节） | 新实现（第9节） |
|------|-------------------|-----------------|
| Memory输出 | 调用LLM生成 | 直接格式化 |
| 答案来源 | LLM重新生成 | Verifier的corrected_hypothesis |
| Evidence来源 | 重新检索 | Verifier的evidence |
| 格式 | Q: \| A: | Q: \| A: \| Evidence: |
| LLM调用 | 3次/迭代 | 2次/迭代 |

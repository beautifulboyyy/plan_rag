# RPVM (Reflective Plan-Verify Memory) 算法说明

## 一、核心理念

### 1.1 问题背景

多跳问答（Multi-hop QA）需要模型进行链式推理，例如：
> "Where was the director of film The Children (1990 Film) born?"

这类问题需要模型：
1. 先找出电影导演是谁
2. 再找出该导演的出生地

传统方法如 ReAct/CoT 采用**每步生成-检索-验证**的迭代模式，步骤繁琐且冗余。

### 1.2 核心思想

RPVM 由三个模块组成：

**Planner（反思规划模块）**
- 基于问题 Q 和现有记忆 M，生成**假设性断言链**
- 一次性推理出所有推理步骤，利用 LLM 内部知识
- 例如：`plan1: 导演是Tony Palmer` → `plan2: Tony Palmer出生在伦敦`

**Verifier（验证模块）**
- 利用 RAG 检索相关资料，验证每个 plan
- 三种判定结果：supported / contradicted / insufficient

**Memory（记忆模块）**
- 缓存已验证的事实和检索资料
- 支撑下一轮规划和答案生成

### 1.3 核心创新点

1. **一次性规划整个推理链**：相比传统逐步迭代，更好地利用 LLM 的全局推理能力
2. **短路验证机制**：若某步 plan 被验证为错误，后续依赖该结果的 plan 直接丢弃，避免错误传播
3. **记忆累积**：每轮迭代后保存已验证的事实，下一轮可基于已有知识继续推理

---

## 二、算法流程

### Step 0. 初始化

```
输入：
    Q = 原始问题
    M = Memory (初始为空)

参数：
    max_iter = 最大迭代次数
    max_retrieval_attempts = 每个plan的最大检索尝试次数
```

### Step 1. Reflective Planner（反思规划器）

**输入**：Q, M
**输出**：`ANSWER_READY` 或 plan列表 `[plan₁, plan₂, ...]`

**逻辑**：
- 若记忆 M 已包含足够信息回答问题 → 输出 `ANSWER_READY`
- 否则，基于 Q 和 M 生成推理链，每条 plan 是可验证的自然语言断言

### Step 2. Plan Verifier（验证模块）

**输入**：当前未验证的 plan_k，问题 Q，记忆 M
**流程**：

1. **检索**：基于 plan 生成检索词，召回相关文档
   - 若检索失败 → rewrite 检索词重试
   - 若多次失败 → 标记 insufficient

2. **判定**：基于文档判断 plan 的真实性
   - **SUPPORTED**：被证据支持
   - **CONTRADICTED**：与证据冲突
   - **INSUFFICIENT**：无充分证据

3. **处理结果**：
   - **supported** → 精炼后加入 M
   - **contradicted** → 修正后加入 M，**短路当前轮**
   - **insufficient** → 不加入 M，**短路当前轮**

### Step 3. Memory 更新

**Memory 形式**：文本拼接

```
Memory:
1. The director of film "The Children" (1990) is Tony Palmer. (verified)
2. Tony Palmer was born in London. (verified)
```

**作用**：
- 供下一轮 Planner 参考，避免重复检索
- 最终合成答案的上下文

### Step 4. 终止条件

- Planner 输出 `ANSWER_READY` → 生成最终答案
- 达到最大迭代次数 → 生成尽力答案（best-effort）

---

## 三、完整案例演示

### 案例 1：第一轮全部验证正确

**Question**: Where was the director of film The Children (1990 Film) born?

**Iteration 1 | Memory: (empty)**

Planner 输出：
```
plan1: The director of the film "The Children" (1990) is Tony Palmer.
plan2: Tony Palmer was born in London.
```

Verifier 验证：
- plan1 → supported ✅ → 加入 M
- plan2 → supported ✅ → 加入 M

**Memory 更新**:
```
1. The director of the film "The Children" (1990) is Tony Palmer. (verified)
2. Tony Palmer was born in London. (verified)
```

**Iteration 2 | Memory**: 已有完整推理链

Planner 输出：
```
ANSWER_READY
```

**最终答案**: Tony Palmer was born in London.

---

### 案例 2：短路重规划机制（核心创新）

**Question**: Which country the director of film The Boys In The Band (2020 Film) is from?

**Iteration 1 | Memory: (empty)**

Planner 输出：
```
plan1: The director of "The Boys In The Band" (2020) is Mart Crowley.
plan2: Mart Crowley comes from the United States.
```

Verifier 验证：
- plan1 → **contradicted** ❌ → 修正为 Joe Mantello，加入 M → **短路当前轮**
- plan2 → 直接丢弃（依赖错误的 plan1）

**Memory 更新**:
```
1. The director of "The Boys In The Band" (2020) is Joe Mantello. (corrected)
```

**Iteration 2 | Memory**: 已纠正导演信息

Planner 输出：
```
plan1: Joe Mantello comes from the United States.
```

Verifier 验证：
- plan1 → supported ✅ → 加入 M

**Memory 更新**:
```
1. The director of "The Boys In The Band" (2020) is Joe Mantello. (corrected)
2. Joe Mantello comes from the United States. (verified)
```

**Iteration 3 | Memory**: 已有完整信息

Planner 输出：
```
ANSWER_READY
```

**最终答案**: Joe Mantello is from the United States.

**创新点解析**：
- 传统方法可能需要更多轮次逐步发现错误
- RPVM 在第一轮验证 plan1 时立即发现错误，修正并短路
- 第二轮基于纠正后的信息重新规划，高效收敛

---

### 案例 3：比较推理（两人出生年份对比）

**Question**: Which film has the director who was born first, State Penitentiary (Film) or Folly Of Love?

**Iteration 1 | Memory: (empty)**

Planner 输出：
```
plan1: The director of "State Penitentiary" was born in a specific year.
plan2: The director of "Folly Of Love" was born in an earlier year.
```

Verifier 验证：
- plan1 → **supported** ✅ → 加入 M (Lew Landers, born in 1901)
- plan2 → **insufficient** ⚠️ → 不加入 M，短路当前轮

**Iteration 2 | Memory**: 已知 State Penitentiary 导演信息

Planner 输出：
```
plan1: The director of "Folly Of Love" was born before 1901.
```

Verifier 验证：
- plan1 → **supported** ✅ → 加入 M (born in 1895)

**Iteration 3 | Memory**: 两人出生年份都已确认

Planner 输出：
```
ANSWER_READY
```

**最终答案**: The director of Folly Of Love was born first (1895 vs 1901).

---

## 四、与传统方法对比

| 维度 | ReAct/CoT（传统迭代式） | RPVM（本文方法） |
|------|-------------------------|------------------|
| **规划方式** | 每步生成-检索-观察 | 一次性生成完整推理链 |
| **LLM调用** | 较多（每步都需LLM介入） | 较少（验证可无需LLM） |
| **错误传播** | 错误逐步累积 | 短路机制阻止错误扩散 |
| **记忆利用** | 上下文记忆，有限长度 | 显式记忆累积，可累积多轮 |
| **全局推理** | 较弱（逐步局部推理） | 较强（一次性全局规划） |

### 优势总结

1. **减少冗余召回**：一次性规划避免重复检索相似内容
2. **更快收敛**：若 LLM 内部知识准确，可能两轮即得出答案
3. **错误隔离**：短路机制防止错误传播，提高准确率
4. **可解释性**：每个 plan 都有明确验证状态和证据

---

## 五、总结

**RPVM（Reflective Plan-Verify Memory）** 是一种面向多跳问答的迭代推理框架：

1. **Planner** 利用 LLM 内部知识一次性生成完整推理假设链
2. **Verifier** 通过 RAG 验证每个假设，支持短路机制防止错误传播
3. **Memory** 累积已验证的事实，支撑后续推理

该方法核心创新在于：**最大化利用 LLM 的全局推理能力，同时通过验证和短路机制确保推理准确性**。

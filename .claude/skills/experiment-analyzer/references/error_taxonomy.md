# Error Taxonomy

## Error Categories

### 1. Retrieval Failure (检索失败)

**Definition**: Retrieved documents do not contain relevant evidence for the sub-question.

**Detection**:
- Sub-question has no matching evidence in retrieved docs
- Global evidence extraction produces empty or irrelevant content

**Indicators**:
- `docs_retrieved` > 0 but `global_evidence` is empty/short
- Retrieval scores all < 0.8

**Example**:
```
Question: Who directed the film X?
Retrieved: [doc about actor, doc about plot, doc about awards]
Evidence: "" (empty or minimal)
```

### 2. Early Termination (提前终止)

**Definition**: Judge incorrectly returns YES when sufficient evidence is lacking.

**Detection**:
- `judge_result` = "YES" on first iteration
- `total_retrievals` = 1
- Final F1 < 0.5

**Indicators**:
- Judge YES rate on low-F1 cases
- Single-iteration completion with incorrect answer

**Example**:
```
Iteration 1:
  Judge: YES (should be NO)
  Final answer: Wrong answer
  Memory: Incomplete evidence
```

### 3. Reasoning Error (推理错误)

**Definition**: Evidence is retrieved but reasoning/answer generation fails.

**Detection**:
- Multiple iterations (retrievals >= 2)
- Judge eventually returns YES
- F1 still < 0.5

**Indicators**:
- High retrieval count but low accuracy
- Evidence exists but answer is incorrect

**Example**:
```
Retrieved evidence contains correct answer
But final_answer is different or partial
```

### 4. Plan Mismatch (规划偏离)

**Definition**: Generated sub-questions do not follow the planned intent.

**Detection**:
- Sub-question deviates from original plan steps
- Plan items remain unfinished after iterations

**Indicators**:
- `plan_updated` shows persistent unfinished items
- Sub-questions are redundant or off-topic

### 5. Memory Update Failure (记忆更新失败)

**Definition**: New evidence not properly integrated into memory.

**Detection**:
- `memory_updated` = false despite new retrieval
- Memory doesn't grow across iterations

**Indicators**:
- Final memory same as initial
- Evidence accumulation stalls

## Severity Levels

| Level | F1 Range | Description |
|-------|----------|-------------|
| Critical | 0.0 - 0.2 | Completely wrong answer |
| Severe | 0.2 - 0.5 | Partially correct |
| Moderate | 0.5 - 0.8 | Mostly correct, missing details |
| Minor | 0.8 - 1.0 | Trivial errors |

## Analysis Metrics per Category

- **Count**: Number of errors in category
- **Percentage**: Of total errors
- **Avg F1**: Average F1 for category
- **Typical Pattern**: Common manifestation

# Data Schema Reference

## intermediate_data.jsonl

Each line is a JSON object representing one question's full execution trace.

### Top-level Fields

| Field | Type | Description |
|-------|------|-------------|
| `question` | string | The multi-hop question |
| `golden_answers` | array | Ground truth answers |
| `final_answer` | string | Model's final answer |
| `final_memory` | string | Accumulated evidence |
| `metric_score` | object | {f1, acc} |
| `total_retrievals` | int | Number of retrieval calls |
| `iterations` | array | Execution trace |

### Iteration Object

| Field | Type | Description |
|-------|------|-------------|
| `iteration` | int | Iteration number (1-based) |
| `phase` | string | "ReSP" or "Judge" |
| `judge_result` | string | "YES" or "NO" (Judge phase) |
| `sub_question` | string | Generated sub-question |
| `docs_retrieved` | int | Number of docs retrieved |
| `global_evidence` | string | Extracted evidence |
| `local_answer` | string | Answer to sub-question |
| `plan_updated` | string | Updated plan state |
| `memory_updated` | boolean | Whether memory changed |
| `final_answer` | string | (Judge phase) Final answer |

### metric_score.txt Format

```
f1: <value>
acc: <value>
```

## retrieval_cache.json

Key: question string
Value: array of retrieved passages

### Passage Object

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Document ID |
| `contents` | string | Passage text |
| `score` | float | Retrieval similarity score |

## Question Types (2WikiMultihopQA)

| Type | Description |
|------|-------------|
| `compositional` | Requires combining facts from multiple sources |
| `bridge_comparison` | Comparison with bridging entity |
| `simple_comparison` | Direct comparison |
| `inference` | Requires logical inference |

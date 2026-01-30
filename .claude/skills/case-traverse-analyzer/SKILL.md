---
name: case-traverse-analyzer
description: Analyzes single question execution traces in PlanRAG experiments, generating detailed trace reports for error case investigation. Use when Claude needs to inspect a specific question's full iteration history, Judge decisions, retrieved documents, and reasoning steps to identify analysis candidates.
---

# Case Traverse Analyzer Skill

This skill generates detailed trace reports for individual question cases.

## Usage

When user asks to analyze a specific question or list error cases:
```bash
analyze_case --path <experiment_directory> --question "question text"
# or
list_errors --path <experiment_directory> --type <error_type> --limit 10
```

## Workflow

1. **Load Data** - Read intermediate_data.jsonl for question trace
2. **Extract Trace** - Reconstruct full iteration history
3. **Analyze Each Step** - Judge decisions, sub-questions, retrieved docs
4. **Generate Report** - Output detailed Markdown trace

## Output

Generates `<case_id>_trace.md` in the experiment directory containing:
- Question and golden answer
- Full iteration timeline
- Each iteration's Judge result, sub-question, retrieved evidence
- Final answer comparison
- Problematic step identification

## Use Case

Use after `experiment-result-analyzer` identifies error cases:
1. Run experiment-analyzer to get error distribution
2. Select interesting error cases
3. Use case-traverse-analyzer to inspect specific traces

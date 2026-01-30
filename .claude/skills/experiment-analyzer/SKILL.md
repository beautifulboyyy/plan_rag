---
name: experiment-result-analyzer
description: Analyzes multi-hop question answering experiment results, providing iteration diagnostics, Judge behavior analysis, and error categorization. Focuses on data-level analysis and error case classification without recommendations. Use when Claude needs to analyze experiment output directories containing intermediate_data.jsonl, retrieval_cache.json to generate error-focused Markdown reports.
---

# Experiment Result Analyzer Skill

This skill analyzes PlanRAG experiment results with focus on error analysis and categorization.

## Usage

When user asks to analyze an experiment result:
```bash
analyze_experiment --path <experiment_directory>
```

The skill will generate a Markdown report saved to `<experiment_directory>/analysis_report.md`.

## Workflow

1. **Load Data** - Read intermediate_data.jsonl, intermediate_data.json, retrieval_cache.json
2. **Core Metrics** - Calculate F1, Acc, retrieval statistics
3. **Iteration Analysis** - Judge rounds, retrieval counts, early termination detection
4. **Type Performance** - Break down metrics by question type
5. **Error Classification** - Categorize errors by type (early_termination, reasoning_error, retrieval_failure)
6. **Generate Report** - Output Markdown with error details to experiment directory

## References

- [Data Schema](references/data_schema.md) - Input file formats
- [Error Taxonomy](references/error_taxonomy.md) - Error classification system

## Output

Generates `analysis_report.md` in the experiment directory containing:
- Executive summary (core metrics)
- Performance by question type
- Iteration behavior analysis
- Retrieval quality statistics
- Error distribution with detailed case examples

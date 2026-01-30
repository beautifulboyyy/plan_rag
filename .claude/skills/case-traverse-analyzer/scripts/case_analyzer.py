#!/usr/bin/env python3
"""
Case Traverse Analyzer for PlanRAG experiments.
Generates detailed trace reports for single question cases.
"""

import json
import sys
from pathlib import Path
from datetime import datetime


def load_experiment_data(exp_dir: Path):
    """Load all experiment data files."""
    data_by_question = {}

    # Load intermediate_data.json for metrics and metadata
    json_path = exp_dir / "intermediate_data.json"
    if json_path.exists():
        with open(json_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
            for item in json_data:
                q = item.get('question', '')
                data_by_question[q] = {
                    'golden_answers': item.get('golden_answers', []),
                    'metadata': item.get('metadata', {}),
                    'metric_score': item.get('output', {}).get('metric_score', {}),
                }

    # Load intermediate_data.jsonl for iteration traces
    jsonl_path = exp_dir / "intermediate_data.jsonl"
    if jsonl_path.exists():
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                item = json.loads(line)
                q = item.get('question', '')
                if q in data_by_question:
                    data_by_question[q].update({
                        'iterations': item.get('iterations', []),
                        'final_answer': item.get('final_answer', ''),
                        'final_memory': item.get('final_memory', ''),
                        'total_retrievals': item.get('total_retrievals', 0),
                    })
                else:
                    # Question not in json, add basic info
                    data_by_question[q] = {
                        'iterations': item.get('iterations', []),
                        'final_answer': item.get('final_answer', ''),
                        'final_memory': item.get('final_memory', ''),
                        'total_retrievals': item.get('total_retrievals', 0),
                    }

    return data_by_question


def generate_case_report(question: str, data: dict) -> str:
    """Generate detailed trace report for a single case."""
    golden = data.get('golden_answers', [])
    iterations = data.get('iterations', [])
    final_answer = data.get('final_answer', '')
    final_memory = data.get('final_memory', '')
    total_retrievals = data.get('total_retrievals', 0)
    metric = data.get('metric_score', {})
    metadata = data.get('metadata', {})

    lines = [
        f"# Case Trace Report",
        f"",
        f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"",
        f"---",
        f"",
        f"## Question",
        f"",
        f"{question}",
        f"",
        f"---",
        f"",
        f"## Metadata",
        f"",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| Type | {metadata.get('type', 'N/A')} |",
        f"| Golden Answers | {', '.join(golden) if golden else 'N/A'} |",
        f"| Total Retrievals | {total_retrievals} |",
        f"| F1 Score | {metric.get('f1', 'N/A')} |",
        f"| Acc Score | {metric.get('acc', 'N/A')} |",
        f"",
        f"---",
        f"",
        f"## Final Answer",
        f"",
        f"**Model Answer**: {final_answer}",
        f"",
        f"---",
        f"",
        f"## Iteration Timeline",
        f"",
    ]

    # Group iterations by phase
    for i, it in enumerate(iterations):
        phase = it.get('phase', 'Unknown')
        lines.append(f"### Iteration {i+1} - {phase}")
        lines.append("")

        if phase == 'ReSP':
            lines.append(f"**Sub-Question**: {it.get('sub_question', 'N/A')}")
            lines.append("")
            lines.append(f"**Docs Retrieved**: {it.get('docs_retrieved', 0)}")
            lines.append("")
            lines.append(f"**Global Evidence**:")
            lines.append(f"> {it.get('global_evidence', 'N/A')[:500]}")
            lines.append("")
            lines.append(f"**Local Answer**:")
            lines.append(f"> {it.get('local_answer', 'N/A')}")
            lines.append("")
            lines.append(f"**Plan Updated**:")
            for line in (it.get('plan_updated', '') or '').split('\n'):
                if line.strip():
                    lines.append(f"> {line}")
            lines.append("")
            lines.append(f"**Memory Updated**: {it.get('memory_updated', False)}")
            lines.append("")

        elif phase == 'Judge':
            judge_result = it.get('judge_result', 'N/A')
            lines.append(f"**Judge Result**: {judge_result}")
            lines.append("")
            if judge_result == 'YES':
                lines.append(f"**Final Answer**: {it.get('final_answer', 'N/A')}")
                lines.append("")

        lines.append("---")
        lines.append("")

    # Final memory
    lines.extend([
        f"",
        f"## Final Memory (Evidence Pool)",
        f"",
        f"```",
        f"{final_memory[:2000]}..." if len(final_memory) > 2000 else f"{final_memory}",
        f"```",
        f"",
    ])

    return '\n'.join(lines)


def list_error_cases(data_by_question: dict, error_type: str = None, limit: int = 10):
    """List error cases for selection."""
    error_cases = []

    for q, data in data_by_question.items():
        f1 = data.get('metric_score', {}).get('f1', 0)
        if f1 >= 0.8:
            continue  # Skip correct cases

        iterations = data.get('iterations', [])
        retrievals = data.get('total_retrievals', 0)

        # Categorize error
        last_judge = None
        for it in reversed(iterations):
            if it.get('phase') == 'Judge':
                last_judge = it.get('judge_result')
                break

        if last_judge == 'YES' and retrievals <= 1:
            category = 'early_termination'
        elif retrievals >= 2:
            category = 'reasoning_error'
        else:
            category = 'retrieval_failure'

        if error_type is None or category == error_type:
            error_cases.append({
                'question': q,
                'f1': f1,
                'category': category,
                'retrievals': retrievals,
                'answer': data.get('final_answer', '')[:80]
            })

    # Sort by F1 (ascending - worst first)
    error_cases.sort(key=lambda x: x['f1'])

    return error_cases[:limit]


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  case_analyzer.py --path <exp_dir> --question '<question>'")
        print("  case_analyzer.py --path <exp_dir> --list-errors [--type <type>] [--limit N]")
        sys.exit(1)

    exp_dir = Path(sys.argv[1])

    # Parse arguments
    args = sys.argv[2:]
    question = None
    list_errors = False
    error_type = None
    limit = 10

    i = 0
    while i < len(args):
        if args[i] == '--question' and i + 1 < len(args):
            question = args[i + 1]
            i += 2
        elif args[i] == '--list-errors':
            list_errors = True
            i += 1
        elif args[i] == '--type' and i + 1 < len(args):
            error_type = args[i + 1]
            i += 2
        elif args[i] == '--limit' and i + 1 < len(args):
            limit = int(args[i + 1])
            i += 2
        else:
            i += 1

    data_by_question = load_experiment_data(exp_dir)

    if not data_by_question:
        print("Error: No data found in experiment directory")
        sys.exit(1)

    if list_errors:
        cases = list_error_cases(data_by_question, error_type, limit)
        print(f"\n{'='*80}")
        print(f"{'F1':<6} {'Ret':<4} {'Category':<18} Question")
        print(f"{'='*80}")
        for i, case in enumerate(cases):
            q = case['question'][:50] + '...' if len(case['question']) > 50 else case['question']
            print(f"{case['f1']:<6.3f} {case['retrievals']:<4} {case['category']:<18} {q}")
        print(f"{'='*80}")
        print(f"Total: {len(cases)} cases shown")
        return

    if question:
        if question not in data_by_question:
            # Try to find partial match
            matches = [k for k in data_by_question.keys() if question.lower() in k.lower()]
            if len(matches) == 1:
                question = matches[0]
            elif len(matches) > 1:
                print(f"Multiple matches found:")
                for m in matches[:5]:
                    print(f"  - {m[:80]}")
                return
            else:
                print("Question not found in experiment data")
                return

        data = data_by_question[question]
        report = generate_case_report(question, data)

        # Save report
        safe_name = question[:30].replace('/', '_').replace(' ', '_')
        output_path = exp_dir / f"{safe_name}_trace.md"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"Trace report saved to: {output_path}")
        print(f"\nPreview:")
        print(report[:1000])
    else:
        print("Please specify --question or --list-errors")


if __name__ == "__main__":
    main()

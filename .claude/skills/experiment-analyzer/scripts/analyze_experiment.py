#!/usr/bin/env python3
"""
Experiment Result Analyzer for PlanRAG experiments.
Analyzes intermediate_data.jsonl, retrieval_cache.json, and metric_score.txt
to generate diagnostic Markdown reports.
"""

import json
import sys
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime


class ExperimentAnalyzer:
    def __init__(self, exp_dir: str):
        self.exp_dir = Path(exp_dir)
        self.data = []
        self.cache = {}
        self.metrics = {}
        self.report = []

    def load_data(self):
        """Load all experiment data files."""
        # Load intermediate_data.json for metrics and metadata
        json_path = self.exp_dir / "intermediate_data.json"
        metrics_by_question = {}
        if json_path.exists():
            with open(json_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
                for item in json_data:
                    q = item.get('question', '')
                    metric_score = item.get('output', {}).get('metric_score', {})
                    metadata = item.get('metadata', {})
                    metrics_by_question[q] = {
                        'metric_score': metric_score,
                        'metadata': metadata
                    }

        # Load intermediate_data.jsonl for iteration trace
        jsonl_path = self.exp_dir / "intermediate_data.jsonl"
        if jsonl_path.exists():
            with open(jsonl_path, 'r', encoding='utf-8') as f:
                for line in f:
                    item = json.loads(line)
                    q = item.get('question', '')
                    # Merge with metrics from intermediate_data.json
                    if q in metrics_by_question:
                        item['metric_score'] = metrics_by_question[q]['metric_score']
                        item['metadata'] = metrics_by_question[q]['metadata']
                    self.data.append(item)

        # Load retrieval_cache.json
        cache_path = self.exp_dir / "retrieval_cache.json"
        if cache_path.exists():
            with open(cache_path, 'r', encoding='utf-8') as f:
                self.cache = json.load(f)

        # Load metric_score.txt
        metric_path = self.exp_dir / "metric_score.txt"
        if metric_path.exists():
            with open(metric_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('f1:'):
                        self.metrics['f1'] = float(line.split(':')[1].strip())
                    elif line.startswith('acc:'):
                        self.metrics['acc'] = float(line.split(':')[1].strip())

    def analyze_core_metrics(self):
        """Calculate core performance metrics."""
        f1_scores = [item.get('metric_score', {}).get('f1', 0) for item in self.data]
        acc_scores = [item.get('metric_score', {}).get('acc', 0) for item in self.data]

        return {
            'total': len(self.data),
            'f1_mean': sum(f1_scores) / len(f1_scores) if f1_scores else 0,
            'f1_std': self._std(f1_scores),
            'acc_mean': sum(acc_scores) / len(acc_scores) if acc_scores else 0,
            'perfect_f1': sum(1 for s in f1_scores if s >= 0.8),
            'perfect_acc': sum(1 for s in acc_scores if s == 1.0),
            'zero_f1': sum(1 for s in f1_scores if s == 0),
        }

    def _std(self, values):
        """Calculate standard deviation."""
        if len(values) < 2:
            return 0
        mean = sum(values) / len(values)
        return (sum((x - mean) ** 2 for x in values) / len(values)) ** 0.5

    def analyze_by_type(self):
        """Analyze performance by question type."""
        type_stats = defaultdict(lambda: {'f1': [], 'acc': [], 'count': 0})
        for item in self.data:
            qtype = item.get('metadata', {}).get('type', 'unknown')
            type_stats[qtype]['f1'].append(item.get('metric_score', {}).get('f1', 0))
            type_stats[qtype]['acc'].append(item.get('metric_score', {}).get('acc', 0))
            type_stats[qtype]['count'] += 1

        return {
            t: {
                'count': stats['count'],
                'f1_mean': sum(stats['f1']) / len(stats['f1']),
                'acc_mean': sum(stats['acc']) / len(stats['acc']),
                'perfect_rate': sum(1 for s in stats['acc'] if s == 1.0) / len(stats['acc']) * 100
            }
            for t, stats in type_stats.items()
        }

    def analyze_iterations(self):
        """Analyze iteration behavior."""
        judge_rounds = []
        retrievals = []

        for item in self.data:
            iterations = item.get('iterations', [])
            judge_count = len([i for i in iterations if i.get('phase') == 'Judge'])
            judge_rounds.append(judge_count)
            retrievals.append(item.get('total_retrievals', 0))

        # Judge YES analysis
        judge_yes_correct = 0
        judge_yes_incorrect = 0
        for item in self.data:
            f1 = item.get('metric_score', {}).get('f1', 0)
            is_correct = f1 >= 0.8
            iterations = item.get('iterations', [])
            for it in reversed(iterations):
                if it.get('phase') == 'Judge' and it.get('judge_result') == 'YES':
                    if is_correct:
                        judge_yes_correct += 1
                    else:
                        judge_yes_incorrect += 1
                    break

        return {
            'judge_round_dist': dict(Counter(judge_rounds)),
            'retrieval_dist': dict(Counter(retrievals)),
            'avg_judge_rounds': sum(judge_rounds) / len(judge_rounds),
            'avg_retrievals': sum(retrievals) / len(retrievals),
            'single_iteration_rate': sum(1 for r in judge_rounds if r == 1) / len(judge_rounds) * 100,
            'judge_yes_correct': judge_yes_correct,
            'judge_yes_incorrect': judge_yes_incorrect,
            'judge_precision': judge_yes_correct / (judge_yes_correct + judge_yes_incorrect) * 100 if (judge_yes_correct + judge_yes_incorrect) > 0 else 0
        }

    def analyze_errors(self):
        """Categorize and analyze errors."""
        errors = {
            'early_termination': [],
            'retrieval_failure': [],
            'reasoning_error': [],
            'other': []
        }

        for item in self.data:
            f1 = item.get('metric_score', {}).get('f1', 0)
            if f1 >= 0.8:
                continue  # Skip correct cases

            iterations = item.get('iterations', [])
            judge_rounds = len([i for i in iterations if i.get('phase') == 'Judge'])
            retrievals = item.get('total_retrievals', 0)

            # Get last judge result
            last_judge = None
            for it in reversed(iterations):
                if it.get('phase') == 'Judge':
                    last_judge = it.get('judge_result')
                    break

            case = {
                'question': item.get('question', '')[:100],
                'f1': f1,
                'final_answer': item.get('final_answer', '')[:80]
            }

            # Categorize error
            if last_judge == 'YES' and retrievals <= 1:
                errors['early_termination'].append(case)
            elif retrievals == 0 or (retrievals == 1 and f1 < 0.1):
                errors['retrieval_failure'].append(case)
            elif retrievals >= 2:
                errors['reasoning_error'].append(case)
            else:
                errors['other'].append(case)

        return errors

    def analyze_retrieval_quality(self):
        """Analyze retrieval cache quality."""
        all_scores = []
        for results in self.cache.values():
            for r in results:
                all_scores.append(r.get('score', 0))

        return {
            'total_queries': len(self.cache),
            'total_retrievals': len(all_scores),
            'avg_score': sum(all_scores) / len(all_scores) if all_scores else 0,
            'high_score_ratio': sum(1 for s in all_scores if s > 0.9) / len(all_scores) * 100 if all_scores else 0,
            'low_score_ratio': sum(1 for s in all_scores if s < 0.8) / len(all_scores) * 100 if all_scores else 0
        }

    def generate_report(self) -> str:
        """Generate Markdown report."""
        core = self.analyze_core_metrics()
        by_type = self.analyze_by_type()
        iterations = self.analyze_iterations()
        errors = self.analyze_errors()
        retrieval = self.analyze_retrieval_quality()

        lines = [
            f"# Experiment Analysis Report",
            f"",
            f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Experiment**: {self.exp_dir.name}",
            f"",
            f"---",
            f"",
            f"## 1. Executive Summary",
            f"",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Questions | {core['total']} |",
            f"| Average F1 | {core['f1_mean']:.4f} |",
            f"| Average Acc | {core['acc_mean']:.4f} |",
            f"| Perfect F1 (≥0.8) | {core['perfect_f1']} ({core['perfect_f1']/core['total']*100:.1f}%) |",
            f"| Perfect Acc | {core['perfect_acc']} ({core['perfect_acc']/core['total']*100:.1f}%) |",
            f"| Zero F1 | {core['zero_f1']} ({core['zero_f1']/core['total']*100:.1f}%) |",
            f"",
            f"---",
            f"",
            f"## 2. Performance by Question Type",
            f"",
            f"| Type | Count | Avg F1 | Avg Acc | Perfect Rate |",
            f"|------|-------|--------|---------|--------------|",
        ]

        for qtype in ['compositional', 'bridge_comparison', 'comparison', 'inference']:
            if qtype in by_type:
                stats = by_type[qtype]
                lines.append(f"| {qtype} | {stats['count']} | {stats['f1_mean']:.4f} | {stats['acc_mean']:.4f} | {stats['perfect_rate']:.1f}% |")

        lines.extend([
            f"",
            f"---",
            f"",
            f"## 3. Iteration Behavior Analysis",
            f"",
            f"### 3.1 Judge Rounds Distribution",
            f"",
            f"| Judge Rounds | Count | Percentage |",
            f"|--------------|-------|------------|",
        ])

        for rounds in sorted(iterations['judge_round_dist'].keys()):
            count = iterations['judge_round_dist'][rounds]
            pct = count / core['total'] * 100
            lines.append(f"| {rounds} | {count} | {pct:.1f}% |")

        lines.extend([
            f"",
            f"- **Average Judge Rounds**: {iterations['avg_judge_rounds']:.2f}",
            f"- **Single Iteration Rate**: {iterations['single_iteration_rate']:.1f}%",
            f"",
            f"### 3.2 Retrieval Count Distribution",
            f"",
            f"| Retrievals | Count | Percentage |",
            f"|-------------|-------|------------|",
        ])

        for ret in sorted(iterations['retrieval_dist'].keys()):
            count = iterations['retrieval_dist'][ret]
            pct = count / core['total'] * 100
            lines.append(f"| {ret} | {count} | {pct:.1f}% |")

        lines.extend([
            f"",
            f"- **Average Retrievals**: {iterations['avg_retrievals']:.2f}",
            f"",
            f"### 3.3 Judge Confidence Analysis",
            f"",
            f"- Judge YES + Correct: {iterations['judge_yes_correct']}",
            f"- Judge YES + Incorrect: {iterations['judge_yes_incorrect']}",
            f"- **Judge Precision**: {iterations['judge_precision']:.1f}%",
            f"",
            f"---",
            f"",
            f"## 4. Retrieval Quality",
            f"",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Queries | {retrieval['total_queries']} |",
            f"| Total Retrievals | {retrieval['total_retrievals']} |",
            f"| Average Score | {retrieval['avg_score']:.4f} |",
            f"| High Score (>0.9) | {retrieval['high_score_ratio']:.1f}% |",
            f"| Low Score (<0.8) | {retrieval['low_score_ratio']:.1f}% |",
            f"",
            f"---",
            f"",
            f"## 5. Error Analysis",
            f"",
            f"### 5.1 Error Distribution",
            f"",
            f"| Error Type | Count | Percentage |",
            f"|------------|-------|------------|",
            f"| Early Termination | {len(errors['early_termination'])} | {len(errors['early_termination'])/core['total']*100:.1f}% |",
            f"| Retrieval Failure | {len(errors['retrieval_failure'])} | {len(errors['retrieval_failure'])/core['total']*100:.1f}% |",
            f"| Reasoning Error | {len(errors['reasoning_error'])} | {len(errors['reasoning_error'])/core['total']*100:.1f}% |",
            f"| Other | {len(errors['other'])} | {len(errors['other'])/core['total']*100:.1f}% |",
            f"",
            f"### 5.2 Early Termination Examples",
            f"",
        ])

        for i, case in enumerate(errors['early_termination'][:5]):
            lines.append(f"**[{i+1}]** Q: {case['question']}...")
            lines.append(f"    F1: {case['f1']:.3f} | Answer: {case['final_answer']}")
            lines.append("")

        lines.extend([
            f"### 5.3 Reasoning Error Examples",
            f"",
        ])

        for i, case in enumerate(errors['reasoning_error'][:5]):
            lines.append(f"**[{i+1}]** Q: {case['question']}...")
            lines.append(f"    F1: {case['f1']:.3f} | Answer: {case['final_answer']}")
            lines.append("")

        # Error examples section - show more examples
        lines.extend([
            f"",
            f"## 6. Error Case Details",
            f"",
        ])

        # Early termination cases
        if errors['early_termination']:
            lines.append(f"### 6.1 Early Termination Cases ({len(errors['early_termination'])} total)")
            lines.append("")
            for i, case in enumerate(errors['early_termination'][:10]):
                lines.append(f"**[{i+1}]** F1: {case['f1']:.3f}")
                lines.append(f"    Q: {case['question']}")
                lines.append(f"    A: {case['final_answer']}")
                lines.append("")
            if len(errors['early_termination']) > 10:
                lines.append(f"... and {len(errors['early_termination']) - 10} more")
                lines.append("")

        # Reasoning error cases
        if errors['reasoning_error']:
            lines.append(f"### 6.2 Reasoning Error Cases ({len(errors['reasoning_error'])} total)")
            lines.append("")
            for i, case in enumerate(errors['reasoning_error'][:10]):
                lines.append(f"**[{i+1}]** F1: {case['f1']:.3f}")
                lines.append(f"    Q: {case['question']}")
                lines.append(f"    A: {case['final_answer']}")
                lines.append("")
            if len(errors['reasoning_error']) > 10:
                lines.append(f"... and {len(errors['reasoning_error']) - 10} more")
                lines.append("")

        lines.extend([
            f"",
            f"---",
            f"",
            f"*Report generated by Experiment Analyzer Skill*",
        ])

        return '\n'.join(lines)

    def save_report(self, output_path: Path = None):
        """Save report to file."""
        if output_path is None:
            output_path = self.exp_dir / "analysis_report.md"

        report_content = self.generate_report()
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_content)

        return output_path


def main():
    if len(sys.argv) < 2:
        print("Usage: analyze_experiment.py <experiment_directory>")
        sys.exit(1)

    exp_dir = sys.argv[1]
    analyzer = ExperimentAnalyzer(exp_dir)
    analyzer.load_data()

    if not analyzer.data:
        print("Error: No data found in experiment directory")
        sys.exit(1)

    output_path = analyzer.save_report()
    print(f"Report saved to: {output_path}")


if __name__ == "__main__":
    main()

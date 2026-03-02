"""
单问题 Case Study 脚本
用于测试单个问题的推理过程，详细输出每一步的信息

使用方法:
    python case_study.py --question "你的问题"
    python case_study.py --question "你的问题" --gpu_id 0
    python case_study.py -q "你的问题" --interactive  # 交互模式

示例:
    python case_study.py --question "Who is the director of the film that starred the actress who was born in 1990?"
"""
import os
import sys
import argparse
import json
from typing import Dict

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 添加 planRAG 目录到路径（run_llama3 的上一级）
planrag_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, planrag_dir)

from flashrag.config import Config
from planrag_pipeline import PlanRAGPipeline


class CaseStudyRunner:
    """Case Study 运行器，用于测试单个问题的推理过程"""

    def __init__(self, gpu_id: str = "0", verbose: bool = True):
        """
        初始化 Case Study 运行器

        Args:
            gpu_id: GPU ID
            verbose: 是否详细输出
        """
        self.verbose = verbose
        self.gpu_id = gpu_id
        self.pipeline = None
        self.config = None

    def _print_section(self, title: str, content: str = "", char: str = "="):
        """打印格式化的分节"""
        if self.verbose:
            print(f"\n{char * 60}")
            print(f"  {title}")
            print(f"{char * 60}")
            if content:
                print(content)

    def _print_step(self, step: str, content: str = ""):
        """打印步骤信息"""
        if self.verbose:
            print(f"\n>>> {step}")
            if content:
                print(f"    {content}")

    def initialize(self):
        """初始化配置和 Pipeline"""
        self._print_section("初始化 Case Study 环境")

        # 配置参数覆盖
        config_dict = {
            "split": ["dev"],
            "gpu_id": self.gpu_id,
            "save_note": "case_study",
            "save_intermediate_data": False,  # case study 不需要保存中间数据
        }

        # 加载配置
        config_file_path = os.path.join(os.path.dirname(__file__), "planrag_hf_config.yaml")
        self.config = Config(config_file_path=config_file_path, config_dict=config_dict)

        # 修正路径为绝对路径
        planrag_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        path_configs = [
            ('data_dir', '数据集目录'),
            ('index_path', '索引路径'),
            ('corpus_path', '语料库路径'),
            ('retrieval_model_path', '检索模型路径'),
            ('generator_model_path', '生成器模型路径'),
            ('save_dir', '输出目录'),
        ]

        for key, desc in path_configs:
            if key in self.config and not os.path.isabs(self.config[key]):
                self.config[key] = os.path.normpath(os.path.join(planrag_root, self.config[key]))
                self._print_step(desc, self.config[key])

        if 'dataset_path' in self.config:
            self.config['dataset_path'] = os.path.join(self.config['data_dir'], self.config['dataset_name'])

        self._print_step("生成器框架", self.config['framework'])
        self._print_step("生成器模型", self.config['generator_model'])
        self._print_step("最大迭代次数", str(self.config['planrag_config'].get('max_iter', 5)))

        # 初始化 Pipeline
        print("\n正在初始化 planRAG Pipeline...")
        self.pipeline = PlanRAGPipeline(self.config)
        print("Pipeline 初始化完成！")

    def run_single_question(self, question: str) -> Dict:
        """
        运行单个问题的推理过程，并详细输出每一步

        Args:
            question: 要测试的问题

        Returns:
            包含推理结果的字典
        """
        if self.pipeline is None:
            self.initialize()

        self._print_section("开始 Case Study", f"问题: {question}")

        # ==================== Step 1: Planner ====================
        self._print_section("Step 1: Planner - 生成全局规划", char="-")
        plan = self.pipeline._planner_generate_plan(question)
        print(f"\n生成的规划 (Plan):\n{plan}")

        memory = ""
        iterations = []
        retrieval_log = []  # 单独记录所有检索
        total_retrievals = 0
        final_answer = None
        initial_plan = plan  # 保存初始规划

        # ==================== Step 2: ReSP Iteration Loop ====================
        self._print_section("Step 2: ReSP 迭代循环", char="-")

        max_iter = self.config['planrag_config'].get('max_iter', 5)
        for iter_idx in range(max_iter):
            print(f"\n{'='*40}")
            print(f"  迭代 {iter_idx + 1}/{max_iter}")
            print(f"{'='*40}")

            # 2.a. Reasoner - Judge
            print("\n[2.a] Reasoner - Judge (判断记忆是否充足)")
            if iter_idx == 0:
                judge_result = "No"
                print(f"     (第一轮跳过 Judge，强制进入信息收集)")
            else:
                judge_result = self.pipeline._reasoner_judge(question, plan, memory)
                print(f"     Judge 结果: {judge_result}")

            if judge_result.upper() == "YES":
                print("     记忆充足，准备生成最终答案...")
                final_answer = self.pipeline._generator_final_answer(question, memory)
                iterations.append({
                    'iteration': iter_idx + 1,
                    'phase': 'Judge',
                    'judge_result': 'YES',
                    'final_answer': final_answer
                })
                break

            # 2.b. Reasoner - Thought
            print("\n[2.b] Reasoner - Thought (生成检索子问题)")
            if iter_idx == 0:
                sub_question = question
                print(f"     (第一轮使用原始问题作为子问题)")
            else:
                sub_question = self.pipeline._reasoner_thought(question, memory)
            print(f"     子问题: {sub_question}")

            # 2.c. Retriever
            print("\n[2.c] Retriever (检索相关文档)")
            retrieval_topk = self.config['planrag_config'].get('retrieval_topk', 3)
            retrieved_docs = self.pipeline.retriever.batch_search([sub_question], num=retrieval_topk)
            total_retrievals += 1
            docs = retrieved_docs[0] if retrieved_docs and retrieved_docs[0] else []
            print(f"     检索到 {len(docs)} 个文档")

            # 保存完整的检索文档信息
            docs_full = []
            for doc in docs:
                doc_info = {
                    'contents': doc.get('contents', doc.get('text', '')),
                    'title': doc.get('title', ''),
                    'id': doc.get('id', ''),
                    'score': doc.get('score', None)
                }
                docs_full.append(doc_info)

            # 记录到检索日志
            retrieval_log.append({
                'retrieval_id': total_retrievals,
                'iteration': iter_idx + 1,
                'query': sub_question,
                'num_results': len(docs),
                'documents': docs_full
            })

            docs_text = self.pipeline._format_docs(docs)
            if self.verbose and docs:
                print(f"\n     检索到的文档摘要:")
                for i, doc in enumerate(docs[:3]):
                    content = doc.get('contents', doc.get('text', ''))[:150]
                    print(f"     [{i+1}] {content}...")

            # 2.d. Dual-Pathway Summarizer
            print("\n[2.d] Dual-Pathway Summarizer")

            # 路径 1: Global Evidence Memory
            print("\n     [路径1] Global Evidence Memory (提取全局证据)")
            global_evidence = self.pipeline._summarizer_global_evidence(question, docs_text)
            print(f"     全局证据: {global_evidence[:200]}..." if len(global_evidence) > 200 else f"     全局证据: {global_evidence}")

            # 路径 2: Local Pathway
            print("\n     [路径2] Local Pathway (尝试回答子问题)")
            local_answer = self.pipeline._summarizer_local_answer(sub_question, global_evidence, memory)
            can_answer, local_answer_text = self.pipeline._parse_local_answer(local_answer)
            print(f"     能否回答: {'是' if can_answer else '否'}")
            if can_answer:
                print(f"     局部答案: {local_answer_text}")

            # 更新记忆
            old_memory = memory
            memory = self.pipeline._update_memory(memory, global_evidence, sub_question, local_answer_text if can_answer else "")

            # 2.e. Checker - 更新 plan 状态
            print("\n[2.e] Checker (更新规划状态)")
            plan = self.pipeline._checker_update_plan(plan, sub_question, local_answer_text)
            print(f"     更新后的规划:\n{plan}")

            # 显示当前记忆状态
            print("\n[当前记忆状态]")
            print(f"{memory}")

            # 记录迭代信息
            iterations.append({
                'iteration': iter_idx + 1,
                'phase': 'ReSP',
                'judge_result': 'NO',
                'sub_question': sub_question,
                'docs_retrieved': len(docs),
                'global_evidence': global_evidence,
                'local_answer': local_answer_text,
                'can_answer': can_answer,
                'memory_before': old_memory,
                'memory_after': memory,
                'plan_before': old_plan if 'old_plan' in dir() else initial_plan,
                'plan_after': plan
            })
            old_plan = plan  # 保存当前 plan 供下次迭代使用

        # ==================== Step 3: Generator ====================
        self._print_section("Step 3: Generator - 生成最终答案", char="-")
        if final_answer is None:
            final_answer = self.pipeline._generator_final_answer(question, memory)

        print(f"\n最终答案: {final_answer}")

        # ==================== 结果汇总 ====================
        self._print_section("Case Study 结果汇总", char="=")
        print(f"原始问题: {question}")
        print(f"最终答案: {final_answer}")
        print(f"总迭代次数: {len(iterations)}")
        print(f"总检索次数: {total_retrievals}")

        result = {
            'question': question,
            'final_answer': final_answer,
            'initial_plan': initial_plan,
            'final_plan': plan,
            'final_memory': memory,
            'iterations': iterations,
            'total_retrievals': total_retrievals,
            '_retrieval_log': retrieval_log  # 内部使用，不保存到主文件
        }

        return result

    def interactive_mode(self):
        """交互模式，可以连续测试多个问题"""
        if self.pipeline is None:
            self.initialize()

        print("\n" + "=" * 60)
        print("  进入交互模式 (输入 'quit' 或 'exit' 退出)")
        print("=" * 60)

        while True:
            try:
                question = input("\n请输入问题 > ").strip()

                if not question:
                    continue

                if question.lower() in ['quit', 'exit', 'q']:
                    print("退出交互模式")
                    break

                result = self.run_single_question(question)

                # 询问是否保存结果
                save_choice = input("\n是否保存结果到文件? (y/n) > ").strip().lower()
                if save_choice == 'y':
                    self.save_result(result)

            except KeyboardInterrupt:
                print("\n\n检测到中断，退出交互模式")
                break

    def save_result(self, result: Dict, filename: str = None):
        """保存结果到文件（包括主结果和检索记录）"""
        if filename is None:
            # 使用问题的前20个字符作为文件名
            safe_question = "".join(c for c in result['question'][:20] if c.isalnum() or c in ' _-')
            base_filename = f"case_study_{safe_question.replace(' ', '_')}"
        else:
            base_filename = filename.replace('.json', '')

        output_dir = os.path.join(os.path.dirname(__file__), "case_study_outputs")
        os.makedirs(output_dir, exist_ok=True)

        # 1. 保存主结果文件（不包含 _retrieval_log）
        main_result = {k: v for k, v in result.items() if not k.startswith('_')}
        main_output_path = os.path.join(output_dir, f"{base_filename}.json")
        with open(main_output_path, 'w', encoding='utf-8') as f:
            json.dump(main_result, f, ensure_ascii=False, indent=2)
        print(f"主结果已保存到: {main_output_path}")

        # 2. 单独保存检索记录文件
        retrieval_record = {
            'question': result['question'],
            'total_retrievals': result['total_retrievals'],
            'retrieval_log': result.get('_retrieval_log', [])
        }
        retrieval_output_path = os.path.join(output_dir, f"{base_filename}_retrieval.json")
        with open(retrieval_output_path, 'w', encoding='utf-8') as f:
            json.dump(retrieval_record, f, ensure_ascii=False, indent=2)
        print(f"检索记录已保存到: {retrieval_output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="planRAG Case Study 脚本 - 测试单个问题的推理过程",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python case_study.py --question "Who directed the film starring Emma Stone?"
    python case_study.py -q "问题" --gpu_id 0
    python case_study.py --interactive  # 交互模式
        """
    )

    parser.add_argument(
        "-q", "--question",
        type=str,
        default=None,
        help="要测试的问题"
    )

    parser.add_argument(
        "--gpu_id",
        type=str,
        default="0",
        help="GPU ID (默认: 0)"
    )

    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="进入交互模式，可以连续测试多个问题"
    )

    parser.add_argument(
        "--quiet",
        action="store_true",
        help="减少输出信息"
    )

    parser.add_argument(
        "--save",
        action="store_true",
        help="自动保存结果到文件"
    )

    args = parser.parse_args()

    # 创建运行器
    runner = CaseStudyRunner(gpu_id=args.gpu_id, verbose=not args.quiet)

    if args.interactive:
        # 交互模式
        runner.interactive_mode()
    elif args.question:
        # 单问题模式
        result = runner.run_single_question(args.question)

        if args.save:
            runner.save_result(result)
    else:
        # 没有提供问题，显示帮助
        parser.print_help()
        print("\n请提供问题 (--question) 或使用交互模式 (--interactive)")


if __name__ == "__main__":
    main()

"""
planRAG Pipeline Implementation
ReSP with Planner-Guided Reasoning

核心流程：
1. Planner: 全局规划生成 plan
2. ReSP Iteration Loop:
   - Reasoner (Judge + Thought)
   - Retriever
   - Dual-Pathway Summarizer (Global Evidence + Local Answer)
   - Checker (更新 plan 状态)
3. Generator: 生成最终答案
"""
import json
import re
from typing import List, Dict, Tuple, Optional
from tqdm import tqdm
from flashrag.pipeline import BasicPipeline
from flashrag.utils import get_retriever, get_generator
from prompt_loader import PromptLoader


class PlanRAGPipeline(BasicPipeline):
    """
    planRAG Pipeline: ReSP with Planner-Guided Reasoning

    核心流程:
    1. Planner: 全局规划生成 plan
    2. ReSP Iteration Loop:
       - Reasoner (Judge + Thought)
       - Retriever
       - Dual-Pathway Summarizer (Global Evidence + Local Answer)
       - Checker (更新 plan 状态)
    3. Generator: 生成最终答案
    """

    def __init__(self, config, prompt_template=None):
        super().__init__(config, prompt_template)

        # 初始化检索器和生成器
        self.retriever = get_retriever(config)
        self.generator = get_generator(config)

        # 判断是否使用 OpenAI 框架
        self.use_openai = config['framework'] == 'openai' if 'framework' in config else False

        # planRAG 配置
        planrag_config = config['planrag_config'] if 'planrag_config' in config else {}
        self.max_iter = planrag_config.get('max_iter', 5)
        self.retrieval_topk = planrag_config.get('retrieval_topk', 3)
        self.max_sub_questions = planrag_config.get('max_sub_questions', 3)

        # 温度参数
        self.planner_temperature = planrag_config.get('planner_temperature', 0.7)
        self.reasoner_temperature = planrag_config.get('reasoner_temperature', 0.1)
        self.generator_temperature = planrag_config.get('generator_temperature', 0.5)

        # 初始化 Prompt Loader（默认使用 planRAG）
        self.prompt_loader = PromptLoader()

        # 用于记录中间数据
        self.intermediate_data = []

    def _call_generator(self, prompt: str, temperature: float = 0.7, max_tokens: int = 512) -> str:
        """
        统一的生成器调用接口

        Args:
            prompt: 完整的 prompt（包含 system 和 user）
            temperature: 温度参数
            max_tokens: 最大输出 token 数

        Returns:
            模型生成的文本
        """
        if self.use_openai:
            # OpenAI 格式：消息列表
            messages = [{"role": "user", "content": prompt}]
            response = self.generator.generate(
                [messages],
                temperature=temperature,
                max_tokens=max_tokens
            )[0]
        else:
            # 本地 HF 模型
            model_name = getattr(self.generator, 'model_name', '')

            if "llama" in model_name.lower():
                # Llama 3 系列：使用 apply_chat_template
                messages = [
                    {"role": "system", "content": ""},
                    {"role": "user", "content": prompt}
                ]
                full_prompt = self.generator.tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True
                )
                response = self.generator.generate(
                    [full_prompt],
                    temperature=temperature,
                    max_new_tokens=max_tokens,
                    stop=["<|eot_id|>"]
                )[0]
            else:
                # 其他模型
                full_prompt = f"<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n"
                response = self.generator.generate(
                    [full_prompt],
                    temperature=temperature,
                    max_new_tokens=max_tokens
                )[0]

        return response.strip()

    def run(self, dataset, do_eval=True, pred_process_fun=None):
        """对整个数据集运行 planRAG pipeline"""
        pred_answer_list = []

        for item in tqdm(dataset, desc="planRAG Processing"):
            question = item.question
            result = self._run_single_question(question)
            pred_answer_list.append(result['final_answer'])

            # 保存中间数据
            if 'save_intermediate_data' in self.config and self.config['save_intermediate_data']:
                self.intermediate_data.append({
                    'question': question,
                    'iterations': result['iterations'],
                    'final_memory': result['final_memory'],
                    'final_answer': result['final_answer'],
                    'total_retrievals': result['total_retrievals']
                })

        # 更新数据集的预测结果
        dataset.update_output("pred", pred_answer_list)

        # 保存中间数据
        if 'save_intermediate_data' in self.config and self.config['save_intermediate_data']:
            self._save_intermediate_data()

        # 评估
        dataset = self.evaluate(dataset, do_eval=do_eval, pred_process_fun=pred_process_fun)

        return dataset

    def _run_single_question(self, question: str) -> Dict:
        """
        对单个问题运行 planRAG 流程

        Returns:
            包含最终答案、记忆、迭代历史等信息的字典
        """
        # ==================== Step 1: Planner ====================
        # 生成全局规划蓝图
        plan = self._planner_generate_plan(question)
        memory = ""
        iterations = []
        total_retrievals = 0

        # ==================== Step 2: ReSP Iteration Loop ====================
        for iter_idx in range(self.max_iter):
            # 2.a. Reasoner - Judge
            judge_result = self._reasoner_judge(question, plan, memory)

            if judge_result.upper() == "YES":
                # 记忆充足，生成最终答案
                final_answer = self._generator_final_answer(question, memory)
                iterations.append({
                    'iteration': iter_idx + 1,
                    'phase': 'Judge',
                    'judge_result': 'YES',
                    'final_answer': final_answer
                })
                break

            # 2.b. Reasoner - Thought
            # 第一轮迭代时，sub_question = question
            if iter_idx == 0:
                sub_question = question
            else:
                sub_question = self._reasoner_thought(question, memory)

            # 2.c. Retriever
            retrieved_docs = self.retriever.batch_search([sub_question], num=self.retrieval_topk)
            total_retrievals += 1
            docs = retrieved_docs[0] if retrieved_docs and retrieved_docs[0] else []

            docs_text = self._format_docs(docs)

            # 2.d. Dual-Pathway Summarizer
            # 路径 1: Global Evidence Memory
            global_evidence = self._summarizer_global_evidence(question, docs_text)

            # 路径 2: Local Pathway
            local_answer = self._summarizer_local_answer(sub_question, memory, docs_text)
            # 解析 local_answer，提取 Yes/No 和答案
            can_answer, local_answer_text = self._parse_local_answer(local_answer)

            # 更新记忆
            old_memory = memory
            if can_answer:
                memory = self._update_memory(memory, global_evidence, local_answer_text)
            else:
                memory = self._update_memory(memory, global_evidence, "")

            # 2.e. Checker - 更新 plan 状态
            plan = self._checker_update_plan(plan, sub_question, local_answer_text)

            # 记录迭代信息
            iterations.append({
                'iteration': iter_idx + 1,
                'phase': 'ReSP',
                'judge_result': 'NO',
                'sub_question': sub_question,
                'docs_retrieved': len(docs),
                'global_evidence': global_evidence[:100] + "..." if len(global_evidence) > 100 else global_evidence,
                'local_answer': local_answer_text,
                'plan_updated': plan,
                'memory_updated': memory != old_memory
            })

        # ==================== Step 3: Generator ====================
        if judge_result.upper() != "YES":
            final_answer = self._generator_final_answer(question, memory)

        return {
            'final_answer': final_answer,
            'final_memory': memory,
            'plan': plan,
            'iterations': iterations,
            'total_retrievals': total_retrievals
        }

    # ==================== Planner Module ====================

    def _planner_generate_plan(self, question: str) -> str:
        """
        Planner: 生成全局规划蓝图

        Args:
            question: 原始问题

        Returns:
            规划蓝图文本
        """
        prompt = self.prompt_loader.get_planner_prompt(question)

        response = self._call_generator(
            prompt=prompt,
            temperature=self.planner_temperature,
            max_tokens=256
        )

        return response.strip()

    # ==================== Reasoner Module ====================

    def _reasoner_judge(self, question: str, plan: str, memory: str) -> str:
        """
        Reasoner Judge: 判断当前记忆是否足以回答问题

        Args:
            question: 原始问题
            plan: 全局规划
            memory: 当前记忆

        Returns:
            "Yes" 或 "No"
        """
        prompt = self.prompt_loader.get_reasoner_judge_prompt(question, plan, memory)

        response = self._call_generator(
            prompt=prompt,
            temperature=self.reasoner_temperature,
            max_tokens=10
        )

        response = response.strip().upper()
        if "YES" in response:
            return "Yes"
        return "No"

    def _reasoner_thought(self, question: str, memory: str) -> str:
        """
        Reasoner Thought: 生成下一个检索意图

        Args:
            question: 原始问题
            memory: 当前记忆

        Returns:
            下一个检索子问题
        """
        prompt = self.prompt_loader.get_reasoner_thought_prompt(question, memory)

        response = self._call_generator(
            prompt=prompt,
            temperature=self.reasoner_temperature,
            max_tokens=128
        )

        return response.strip()

    # ==================== Retriever ====================

    def _format_docs(self, docs: List[Dict]) -> str:
        """格式化检索到的文档"""
        if not docs:
            return "No relevant documents found."

        docs_text = ""
        for i, doc in enumerate(docs[:3]):
            contents = doc.get('contents', doc.get('text', ''))
            docs_text += f"Document {i+1}: {contents}\n\n"

        return docs_text.strip()

    # ==================== Summarizer Module ====================

    def _summarizer_global_evidence(self, question: str, docs: str) -> str:
        """
        Global Evidence Memory: 提取文档中支持回答原始问题的证据

        Args:
            question: 原始问题
            docs: 检索到的文档文本

        Returns:
            全局证据文本
        """
        prompt = self.prompt_loader.get_summarizer_global_evidence_prompt(question, docs)

        response = self._call_generator(
            prompt=prompt,
            temperature=0.3,
            max_tokens=256
        )

        # 提取 [DONE] 之前的部分
        if "[DONE]" in response:
            response = response.split("[DONE]")[0].strip()

        return response.strip()

    def _summarizer_local_answer(self, sub_question: str, memory: str, docs: str) -> str:
        """
        Local Pathway: 直接回答子问题

        Args:
            sub_question: 子问题
            memory: 当前记忆（作为背景）
            docs: 检索到的文档

        Returns:
            包含 Yes/No 和答案的响应
        """
        prompt = self.prompt_loader.get_summarizer_local_answer_prompt(sub_question, memory, docs)

        response = self._call_generator(
            prompt=prompt,
            temperature=0.1,
            max_tokens=128
        )

        return response.strip()

    def _parse_local_answer(self, response: str) -> Tuple[bool, str]:
        """
        解析 Local Pathway 的响应

        Returns:
            (can_answer: bool, answer_text: str)
        """
        response = response.strip()

        if response.upper().startswith("YES"):
            # 提取 "Yes" 之后的答案
            answer = response[3:].strip()
            return True, answer
        else:
            return False, ""

    def _update_memory(self, memory: str, global_evidence: str, local_answer: str) -> str:
        """
        更新记忆：累积 global_evidence 和 local_answer

        Args:
            memory: 已有记忆
            global_evidence: 全局证据
            local_answer: 局部答案

        Returns:
            更新后的记忆
        """
        new_parts = []

        if global_evidence:
            new_parts.append(f"[Global Evidence]: {global_evidence}")

        if local_answer:
            new_parts.append(f"[Local Answer]: {local_answer}")

        if not new_parts:
            return memory

        new_content = "\n".join(new_parts)

        if memory.strip():
            return f"{memory}\n{new_content}"
        else:
            return new_content

    # ==================== Checker Module ====================

    def _checker_update_plan(self, plan: str, sub_question: str, local_answer: str) -> str:
        """
        Checker: 根据 local_answer 更新 plan 状态

        Args:
            plan: 当前 plan
            sub_question: 刚回答的子问题
            local_answer: 子问题的答案

        Returns:
            更新后的 plan
        """
        prompt = self.prompt_loader.get_checker_prompt(plan, sub_question, local_answer)

        response = self._call_generator(
            prompt=prompt,
            temperature=0.1,
            max_tokens=256
        )

        return response.strip()

    # ==================== Generator Module ====================

    def _generator_final_answer(self, question: str, memory: str) -> str:
        """
        Generator: 基于记忆生成最终答案

        Args:
            question: 原始问题
            memory: 累积的记忆

        Returns:
            最终答案
        """
        prompt = self.prompt_loader.get_generator_prompt(question, memory)

        response = self._call_generator(
            prompt=prompt,
            temperature=self.generator_temperature,
            max_tokens=128
        )

        # 清理输出
        answer = response.strip()
        answer = re.sub(r'^Answer:\s*', '', answer)
        answer = re.sub(r'^["\']|["\']$', '', answer)

        return answer

    # ==================== Utility Methods ====================

    def _save_intermediate_data(self):
        """保存中间数据到文件"""
        import os
        save_dir = self.config['save_dir'] if 'save_dir' in self.config else 'output'
        os.makedirs(save_dir, exist_ok=True)

        output_path = os.path.join(save_dir, 'intermediate_data.jsonl')
        with open(output_path, 'w', encoding='utf-8') as f:
            for item in self.intermediate_data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')

        print(f"Intermediate data saved to: {output_path}")

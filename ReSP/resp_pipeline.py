"""
ReSP Pipeline Implementation
Reasoning with Summary and Planning

核心流程（根据 ReSP.md Algorithm 1）：
1. 初始检索：使用原始 query Q 检索 K 个文档
2. Summarizer：
   - Global Evidence: 生成与原始问题相关的证据摘要 -> global evidence memory
   - Local Pathway: 响应当前子问题 -> local pathway memory（第一轮无）
3. Reasoner Judge：判断当前信息是否足以回答问题
4. 如果充足：Generator 生成最终答案
5. 如果不充足：Reasoner Plan 生成下一个子问题 Q*，进入下一轮迭代
"""
import json
import re
from typing import List, Dict, Tuple, Optional
from tqdm import tqdm
from flashrag.pipeline import BasicPipeline
from flashrag.utils import get_retriever, get_generator
from prompt_loader import PromptLoader


class ReSPPipeline(BasicPipeline):
    """
    ReSP Pipeline: Reasoning with Summary and Planning

    核心组件:
    - Reasoner: Judge（判断信息是否充足）+ Plan（生成下一个子问题）
    - Retriever: 检索相关文档
    - Dual-Function Summarizer:
        - Global Evidence Memory: 与原始问题相关的证据
        - Local Pathway Memory: 子问题 + 答案对
    - Generator: 生成最终答案
    """

    def __init__(self, config, prompt_template=None):
        super().__init__(config, prompt_template)

        # 初始化检索器和生成器
        self.retriever = get_retriever(config)
        self.generator = get_generator(config)

        # 判断是否使用 OpenAI 框架
        self.use_openai = config['framework'] == 'openai' if 'framework' in config else False

        # ReSP 配置
        resp_config = config['resp_config'] if 'resp_config' in config else {}
        self.max_iter = resp_config.get('max_iter', 5)
        self.retrieval_topk = resp_config.get('retrieval_topk', 3)

        # 温度参数
        self.reasoner_temperature = resp_config.get('reasoner_temperature', 0.1)
        self.generator_temperature = resp_config.get('generator_temperature', 0.5)

        # 初始化 Prompt Loader
        self.prompt_loader = PromptLoader()

        # 用于记录中间数据
        self.intermediate_data = []

    def _call_generator(self, prompt: str, temperature: float = 0.7, max_tokens: int = 512) -> str:
        """
        统一的生成器调用接口

        Args:
            prompt: 完整的 prompt
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
        """对整个数据集运行 ReSP pipeline"""
        pred_answer_list = []

        for item in tqdm(dataset, desc="ReSP Processing", position=0, leave=True):
            question = item.question
            result = self._run_single_question(question)
            pred_answer_list.append(result['final_answer'])

            # 保存中间数据
            if 'save_intermediate_data' in self.config and self.config['save_intermediate_data']:
                self.intermediate_data.append({
                    'question': question,
                    'iterations': result['iterations'],
                    'global_evidence_memory': result['global_evidence_memory'],
                    'local_pathway_memory': result['local_pathway_memory'],
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
        对单个问题运行 ReSP 流程

        Returns:
            包含最终答案、记忆、迭代历史等信息的字典
        """
        # 初始化两个记忆队列
        global_evidence_memory = []  # 存储 global evidence 摘要
        local_pathway_memory = []    # 存储 (sub_question, answer) 对

        iterations = []
        total_retrievals = 0
        final_answer = ""

        # ==================== ReSP Iteration Loop ====================
        for iter_idx in range(self.max_iter):
            # 确定当前检索 query
            if iter_idx == 0:
                # 第一轮：使用原始问题
                current_query = question
            else:
                # 后续轮：使用 Reasoner Plan 生成的子问题
                current_query = sub_question

            # Step 1: Retriever - 检索文档
            retrieved_docs = self.retriever.batch_search([current_query], num=self.retrieval_topk)
            total_retrievals += 1
            docs = retrieved_docs[0] if retrieved_docs and retrieved_docs[0] else []
            docs_text = self._format_docs(docs)

            # Step 2: Dual-Function Summarizer
            # 2.a. Global Evidence - 提取与原始问题相关的证据
            global_evidence = self._summarizer_global_evidence(question, docs_text)
            global_evidence_memory.append(global_evidence)

            # 2.b. Local Pathway - 回答当前子问题
            # 注意：第一轮迭代时子问题就是原始问题，根据论文不生成 local pathway 响应
            if iter_idx > 0:
                combined_memory = self._combine_memory(global_evidence_memory, local_pathway_memory)
                local_response = self._summarizer_local_pathway(current_query, combined_memory)
                can_answer, local_answer = self._parse_local_response(local_response)
                if can_answer:
                    local_pathway_memory.append((current_query, local_answer))
                else:
                    local_pathway_memory.append((current_query, "No"))

            # Step 3: Reasoner Judge - 判断信息是否充足
            combined_memory = self._combine_memory(global_evidence_memory, local_pathway_memory)
            judge_result = self._reasoner_judge(question, combined_memory)

            # 记录迭代信息
            iteration_info = {
                'iteration': iter_idx + 1,
                'current_query': current_query,
                'docs_retrieved': len(docs),
                'global_evidence': global_evidence[:200] + "..." if len(global_evidence) > 200 else global_evidence,
                'judge_result': judge_result
            }

            if judge_result.upper() == "YES":
                # 信息充足，生成最终答案
                final_answer = self._generator_final_answer(question, combined_memory)
                iteration_info['final_answer'] = final_answer
                iterations.append(iteration_info)
                break

            # Step 4: Reasoner Plan - 生成下一个子问题
            sub_question = self._reasoner_plan(question, combined_memory)
            iteration_info['next_sub_question'] = sub_question
            iterations.append(iteration_info)

        # 如果达到最大迭代次数仍未找到答案，强制生成
        if not final_answer:
            combined_memory = self._combine_memory(global_evidence_memory, local_pathway_memory)
            final_answer = self._generator_final_answer(question, combined_memory)

        return {
            'final_answer': final_answer,
            'global_evidence_memory': global_evidence_memory,
            'local_pathway_memory': local_pathway_memory,
            'iterations': iterations,
            'total_retrievals': total_retrievals
        }

    # ==================== Reasoner Module ====================

    def _reasoner_judge(self, question: str, memory: str) -> str:
        """
        Reasoner Judge: 判断当前记忆是否足以回答问题

        Args:
            question: 原始问题
            memory: 当前组合记忆（global + local）

        Returns:
            "Yes" 或 "No"
        """
        prompt = self.prompt_loader.get_reasoner_judge_prompt(question, memory)

        response = self._call_generator(
            prompt=prompt,
            temperature=self.reasoner_temperature,
            max_tokens=10
        )

        response = response.strip().upper()
        if "YES" in response:
            return "Yes"
        return "No"

    def _reasoner_plan(self, question: str, memory: str) -> str:
        """
        Reasoner Plan: 生成下一个检索的子问题（thought）

        Args:
            question: 原始问题
            memory: 当前组合记忆

        Returns:
            下一个子问题
        """
        prompt = self.prompt_loader.get_reasoner_plan_prompt(question, memory)

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
        for i, doc in enumerate(docs[:self.retrieval_topk]):
            contents = doc.get('contents', doc.get('text', ''))
            docs_text += f"Document {i+1}: {contents}\n\n"

        return docs_text.strip()

    # ==================== Dual-Function Summarizer ====================

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

    def _summarizer_local_pathway(self, sub_question: str, memory: str) -> str:
        """
        Local Pathway: 判断是否能回答子问题，如果能则给出答案

        Args:
            sub_question: 子问题
            memory: 当前组合记忆

        Returns:
            包含 Yes/No 和答案的响应
        """
        prompt = self.prompt_loader.get_summarizer_local_pathway_prompt(sub_question, memory)

        response = self._call_generator(
            prompt=prompt,
            temperature=0.1,
            max_tokens=128
        )

        return response.strip()

    def _parse_local_response(self, response: str) -> Tuple[bool, str]:
        """
        解析 Local Pathway 的响应

        Returns:
            (can_answer: bool, answer_text: str)
        """
        response = response.strip()

        if response.upper().startswith("YES"):
            # 提取 "Yes" 之后的答案
            # 处理 "Yes," 或 "Yes:" 或 "Yes " 等情况
            answer = re.sub(r'^YES[,:\s]*', '', response, flags=re.IGNORECASE).strip()
            return True, answer
        else:
            return False, ""

    def _combine_memory(self, global_evidence_memory: List[str], local_pathway_memory: List[Tuple[str, str]]) -> str:
        """
        组合两个记忆队列为统一的上下文

        Args:
            global_evidence_memory: 全局证据列表
            local_pathway_memory: (子问题, 答案) 对列表

        Returns:
            组合后的记忆文本
        """
        parts = []

        # Global Evidence Memory
        if global_evidence_memory:
            evidence_text = "\n".join([f"[Evidence {i+1}]: {ev}" for i, ev in enumerate(global_evidence_memory)])
            parts.append(f"=== Global Evidence Memory ===\n{evidence_text}")

        # Local Pathway Memory
        if local_pathway_memory:
            pathway_text = "\n".join([f"Q: {q}\nA: {a}" for q, a in local_pathway_memory])
            parts.append(f"=== Local Pathway Memory ===\n{pathway_text}")

        if not parts:
            return "No information available."

        return "\n\n".join(parts)

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
        answer = re.sub(r'^Answer:\s*', '', answer, flags=re.IGNORECASE)
        answer = re.sub(r'^["\']|["\']$', '', answer)

        return answer

    # ==================== Utility Methods ====================

    def _save_intermediate_data(self):
        """保存中间数据到文件"""
        import os
        save_dir = self.config['save_dir'] if 'save_dir' in self.config else 'output'
        os.makedirs(save_dir, exist_ok=True)

        output_path = os.path.join(save_dir, 'intermediate_data.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.intermediate_data, f, ensure_ascii=False, indent=2)

        print(f"Intermediate data saved to: {output_path}")

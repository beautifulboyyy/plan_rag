"""
Prompt Loader Module
用于从文件加载RPVM pipeline使用的各类prompts

重构后的设计：
- 支持两种prompt风格：openai（原版）和GPT35（重构版）
- GPT35版本将Planner拆分为Judge+Plan两次LLM调用
- Memory模块统一处理supported和contradicted两种情况
"""
import os
from typing import Dict, Tuple, Optional


class PromptLoader:
    """从prompts目录加载所有prompt模板"""

    def __init__(self, prompts_dir: str = None):
        """
        初始化PromptLoader

        Args:
            prompts_dir: prompt文件目录路径。
                        如果指定了model_name参数，则使用 prompts/{model_name} 目录。
                        如果直接指定prompts_dir，则使用该目录。
        """
        current_dir = os.path.dirname(os.path.abspath(__file__))
        prompts_base_dir = os.path.join(current_dir, 'prompts')

        if prompts_dir is None:
            # 默认使用GPT35的prompts（重构版）
            self.prompts_dir = os.path.join(prompts_base_dir, 'GPT35')
            self.prompt_style = 'GPT35'
        elif os.path.isabs(prompts_dir):
            # 绝对路径
            self.prompts_dir = prompts_dir
            self.prompt_style = 'GPT35' if 'GPT35' in prompts_dir else 'openai'
        else:
            # 相对路径，相对于prompts目录
            self.prompts_dir = os.path.join(prompts_base_dir, prompts_dir)
            # 如果目录名是 GPT35 或 openai，使用该风格；否则使用 GPT35 风格（重构版）
            if prompts_dir in ('GPT35', 'openai'):
                self.prompt_style = prompts_dir
            else:
                # 自定义风格目录（如 llama3），使用 GPT35 文件结构
                self.prompt_style = 'GPT35'

        self._prompts = {}
        self._load_all_prompts()

    def _load_all_prompts(self):
        """加载所有prompt文件"""
        if self.prompt_style == 'GPT35':
            prompt_files = {
                # Planner - Judge (Step 1)
                'planner_judge_system': 'planner_judge_system.md',
                'planner_judge_user': 'planner_judge_user.md',
                # Planner - Plan (Step 2) - First iteration
                'planner_plan_system': 'planner_plan_system.md',
                'planner_plan_first_user': 'planner_plan_first_user.md',
                # Planner - Plan (Step 2) - Subsequent iterations
                'planner_plan_next_user': 'planner_plan_next_user.md',
                # Verifier - Query Rewrite
                'verifier_query_system': 'verifier_query_system.md',
                'verifier_query_user': 'verifier_query_user.md',
                # Verifier - Verify
                'verifier_system': 'verifier_system.md',
                'verifier_user': 'verifier_user.md',
                # Memory - Unified (supports both supported and contradicted)
                'memory_system': 'memory_system.md',
                'memory_user_supported': 'memory_user_supported.md',
                'memory_user_contradicted': 'memory_user_contradicted.md',
                # Generate - Final Answer
                'generate_system': 'generate_system.md',
                'generate_user': 'generate_user.md',
            }
        else:
            # OpenAI style (legacy)
            prompt_files = {
                'planner_system': 'planner_system.md',
                'planner_few_shot_examples': 'planner_few_shot_examples.md',
                'planner_user_with_memory': 'planner_user_with_memory.md',
                'planner_user_without_memory': 'planner_user_without_memory.md',
                'verifier_system': 'verifier_system.md',
                'verifier_user': 'verifier_user.md',
                'verifier_query_system': 'verifier_query_system.md',
                'verifier_query_user': 'verifier_query_user.md',
                'memory_summarizer_system': 'memory_summarizer_system.md',
                'memory_summarizer_user': 'memory_summarizer_user.md',
                'final_answer_system': 'final_answer_system.md',
                'final_answer_user': 'final_answer_user.md',
                'best_effort_answer_system': 'best_effort_answer_system.md',
                'best_effort_answer_user_no_memory': 'best_effort_answer_user_no_memory.md',
                'best_effort_answer_user_with_memory': 'best_effort_answer_user_with_memory.md',
            }

        for key, filename in prompt_files.items():
            filepath = os.path.join(self.prompts_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    self._prompts[key] = f.read()
            except FileNotFoundError:
                raise FileNotFoundError(f"Prompt file not found: {filepath}")

    def get(self, prompt_name: str, **kwargs) -> str:
        """
        获取prompt并进行格式化

        Args:
            prompt_name: prompt名称
            **kwargs: 用于格式化prompt的参数

        Returns:
            格式化后的prompt字符串
        """
        if prompt_name not in self._prompts:
            raise KeyError(f"Prompt '{prompt_name}' not found. Available prompts: {list(self._prompts.keys())}")

        prompt = self._prompts[prompt_name]

        if kwargs:
            return prompt.format(**kwargs)
        else:
            return prompt

    # ==================== Planner - Judge ====================

    def get_planner_judge_prompt(self, question: str, memory: str) -> tuple:
        """
        获取Planner Judge的system和user prompt
        Step 1: 判断当前记忆是否足以回答问题

        Returns:
            (system_prompt, user_prompt)
        """
        system_prompt = self.get('planner_judge_system')
        user_prompt = self.get('planner_judge_user', question=question, memory=memory)
        return system_prompt, user_prompt

    # ==================== Planner - Plan ====================

    def get_planner_plan_prompt(self, question: str, memory: str, is_first_iteration: bool = True) -> tuple:
        """
        获取Planner Plan的system和user prompt
        Step 2: 生成下一步需要查询的子问题（仅在Judge=NO时调用）

        Args:
            question: 原始问题
            memory: 当前记忆
            is_first_iteration: 是否是首次迭代（首次生成多个plan，后续生成单个plan）

        Returns:
            (system_prompt, user_prompt)
        """
        if is_first_iteration:
            return self.get_planner_plan_prompt_first(question, memory)
        else:
            return self.get_planner_plan_prompt_next(question, memory)

    def get_planner_plan_prompt_first(self, question: str, memory: str) -> tuple:
        """
        获取Planner Plan的system和user prompt（首次迭代）
        生成覆盖问题所有方面的多个plans

        Returns:
            (system_prompt, user_prompt)
        """
        system_prompt = self.get('planner_plan_system')
        user_prompt = self.get('planner_plan_first_user', question=question, memory=memory)
        return system_prompt, user_prompt

    def get_planner_plan_prompt_next(self, question: str, memory: str) -> tuple:
        """
        获取Planner Plan的system和user prompt（后续迭代）
        仅生成下一个需要验证的单个问题

        Returns:
            (system_prompt, user_prompt)
        """
        system_prompt = self.get('planner_plan_system')
        user_prompt = self.get('planner_plan_next_user', question=question, memory=memory)
        return system_prompt, user_prompt

    # ==================== Legacy Planner (OpenAI style) ====================

    def get_planner_prompt(self, question: str, memory: str) -> tuple:
        """
        获取Planner的system和user prompt（OpenAI风格，兼容旧版本）

        Returns:
            (system_prompt, user_prompt)
        """
        if self.prompt_style != 'GPT35':
            system_prompt = self.get('planner_system')
            few_shot_examples = self.get('planner_few_shot_examples')

            if memory.strip():
                user_prompt = self.get('planner_user_with_memory',
                                      few_shot_examples=few_shot_examples,
                                      question=question,
                                      memory=memory)
            else:
                user_prompt = self.get('planner_user_without_memory',
                                      few_shot_examples=few_shot_examples,
                                      question=question)

            return system_prompt, user_prompt
        else:
            # GPT35 style uses separate Judge + Plan
            raise NotImplementedError("Use get_planner_judge_prompt and get_planner_plan_prompt for GPT35 style")

    # ==================== Verifier ====================

    def get_verifier_prompt(self, sub_question: str, hypothesis: str, docs_text: str) -> tuple:
        """
        获取Verifier的system和user prompt（验证 Hypothesis）

        Args:
            sub_question: 子问题
            hypothesis: 假设答案
            docs_text: 检索到的文档文本

        Returns:
            (system_prompt, user_prompt)
        """
        system_prompt = self.get('verifier_system')
        user_prompt = self.get('verifier_user', sub_question=sub_question, hypothesis=hypothesis, docs_text=docs_text)
        return system_prompt, user_prompt

    def get_verifier_query_prompt(self, question: str, plan: str, memory: str = "") -> tuple:
        """
        获取Verifier Query Extractor的system和user prompt
        用于从原始问题中提取权威实体，生成不包含plan幻觉的检索词

        Args:
            question: 原始问题
            plan: 当前plan
            memory: 已验证的记忆（可选）

        Returns:
            (system_prompt, user_prompt)
        """
        system_prompt = self.get('verifier_query_system')
        user_prompt = self.get('verifier_query_user', question=question, plan=plan, memory=memory)
        return system_prompt, user_prompt

    # ==================== Memory ====================

    def get_memory_prompt(self, question: str, sub_question: str, hypothesis: str, docs_text: str, memory: str, verdict: str) -> tuple:
        """
        获取Memory模块的system和user prompt
        统一处理supported和contradicted两种情况

        Args:
            question: 原始问题
            sub_question: 子问题 (Q|H 对中的 Question)
            hypothesis: 假设答案 (Q|H 对中的 Hypothesis)
            docs_text: 检索到的文档
            memory: 已有记忆
            verdict: 验证结果 ("supported" | "contradicted")

        Returns:
            (system_prompt, user_prompt)
        """
        system_prompt = self.get('memory_system')

        if verdict == "supported":
            user_prompt = self.get('memory_user_supported',
                                   question=question,
                                   sub_question=sub_question,
                                   hypothesis=hypothesis,
                                   docs_text=docs_text,
                                   memory=memory)
        elif verdict == "contradicted":
            user_prompt = self.get('memory_user_contradicted',
                                   question=question,
                                   sub_question=sub_question,
                                   hypothesis=hypothesis,
                                   docs_text=docs_text,
                                   memory=memory)
        else:
            raise ValueError(f"Invalid verdict: {verdict}. Must be 'supported' or 'contradicted'")

        return system_prompt, user_prompt

    # ==================== Generate ====================

    def get_generate_prompt(self, question: str, memory: str) -> tuple:
        """
        获取Generate模块的system和user prompt
        基于已验证的完整路径知识生成最终答案

        Returns:
            (system_prompt, user_prompt)
        """
        system_prompt = self.get('generate_system')
        user_prompt = self.get('generate_user', question=question, memory=memory)
        return system_prompt, user_prompt

    # ==================== Legacy Methods (OpenAI style) ====================

    def get_memory_summarizer_prompt(self, memory: str) -> tuple:
        """
        获取Memory Summarizer的system和user prompt（OpenAI风格）

        Returns:
            (system_prompt, user_prompt)
        """
        if self.prompt_style == 'GPT35':
            raise NotImplementedError("Use get_memory_prompt for GPT35 style")
        system_prompt = self.get('memory_summarizer_system')
        user_prompt = self.get('memory_summarizer_user', memory=memory)
        return system_prompt, user_prompt

    def get_final_answer_prompt(self, question: str, memory: str) -> tuple:
        """
        获取Final Answer的system和user prompt（OpenAI风格）

        Returns:
            (system_prompt, user_prompt)
        """
        if self.prompt_style == 'GPT35':
            return self.get_generate_prompt(question, memory)
        system_prompt = self.get('final_answer_system')
        user_prompt = self.get('final_answer_user', question=question, memory=memory)
        return system_prompt, user_prompt

    def get_best_effort_answer_prompt(self, question: str, memory: str = None) -> tuple:
        """
        获取Best Effort Answer的system和user prompt（OpenAI风格）

        Returns:
            (system_prompt, user_prompt)
        """
        if self.prompt_style == 'GPT35':
            return self.get_generate_prompt(question, memory if memory else "")
        system_prompt = self.get('best_effort_answer_system')

        if memory and memory.strip():
            user_prompt = self.get('best_effort_answer_user_with_memory',
                                  question=question,
                                  memory=memory)
        else:
            user_prompt = self.get('best_effort_answer_user_no_memory',
                                  question=question)

        return system_prompt, user_prompt

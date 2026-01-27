"""
planRAG Prompt Loader
用于从 prompts/planRAG 目录加载各类 prompts（每个模块一个md文件）
"""
import os


class PromptLoader:
    """从 planRAG/prompts 目录加载所有 prompt 模板"""

    def __init__(self, prompts_dir: str = None):
        """
        初始化 PromptLoader

        Args:
            prompts_dir: prompt 文件目录路径。
                        默认使用 'planRAG' 目录。
        """
        current_dir = os.path.dirname(os.path.abspath(__file__))
        prompts_base_dir = os.path.join(current_dir, 'prompts')

        if prompts_dir is None:
            self.prompts_dir = os.path.join(prompts_base_dir, 'planRAG')
        elif os.path.isabs(prompts_dir):
            self.prompts_dir = prompts_dir
        else:
            self.prompts_dir = os.path.join(prompts_base_dir, prompts_dir)

        self._prompts = {}
        self._load_all_prompts()

    def _load_all_prompts(self):
        """加载所有 prompt 文件"""
        prompt_files = {
            'planner': 'planner.md',
            'reasoner_judge': 'reasoner_judge.md',
            'reasoner_thought': 'reasoner_thought.md',
            'summarizer_global_evidence': 'summarizer_global_evidence.md',
            'summarizer_local_answer': 'summarizer_local_answer.md',
            'checker': 'checker.md',
            'generator': 'generator.md',
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
        获取 prompt 并进行格式化

        Args:
            prompt_name: prompt 名称
            **kwargs: 用于格式化 prompt 的参数

        Returns:
            格式化后的 prompt 字符串
        """
        if prompt_name not in self._prompts:
            raise KeyError(f"Prompt '{prompt_name}' not found. Available prompts: {list(self._prompts.keys())}")

        prompt = self._prompts[prompt_name]

        if kwargs:
            return prompt.format(**kwargs)
        else:
            return prompt

    # ==================== 模块化获取方法 ====================

    def get_planner_prompt(self, question: str) -> str:
        """获取 Planner 模块的 prompt"""
        return self.get('planner', question=question)

    def get_reasoner_judge_prompt(self, question: str, plan: str, memory: str) -> str:
        """获取 Reasoner Judge 模块的 prompt"""
        return self.get('reasoner_judge', question=question, plan=plan, memory=memory)

    def get_reasoner_thought_prompt(self, question: str, memory: str) -> str:
        """获取 Reasoner Thought 模块的 prompt"""
        return self.get('reasoner_thought', question=question, memory=memory)

    def get_summarizer_global_evidence_prompt(self, question: str, docs: str) -> str:
        """获取 Global Evidence Memory 模块的 prompt"""
        return self.get('summarizer_global_evidence', question=question, docs=docs)

    def get_summarizer_local_answer_prompt(self, sub_question: str, memory: str, docs: str) -> str:
        """获取 Local Pathway 模块的 prompt"""
        return self.get('summarizer_local_answer', sub_question=sub_question, memory=memory, docs=docs)

    def get_checker_prompt(self, plan: str, sub_question: str, local_answer: str) -> str:
        """获取 Checker 模块的 prompt"""
        return self.get('checker', plan=plan, sub_question=sub_question, local_answer=local_answer)

    def get_generator_prompt(self, question: str, memory: str) -> str:
        """获取 Generator 模块的 prompt"""
        return self.get('generator', question=question, memory=memory)

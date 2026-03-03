"""
ReSP Prompt Loader
用于从 ReSP/prompts 目录加载各类 prompts
"""
import os


class PromptLoader:
    """从 ReSP/prompts 目录加载所有 prompt 模板"""

    def __init__(self, prompts_dir: str = None):
        """
        初始化 PromptLoader

        Args:
            prompts_dir: prompt 文件目录路径。
                        默认使用当前目录下的 'prompts' 目录。
        """
        current_dir = os.path.dirname(os.path.abspath(__file__))

        if prompts_dir is None:
            self.prompts_dir = os.path.join(current_dir, 'prompts')
        elif os.path.isabs(prompts_dir):
            self.prompts_dir = prompts_dir
        else:
            self.prompts_dir = os.path.join(current_dir, prompts_dir)

        self._prompts = {}
        self._load_all_prompts()

    def _load_all_prompts(self):
        """加载所有 prompt 文件"""
        prompt_files = {
            'reasoner_judge': 'reasoner_judge.md',
            'reasoner_plan': 'reasoner_plan.md',
            'summarizer_global_evidence': 'summarizer_global_evidence.md',
            'summarizer_local_pathway': 'summarizer_local_pathway.md',
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

    def get_reasoner_judge_prompt(self, question: str, memory: str) -> str:
        """获取 Reasoner Judge 模块的 prompt"""
        return self.get('reasoner_judge', question=question, memory=memory)

    def get_reasoner_plan_prompt(self, question: str, memory: str) -> str:
        """获取 Reasoner Plan 模块的 prompt"""
        return self.get('reasoner_plan', question=question, memory=memory)

    def get_summarizer_global_evidence_prompt(self, question: str, docs: str) -> str:
        """获取 Global Evidence Memory 模块的 prompt"""
        return self.get('summarizer_global_evidence', question=question, docs=docs)

    def get_summarizer_local_pathway_prompt(self, sub_question: str, memory: str) -> str:
        """获取 Local Pathway 模块的 prompt"""
        return self.get('summarizer_local_pathway', sub_question=sub_question, memory=memory)

    def get_generator_prompt(self, question: str, memory: str) -> str:
        """获取 Generator 模块的 prompt"""
        return self.get('generator', question=question, memory=memory)

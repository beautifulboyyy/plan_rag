import argparse
import os

import dotenv

from flashrag.config import Config
from flashrag.utils import get_dataset
from flashrag.pipeline import SequentialPipeline
from flashrag.prompt import PromptTemplate


dotenv.load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
openai_base_url = os.getenv("OPENAI_BASE_URL")

config_dict = {
    "data_dir": "datasets/",
    "index_path": "indexes/e5_Flat.index",
    "corpus_path": "indexes/general_knowledge.jsonl",
    # 只保留 retriever 的 model2path（如果 retriever 仍是本地 e5）
    "model2path": {"e5": "./e5-base-v2"},

    # 生成器改为 OpenAI
    "framework": "openai",  # ← 关键：指定使用 OpenAI API
    "generator_model": "gpt-3.5-turbo",  # ← OpenAI 模型名称

    # OpenAI API 设置（必须提供 api_key）
    "openai_setting": {
        "api_key": openai_api_key,  # 建议从环境变量读取
        "base_url": openai_base_url,  # 默认可省略
    },

    "retrieval_method": "e5",
    "metrics": ["em", "f1", "acc"],
    "retrieval_topk": 1,
    "save_intermediate_data": True,
}

config = Config(config_dict=config_dict)

all_split = get_dataset(config)
test_data = all_split["test"]
prompt_templete = PromptTemplate(
    config,
    system_prompt="Answer the question based on the given document. \
                    Only give me the answer and do not output any other words. \
                    \nThe following are given documents.\n\n{reference}",
    user_prompt="Question: {question}\nAnswer:",
)


pipeline = SequentialPipeline(config, prompt_template=prompt_templete)


output_dataset = pipeline.run(test_data, do_eval=True)
print("---generation output---")
print(output_dataset.pred)

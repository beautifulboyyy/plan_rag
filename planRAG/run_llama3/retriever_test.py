"""
独立检索器测试脚本
用于测试单个query的检索结果

使用方法:
    python retriever_test.py --query "你的查询"
    python retriever_test.py -q "你的查询" --topk 5
    python retriever_test.py -q "你的查询" --topk 5 --save

示例:
    python retriever_test.py --query "Who is the director of Inception?"
    python retriever_test.py -q "Christopher Nolan films" -k 10 --save
"""
import os
import sys
import argparse
import json
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from flashrag.config import Config
from flashrag.utils import get_retriever


class RetrieverTester:
    """检索器测试类"""

    def __init__(self, gpu_id: str = "0"):
        """
        初始化检索器测试器

        Args:
            gpu_id: GPU ID
        """
        self.gpu_id = gpu_id
        self.retriever = None
        self.config = None

    def initialize(self):
        """初始化配置和检索器"""
        print("正在初始化检索器...")

        # 配置参数覆盖（只需要检索器相关配置）
        config_dict = {
            "gpu_id": self.gpu_id,
            "disable_save": True,  # 禁用配置文件保存
        }

        # 加载配置
        config_file_path = os.path.join(os.path.dirname(__file__), "planrag_hf_config.yaml")
        self.config = Config(config_file_path=config_file_path, config_dict=config_dict)

        # 修正路径为绝对路径
        planrag_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        path_configs = ['index_path', 'corpus_path', 'retrieval_model_path']
        for key in path_configs:
            if key in self.config and not os.path.isabs(self.config[key]):
                self.config[key] = os.path.normpath(os.path.join(planrag_root, self.config[key]))

        # 初始化检索器
        self.retriever = get_retriever(self.config)
        print(f"检索器初始化完成 (方法: {self.config['retrieval_method']})")

    def search(self, query: str, topk: int = 3) -> dict:
        """
        执行检索

        Args:
            query: 检索查询
            topk: 召回数量

        Returns:
            检索结果字典
        """
        if self.retriever is None:
            self.initialize()

        # 执行检索
        retrieved_docs = self.retriever.batch_search([query], num=topk)
        docs = retrieved_docs[0] if retrieved_docs and retrieved_docs[0] else []

        # 构建结果
        documents = []
        for doc in docs:
            doc_info = {
                'id': doc.get('id', ''),
                'title': doc.get('title', ''),
                'contents': doc.get('contents', doc.get('text', '')),
                'score': doc.get('score', None)
            }
            documents.append(doc_info)

        result = {
            'query': query,
            'topk': topk,
            'num_results': len(documents),
            'documents': documents
        }

        return result

    def print_result(self, result: dict):
        """打印检索结果"""
        print(f"\n检索查询: {result['query']}")
        print(f"召回数量: {result['num_results']}/{result['topk']}")
        print("-" * 60)

        for i, doc in enumerate(result['documents']):
            score_str = f"(score: {doc['score']:.4f})" if doc['score'] is not None else ""
            print(f"\n[{i+1}] {score_str}")
            if doc['title']:
                print(f"    Title: {doc['title']}")
            print(f"    Content: {doc['contents']}")

    def save_result(self, result: dict):
        """保存检索结果到文件"""
        output_dir = os.path.join(os.path.dirname(__file__), "retriever_outputs")
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(output_dir, f"retrieval_{timestamp}.json")

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"\n结果已保存: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="独立检索器测试脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python retriever_test.py --query "Who is the director of Inception?"
    python retriever_test.py -q "Christopher Nolan" --topk 5 --save
        """
    )

    parser.add_argument(
        "-q", "--query",
        type=str,
        required=True,
        help="检索查询"
    )

    parser.add_argument(
        "-k", "--topk",
        type=int,
        default=3,
        help="召回文档数量 (默认: 3)"
    )

    parser.add_argument(
        "--save",
        action="store_true",
        help="保存检索结果到文件"
    )

    parser.add_argument(
        "--gpu_id",
        type=str,
        default="0",
        help="GPU ID (默认: 0)"
    )

    args = parser.parse_args()

    # 创建测试器并执行检索
    tester = RetrieverTester(gpu_id=args.gpu_id)
    result = tester.search(args.query, topk=args.topk)

    # 输出结果
    tester.print_result(result)

    # 保存结果
    if args.save:
        tester.save_result(result)


if __name__ == "__main__":
    main()

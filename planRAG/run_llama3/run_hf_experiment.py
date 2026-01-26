"""
运行本地HF模型 RPVM实验的脚本
使用 wiki18 小语料库 + Llama 3 8B Instruct (本地HF)
"""
import os
import sys
import argparse
from pathlib import Path

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 添加RPVM目录到路径
rpvm_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, rpvm_dir)

from flashrag.config import Config
from flashrag.utils import get_dataset
from rpvm_pipeline import RPVMPipeline


def run_hf_experiment(args):
    """运行本地HF模型 RPVM实验"""

    # 设置保存标识
    save_note = f"rpvm_llama3_hf_{args.split}"

    # 配置参数覆盖
    config_dict = {
        "split": [args.split],
        "gpu_id": args.gpu_id,
        "save_note": save_note,
    }

    # 加载配置
    config_file_path = os.path.join(os.path.dirname(__file__), "rpvm_hf_config.yaml")
    config = Config(config_file_path=config_file_path, config_dict=config_dict)

    # 修正路径为绝对路径
    rpvm_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    if 'data_dir' in config and not os.path.isabs(config['data_dir']):
        config['data_dir'] = os.path.join(rpvm_root, config['data_dir'])
        print(f"数据集目录: {config['data_dir']}")

    # 重新构建 dataset_path
    if 'dataset_path' in config:
        config['dataset_path'] = os.path.join(config['data_dir'], config['dataset_name'])
        print(f"数据集路径: {config['dataset_path']}")

    if 'index_path' in config and not os.path.isabs(config['index_path']):
        config['index_path'] = os.path.join(rpvm_root, config['index_path'])
        print(f"索引路径: {config['index_path']}")

    if 'corpus_path' in config and not os.path.isabs(config['corpus_path']):
        config['corpus_path'] = os.path.join(rpvm_root, config['corpus_path'])
        print(f"语料库路径: {config['corpus_path']}")

    if 'retrieval_model_path' in config and not os.path.isabs(config['retrieval_model_path']):
        config['retrieval_model_path'] = os.path.join(rpvm_root, config['retrieval_model_path'])
        print(f"检索模型路径: {config['retrieval_model_path']}")

    if 'generator_model_path' in config and not os.path.isabs(config['generator_model_path']):
        config['generator_model_path'] = os.path.join(rpvm_root, config['generator_model_path'])
        print(f"生成器模型路径: {config['generator_model_path']}")

    if 'save_dir' in config and not os.path.isabs(config['save_dir']):
        config['save_dir'] = os.path.join(rpvm_root, config['save_dir'])
        print(f"输出目录: {config['save_dir']}")

    # 打印生成器配置信息
    print(f"生成器框架: {config['framework']}")
    print(f"生成器模型: {config['generator_model']}")
    print(f"生成器模型路径: {config['generator_model_path']}")

    # 加载数据集
    print(f"加载数据集: {config['dataset_name']}, split: {args.split}")
    all_split = get_dataset(config)

    print(f"all_split 类型: {type(all_split)}")

    test_data = all_split[args.split]

    # 检查数据集是否加载成功
    if test_data is None:
        print(f"错误：无法加载数据集 split '{args.split}'")
        print(f"可用的 splits: {list(all_split.keys()) if all_split else 'None'}")
        dataset_path = os.path.join(config['data_dir'], config['dataset_name'], f"{args.split}.jsonl")
        print(f"期望的数据集文件: {dataset_path}")
        print(f"文件存在: {os.path.exists(dataset_path)}")
        return None

    print(f"原始数据集大小: {len(test_data)}")

    # 如果指定了样本数量(用于测试)
    if args.num_samples and args.num_samples > 0:
        print(f"仅使用 {args.num_samples} 个样本进行测试")
        from flashrag.dataset import Dataset
        sampled_data = test_data.data[:args.num_samples]
        test_data = Dataset(config, data=sampled_data)

    print(f"最终数据集大小: {len(test_data)}")

    # 创建RPVM Pipeline
    print("正在初始化 planRAG Pipeline (使用本地 HF Llama 3)...")
    pipeline = RPVMPipeline(config)

    # 运行实验
    print("开始运行 planRAG 实验...")
    result_dataset = pipeline.run(test_data, do_eval=True)

    print("实验完成！")
    print(f"结果保存到: {config['save_dir']}")

    return result_dataset


def main():
    parser = argparse.ArgumentParser(description="运行本地HF模型 RPVM实验")

    parser.add_argument(
        "--split",
        type=str,
        default="dev",
        choices=["train", "dev", "test"],
        help="数据集分割"
    )

    parser.add_argument(
        "--gpu_id",
        type=str,
        default="1",
        help="GPU ID (用于检索器和生成器)"
    )

    parser.add_argument(
        "--num_samples",
        type=int,
        default=5,
        help="测试样本数量，默认5个用于快速测试"
    )

    args = parser.parse_args()
    run_hf_experiment(args)


if __name__ == "__main__":
    main()

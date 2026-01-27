#!/bin/bash
# 运行本地HF模型 planRAG 实验的脚本
# 使用 Llama 3 8B Instruct (本地)

# 切换到脚本所在目录
cd "$(dirname "$0")"

# 激活conda环境
conda activate lsw_rpvm

# 设置环境变量
export CUDA_VISIBLE_DEVICES=0

# 运行实验
python ./run_hf_experiment.py \
    --split dev \
    --gpu_id 0 \
    --num_samples 5

echo "实验完成！"

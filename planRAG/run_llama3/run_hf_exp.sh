#!/bin/bash
# 运行本地HF模型 RPVM实验的脚本
# 使用 Llama 3 8B Instruct (本地)

# 切换到脚本所在目录
cd "$(dirname "$0")"

# 激活conda环境（如果需要）
conda activate lsw_rpvm

# 设置环境变量（使用单个GPU）
export CUDA_VISIBLE_DEVICES=0

# 运行实验（使用GPT35 prompt风格 + Llama 3 8B）
python ./run_hf_experiment.py \
    --split dev \
    --gpu_id 0 \
    --num_samples 5

echo "实验完成！"

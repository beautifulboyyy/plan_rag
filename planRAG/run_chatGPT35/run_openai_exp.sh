#!/bin/bash
# 运行OpenAI API RPVM实验的脚本（重构版）

# 切换到脚本所在目录
cd "$(dirname "$0")"

# 激活conda环境（如果需要）
conda activate lsw_rpvm

# 设置环境变量
export CUDA_VISIBLE_DEVICES=0

# 运行实验（使用重构后的GPT35 prompt）
python ./run_openai_experiment.py \
    --split dev \
    --gpu_id 0 \
    --num_samples 5

echo "实验完成！"

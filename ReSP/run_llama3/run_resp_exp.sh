#!/bin/bash
# ReSP 实验运行脚本

# 默认参数
SPLIT="dev"
GPU_ID="0"
NUM_SAMPLES=5

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --split)
            SPLIT="$2"
            shift 2
            ;;
        --gpu_id)
            GPU_ID="$2"
            shift 2
            ;;
        --num_samples)
            NUM_SAMPLES="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "========== ReSP Experiment =========="
echo "Split: $SPLIT"
echo "GPU ID: $GPU_ID"
echo "Num Samples: $NUM_SAMPLES"
echo "======================================"

# 运行实验
python run_resp_experiment.py \
    --split $SPLIT \
    --gpu_id $GPU_ID \
    --num_samples $NUM_SAMPLES

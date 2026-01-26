"""
Plan Generation Experiment for Llama3 8B
Test model's ability to generate efficient global planning for multi-hop questions.
"""

import argparse
import json
import os
from pathlib import Path
import re

from transformers import AutoModelForCausalLM, AutoTokenizer
import torch


def parse_args():
    parser = argparse.ArgumentParser(description="Plan generation experiment")
    parser.add_argument("--model_path", type=str,
                        default="/home/algroup/lsw/planRAG/planRAG/llama3-8b-instruct",
                        help="Path to Llama3 model")
    parser.add_argument("--dataset_path", type=str,
                        default="/home/algroup/lsw/planRAG/planRAG/datasets/2wikimultihopqa/train.jsonl",
                        help="Path to dataset")
    parser.add_argument("--prompt_path", type=str,
                        default="/home/algroup/lsw/planRAG/planRAG/experiments/plan_evaluation/prompts/planner_global.md",
                        help="Path to prompt template")
    parser.add_argument("--output_dir", type=str,
                        default="/home/algroup/lsw/planRAG/planRAG/experiments/plan_evaluation/outputs/llama3_8b_global_plan",
                        help="Output directory")
    parser.add_argument("--num_samples", type=int, default=100,
                        help="Number of test samples")
    parser.add_argument("--max_new_tokens", type=int, default=512,
                        help="Max new tokens for generation")
    parser.add_argument("--temperature", type=float, default=0.0,
                        help="Generation temperature (0 for deterministic)")
    return parser.parse_args()


def load_prompt(prompt_path: str) -> str:
    """Load and return the prompt template."""
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


def load_dataset(dataset_path: str, num_samples: int):
    """Load dataset and return first N samples."""
    samples = []
    with open(dataset_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= num_samples:
                break
            sample = json.loads(line.strip())
            samples.append({
                "id": sample.get("id", f"sample_{i}"),
                "question": sample.get("question", "")
            })
    return samples


def format_prompt(template: str, question: str) -> str:
    """Format the prompt template with the question."""
    return template.replace("{question}", question)


def generate_plan(model, tokenizer, prompt: str, max_new_tokens: int, temperature: float) -> str:
    """Generate plan from the model."""
    # Apply chat template for Llama3
    messages = [
        {"role": "user", "content": prompt}
    ]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

    inputs = tokenizer(text, return_tensors="pt").to(model.device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            do_sample=temperature > 0,
            pad_token_id=tokenizer.eos_token_id,
        )

    response = outputs[0][inputs["input_ids"].shape[-1]:]
    response_text = tokenizer.decode(response, skip_special_tokens=True)
    return response_text


def parse_output(raw_output: str):
    """Parse the raw model output into reasoning and plan."""
    reasoning = ""
    plan = ""

    # Simple parsing: split by "Reasoning:" and "Plan:" markers if present
    # Otherwise try to find the sections by looking for common patterns

    lines = raw_output.strip().split("\n")

    # Try to identify reasoning and plan sections
    in_reasoning = False
    in_plan = False

    for line in lines:
        line_lower = line.lower().strip()
        if "reasoning:" in line_lower:
            in_reasoning = True
            in_plan = False
            continue
        if "plan:" in line_lower:
            in_plan = True
            in_reasoning = False
            continue

        if in_reasoning:
            reasoning += line + "\n"
        elif in_plan:
            plan += line + "\n"

    # If no markers found, try heuristic parsing
    if not reasoning and not plan:
        # Assume everything before "Plan:" is reasoning
        if "Plan:" in raw_output:
            parts = raw_output.split("Plan:", 1)
            reasoning = parts[0].strip()
            plan = parts[1].strip()
        else:
            # Just return the raw output as reasoning, empty plan
            reasoning = raw_output.strip()
            plan = ""

    return reasoning.strip(), plan.strip()


def main():
    args = parse_args()

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    print(f"Loading model from: {args.model_path}")
    tokenizer = AutoTokenizer.from_pretrained(args.model_path)
    model = AutoModelForCausalLM.from_pretrained(
        args.model_path,
        torch_dtype=torch.float16,
    ).cuda()
    print("Model loaded successfully")

    # Load prompt template
    prompt_template = load_prompt(args.prompt_path)
    print(f"Prompt loaded from: {args.prompt_path}")

    # Load dataset
    samples = load_dataset(args.dataset_path, args.num_samples)
    print(f"Loaded {len(samples)} samples from dataset")

    # Generate plans
    results = []
    for i, sample in enumerate(samples):
        print(f"Processing {i+1}/{len(samples)}: {sample['id']}")

        # Format prompt
        prompt = format_prompt(prompt_template, sample["question"])

        # Generate
        raw_output = generate_plan(model, tokenizer, prompt, args.max_new_tokens, args.temperature)

        # Parse output
        reasoning, plan = parse_output(raw_output)

        result = {
            "id": sample["id"],
            "question": sample["question"],
            "reasoning": reasoning,
            "plan": plan,
            "raw_output": raw_output
        }
        results.append(result)

    # Save results
    output_path = os.path.join(args.output_dir, "results.jsonl")
    with open(output_path, "w", encoding="utf-8") as f:
        for result in results:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")

    print(f"\nResults saved to: {output_path}")
    print(f"Total samples: {len(results)}")


if __name__ == "__main__":
    main()

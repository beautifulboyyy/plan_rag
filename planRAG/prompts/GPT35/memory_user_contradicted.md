## Input Information

**Original Question**: {question}

**Sub-Question**: {sub_question}

**Original Hypothesis (Contradicted)**: {hypothesis}

**Retrieved Documents**:
{docs_text}

**Existing Memory**:
{memory}

## Task

The original hypothesis was CONTRADICTED by the evidence in the documents.
Your task is to:
1. Analyze what the CORRECT answer should be based on the documents
2. Refine this into a corrected Q&A pair
3. Ensure it can be directly used for subsequent reasoning

## Requirements

- Output in format: "Q: [Sub-Question] | A: [Corrected Answer]"
- Extract the CORRECT information from documents
- Make it concise but preserve critical facts
- Ensure it connects logically with existing Memory

## Important

The corrected Q&A pair should provide the RIGHT direction for future reasoning, replacing the incorrect hypothesis.

## Output

[Corrected Q&A Pair]:
Q: {sub_question} | A: [Correct answer from documents]

## Input Information

**Original Question**: {question}

**Sub-Question**: {sub_question}

**Hypothesis (Verified)**: {hypothesis}

**Retrieved Documents**:
{docs_text}

**Existing Memory**:
{memory}

## Task

The hypothesis above has been VERIFIED by the evidence in the documents.
Your task is to:
1. Extract the key factual answer from the documents that supports the hypothesis
2. Refine and compress this into a verified Q&A pair
3. Ensure it can be directly used for subsequent reasoning

## Requirements

- Output in format: "Q: [Sub-Question] | A: [Answer]"
- Bind the evidence to the Q&A pair
- Make it concise but preserve critical facts
- Ensure it connects logically with existing Memory

## Output

[Verified Q&A Pair]:
Q: {sub_question} | A: [Correct answer extracted from documents]

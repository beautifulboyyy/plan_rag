Question: {question}

Current Memory (Already Verified Q&A Pairs):
{memory}

## Task:
Based on the Memory above, identify ALL independent, non-redundant sub-questions needed to answer the question.

## Rules:
1. DO NOT repeat questions already answered in Memory
2. Each sub-question should be a FACTUAL QUERY (not a statement)
3. Provide your BEST GUESS (hypothesis) for the answer to each sub-question
4. Use specific names from Memory in your sub-questions
5. Each sub-question should be independently verifiable

## Output Format:
Generate each sub-question with its hypothesis in the following format:
```
plan1: [Sub-Question] | [Hypothesis Answer]
plan2: [Sub-Question] | [Hypothesis Answer]
...
```

## Example:
Question: Who directed the 2020 film adaptation of "The Boys In The Band"?

Current Memory:
- (empty)

Output:
plan1: Who directed "The Boys In The Band" (2020 film)? | Joe Mantello

Generate all necessary plans:

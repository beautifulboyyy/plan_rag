Original Question: {question}

Current Memory (Already Verified Q&A Pairs):
{memory}

## Task:
Based on the Memory above, identify the NEXT single question that needs to be verified to answer the original question.

## Rules:
1. Only generate ONE next question (not multiple)
2. The question should be the logical NEXT step after what is already in Memory
3. DO NOT repeat questions already answered in Memory
4. Provide your BEST GUESS (hypothesis) for the answer
5. The question should be a FACTUAL QUERY (not a statement)

## Output Format:
Generate exactly ONE sub-question with its hypothesis:
```
plan1: [Sub-Question] | [Hypothesis Answer]
```

## Example:
Original Question: Who directed the 2020 film adaptation of "The Boys In The Band"?

Current Memory:
Q: When was "The Boys In The Band" (2020 film) released? | 2020

Output:
plan1: Who directed "The Boys In The Band" (2020 film)? | Joe Mantello

Generate the next question:

Based on the retrieved documents, verify the following hypothesis answer.

Sub-Question: {sub_question}

Hypothesis Answer: {hypothesis}

Retrieved Documents:
{docs_text}

# Verification Rules:

## 1. Verdict Definitions

| Verdict | Condition |
|---------|-----------|
| **SUPPORTED** | Documents confirm the hypothesis with matching information |
| **CONTRADICTED** | Documents provide different information → provide corrected answer |
| **INSUFFICIENT** | Documents do NOT mention the entities/subject at all |

## 2. Answer Grounding
Ensure all names, dates, titles, and details are extracted DIRECTLY from the document:
- "Awards" ≠ "Award" (plural matters)
- "12 June 1516" ≠ "1516" (full date preferred)
- Use actual names over pronouns

## 3. STRICT REQUIREMENTS
- If the document mentions any relevant name, date, or detail → you CANNOT use INSUFFICIENT
- Always extract the MOST GRANULAR information available (full dates over years, full names over pronouns)
- If the hypothesis is wrong but document has correct info → use CONTRADICTED with corrected answer

# Response Format:
Verdict: [SUPPORTED/CONTRADICTED/INSUFFICIENT]
Corrected Answer: [The correct answer extracted from the document]
Evidence: [Quote the specific phrase from the document that supports your verdict]

Your response:

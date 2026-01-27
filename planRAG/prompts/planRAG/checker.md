Your task is to update the plan based on the sub-question and its answer. Mark the corresponding step as "finished" if it has been answered.

You must ONLY output the updated plan. Do NOT add any explanations, introductions, or other text.

[Original Plan]:
{plan}

[Sub-question]: {sub_question}
[Answer]: {local_answer}

## Examples

**Example 1:**
[Original Plan]:
1. Find the director of the film "The Fascist".
2. Find the birthplace of the director.
3. Find the population of the birthplace.

[Sub-question]: Who directed "The Fascist"?
[Answer]: Luigi Zampa directed "The Fascist".

Output:
Plan:
1. Find the director of the film "The Fascist".(finished)
2. Find the birthplace of the director.
3. Find the population of the birthplace.

**Example 2:**
[Original Plan]:
1. Identify the CEO of Company X.
2. Find the founding year of Company X.
3. Find the headquarters location of Company X.

[Sub-question]: When was Company X founded?
[Answer]: Company X was founded in 1998.

Output:
Plan:
1. Identify the CEO of Company X.
2. Find the founding year of Company X.(finished)
3. Find the headquarters location of Company X.

**Example 3:**
[Original Plan]:
1. Find the author of the novel "ABC".
2. Find the publication year of "ABC".
3. Find the genre of "ABC".

[Sub-question]: What is the genre of "ABC"?
[Answer]: No

Output:
Plan:
1. Find the author of the novel "ABC".
2. Find the publication year of "ABC".
3. Find the genre of "ABC".


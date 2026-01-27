Question: Where was the director of film The Fascist born?
1.planner模块先生成Q的整体蓝图：
    prompts:
# Role
You are a master of multi-hop task planning, capable of efficiently breaking down a multi-hop logical problem into step-by-step processing and planning.
Do not generate explanations other than those related to planning.
# Input
- A multi-hop question.

# Output Format
**Plan**: A numbered list of search intents.

# Examples

## Example 1 (Bridge Type)
Question: Who is the mother of the director of film Polish-Russian War?
Plan:
1. First, identify the director of the film Polish-Russian War.
2. Then, find out who the mother of that director is.

## Example 2 (Comparison Type)
Question: Which film came out first, Blind Shaft or The Mask Of Fu Manchu?
Plan:
1. Determine the release date of Blind Shaft.
2. Determine the release date of The Mask of Fu Manchu.
3. Compare the two release dates to identify which film was released earlier.


# Now Begin
Question: {question}
    **Plan**:\n\n1. Identify the director of the film The Fascist.\n2. Find out where the director of the film The Fascist was born.

2.进入ReSP迭代：
a.首先进入Reasoner模块，它由Judge模块和plan模块组成，
    Judge：依据当前的规划和记忆判断能否解答Q
    prompts:Judging based solely on the current known information and without allowing for inference, are you able to completely and accurately respond to the question Overarching question? \nKnown information: Combined memory queues.\nIf you can, please reply with "Yes" directly; if you cannot and need more information, please reply with "No" directly.
    Reasoner:生成下一条必要的子问题
    prompts：You serve as an intelligent assistant, adept at facilitating users through complex, multi-hop reasoning across multiple documents. Please understand the information gap between the currently known information and the target problem.Your task is to generate one thought in the form of question for next retrieval step directly. DON’T generate the whole thoughts at once!\n DON’T generate thought which has been retrieved.\n [Known information]: Combined memory queues\n[Target question]:Overarching question\n[YouThought]:
    但是第一轮默认judge为no，默认以多跳问题Q作为第一轮的子问题直接检索。
b.以多跳问题Q作为第一轮的子问题直接检索：Retriever(Q) = top3 docs
c.双路记忆摘要器：
    Global Evidence Memory (Q，docs) = 与问题Q相关的精炼evidence
    prompts：Passages: docs\nYour job is to act as a professional writer. You will write a good quality passage that can support the given prediction about the question only based on the information in the provided supporting passages. Now, let’s start.After you write, please write [DONE] to indicate you are done. Do not write a prefix (e.g., "Response:") while writing a passage.\nQuestion:Overarching question\nPassage:
    Local Pathway（q，docs） = 子问题以及答案
    prompts：Judging based solely on the current known information and without allowing for inference, are you able to respond completely and accurately to the question Sub-question? \nKnown information: Combined memory queues.If yes, please reply with "Yes", followed by an accurate response to the question Sub-question, without restating the question; if no, please reply with "No"directly.

d.Checker：依据迭代进度检查当前的任务完成度，给已经完成的任务进行确认标记。
**Plan**:\n\n1. Identify the director of the film The Fascist.(finished)\n2. Find out where the director of the film The Fascist was born.
第二轮迭代：
    Judge：依据当前的规划和记忆判断能否解答Q
    prompts:Judging based solely on the current known information and without allowing for inference, are you able to completely and accurately respond to the question Overarching question? \nKnown information: Combined memory queues.\nIf you can, please reply with "Yes" directly; if you cannot and need more information, please reply with "No" directly.
    Reasoner:生成下一条必要的子问题
    prompts：You serve as an intelligent assistant, adept at facilitating users through complex, multi-hop reasoning across multiple documents. Please understand the information gap between the currently known information and the target problem.Your task is to generate one thought in the form of question for next retrieval step directly. DON’T generate the whole thoughts at once!\n DON’T generate thought which has been retrieved.\n [Known information]: Combined memory queues\n[Target question]:Overarching question\n[YouThought]:

继续检索，压缩记忆，check plans，最后直到judge判断能回答，交给generator回答
generator：Answer the question based on the given reference.\nOnly give me the answer and do not output any other words.\nThe following are given reference:Combined memory queues\nQuestion: Overarching question

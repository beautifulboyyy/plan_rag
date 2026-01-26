Question: Where was the director of film The Fascist born?
1.planner模块先生成Q的整体蓝图：
    **Plan**:\n\n1. Identify the director of the film The Fascist.\n2. Find out where the director of the film The Fascist was born.

2.进入ReSP迭代：
a.首先以多跳问题Q作为第一轮的子问题直接检索：Retriever(Q) = top3 docs
b.双路记忆摘要器：
    Global Evidence Memory (Q，docs) = 与问题Q相关的精炼evidence
    prompts：Passages: docs\nYour job is to act as aprofessional writer. You will write a goodquality passage that can support the given prediction about the question onlyGlobal EvidenceSummarizerLocal Pathwaybased on the information in the provided supporting passages. Now, let’s start.After you write, please write [DONE] to indicate you are done. Do not writea prefix (e.g., "Response:") while writing a passage.\nQuestion:Overarchingquestion\nPassage:
    Local Pathway（q，docs） = 子问题以及答案
    prompts：Judging based solely on the current known information and without allowing for inference, are you able to respond completely and accurately to thequestion Sub-question? \nKnown information: Combined memory queues.If yes, please reply with "Yes", followed by an accurate response to the questionSub-question, without restating the question; if no, please reply with "No"directly.

c.Checker：依据迭代进度检查当前的任务完成度，给已经完成的任务进行确认标记。
**Plan**:\n\n1. Identify the director of the film The Fascist.\n2. Find out where the director of the film The Fascist was born.
第二轮迭代：
    Judge：依据当前的规划和记忆判断能否解答Q
    prompts:Judging based solely on the current known information and without allowingfor inference, are you able to completely and accurately respond to the question Overarching question? \nKnown information: Combined memory queues.\nIf you can, please reply with "Yes" directly; if you cannot and need moreinformation, please reply with "No" directly.
    Reasoner:生成下一条必要的子问题
    prompts：You serve as an intelligent assistant, adept at facilitating users through complex, multi-hop reasoning across multiple documents. Please understand theinformation gap between the currently known information and the targetproblem.Your task is to generate one thought in the form of question for nextretrieval step directly. DON’T generate the whole thoughts at once!\n DON’Tgenerate thought which has been retrieved.\n [Known information]: Combinedmemory queues\n[Targetquestion]:Overarching question\n[YouThought]:

继续检索，压缩记忆，check plans，最后直到judge判断能回答，交给generator回答
generator：Answer the question based on the given reference.\nOnly give me the annswer and do not output any other words.\nThe following are given reference:Combined memory queues\nQuestion: Overarching question

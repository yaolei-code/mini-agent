"""
agent.py —— ReAct Agent 的核心循环
====================================
这就是博主说的 "手搓 Agent" 的核心文件。

整个 Agent 的本质就是一个 while 循环：
  1. 把对话历史发给 LLM
  2. LLM 返回它的 "思考" 和 "行动"
  3. 我们解析出行动，执行它
  4. 把执行结果（观察）追加到对话历史
  5. 重复，直到 LLM 说 "完成"

ReAct = Reasoning（推理）+ Acting（行动）
ReAct Agent = 普通的 Agent + 在行动前先思考

如果你能完全理解这个文件，你就已经理解了 Agent 的底层原理。
之后你看 LangChain、AutoGPT、SWE-Agent、OpenClaw，都是在不同层面
包装这个循环。
"""

import re
import json
import os
import sys
from openai import OpenAI
from dotenv import load_dotenv
from tools import execute_tool, get_tools_description

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 加载 .env 文件中的环境变量
load_dotenv()


# ============================================================
# System Prompt —— Agent 的"人设"和"行为规范"
# ============================================================
# 这是整个 Agent 最重要的设计点之一。
# prompt 写得好不好，直接决定了 Agent 稳不稳定、聪不聪明。
# 试试改这里的文字，观察 Agent 的行为怎么变化！

SYSTEM_PROMPT = """你是一个学习版 AI Coding Agent。你需要一步步观察代码仓库，使用工具帮助用户理解、定位和分析代码问题。

## 你可以使用的工具

{tools_description}

## 回答格式（必须严格遵守！）

对于每一步，你必须按照以下格式输出：

Thought: [你当前的思考过程——你要解决什么问题？接下来打算怎么做？]
Action: [你要使用的工具名字，或者 "Finish" 如果你已经可以给出最终答案]
Action Input: [传给工具的输入参数，或者你的最终答案（当 Action 是 Finish 时）]

## 重要规则

1. 每次只能调用一个工具。
2. 在调用工具之前，先思考（Thought）你需要什么信息，以及哪个工具能帮你获取。
3. 工具的返回结果会以 "Observation: ..." 的形式返回给你，你需要在下一轮继续思考。
4. 当你收集到足够的信息、可以回答用户时，Action 写 "Finish"，Action Input 写你的完整回答。
5. 不要编造信息。如果你通过工具查不到，就如实告诉用户。
6. 当前版本是只读 Coding Agent。你可以查看、搜索和分析代码，但不能修改文件，也不能声称已经修改了代码。
7. 遇到代码任务时，优先使用 list_files 了解项目结构，再用 search_code 定位关键词，最后用 read_file 阅读关键文件。
8. 最终回答要说明你查看了哪些文件、发现了什么、建议下一步怎么改。
9. 输出保持工程化和简洁，不要使用 emoji，不要使用营销化或夸张语气。

## 示例

用户："这个项目的登录逻辑在哪里？"

Thought: 用户想定位登录逻辑。我需要先查看项目结构，判断这是 Java、Python 还是前端项目。
Action: list_files
Action Input: .

---

现在开始！记住：每一步都必须包含 Thought、Action、Action Input 三行。"""


# ============================================================
# ReAct Agent 类
# ============================================================
class ReActAgent:
    """
    ReAct Agent 的实现。

    核心流程：
        User Question → [ Thought → Action → Observation ] × N → Final Answer

    这个类只做三件事：
        1. 管理对话历史（messages）
        2. 调用 LLM 拿到下一步的 Thought/Action
        3. 解析 LLM 的输出，执行工具
    """

    def __init__(self, verbose: bool = True):
        """
        初始化 Agent。

        参数：
            verbose: 如果为 True，会打印每一步的详情（调试/学习用）
        """
        self.verbose = verbose

        # 初始化 DeepSeek 客户端
        # DeepSeek 的 API 完全兼容 OpenAI 格式，直接用 openai 库就行！
        self.client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        )
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

        # 把工具描述插入 system prompt
        self.system_prompt = SYSTEM_PROMPT.format(
            tools_description=get_tools_description()
        )

    def run(self, user_question: str, max_steps: int = 10) -> str:
        """
        运行 Agent，回答用户的问题。

        参数：
            user_question: 用户的问题
            max_steps: 最多允许多少轮思考-行动（防止死循环）

        返回：
            Agent 的最终回答
        """
        # ============================================
        # 初始化对话历史
        # ============================================
        # messages 就是一个列表，每个元素是一个 dict。
        # 这就是 LLM 看到的"上下文"。
        # 如果对话太长，超过了模型的 context window，
        # 就需要 "auto compact"（自动压缩）—— 这是 Codex/OpenClaw 的核心功能之一。
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_question},
        ]

        if self.verbose:
            print("=" * 60)
            print(f"[USER] 用户提问：{user_question}")
            print("=" * 60)

        # ============================================
        # ★★★ Agent 的核心循环 ★★★
        # ============================================
        # 这就是你面试被问到 "Agent 怎么实现的" 时的标准答案。
        for step in range(1, max_steps + 1):
            if self.verbose:
                print(f"\n{'-' * 40}")
                print(f"[STEP] 第 {step} 步")
                print(f"{'-' * 40}")

            # --- 步骤 1：调用 LLM，获取下一步的 Thought 和 Action ---
            response = self._call_llm(messages)

            # --- 步骤 2：解析 LLM 的输出 ---
            parsed = self._parse_response(response)

            if parsed is None:
                # LLM 输出格式不对，提醒它重新输出
                if self.verbose:
                    print("[WARN] LLM 输出格式异常，要求重新输出")
                messages.append({
                    "role": "user",
                    "content": "你的输出格式不正确。请严格按照格式输出：\nThought: [你的思考]\nAction: [工具名或Finish]\nAction Input: [参数或最终答案]"
                })
                continue

            thought = parsed.get("thought", "")
            action = parsed.get("action", "")
            action_input = parsed.get("action_input", "")

            if self.verbose:
                print(f"[THOUGHT] 思考：{thought}")
                print(f"[ACTION] 行动：{action}")
                if action != "Finish":
                    print(f"[INPUT] 输入：{action_input}")

            # --- 步骤 3：判断是继续还是结束 ---
            if action == "Finish":
                # Agent 认为任务完成了，返回最终答案
                if self.verbose:
                    print(f"\n{'=' * 60}")
                    print("[DONE] Agent 完成！")
                    print(f"{'=' * 60}")
                return action_input

            # --- 步骤 4：执行工具 ---
            observation = execute_tool(action, action_input)

            if self.verbose:
                # 截断过长的 observation
                display_obs = observation[:200] + "..." if len(observation) > 200 else observation
                print(f"[OBSERVATION] 观察：{display_obs}")

            # --- 步骤 5：把 LLM 的输出和执行结果追加到对话历史 ---
            # 这一步非常关键！Agent 正是通过不断往 messages 里加东西，
            # 才能"记住"之前做了什么、查到了什么。
            messages.append({
                "role": "assistant",
                "content": f"Thought: {thought}\nAction: {action}\nAction Input: {action_input}"
            })
            messages.append({
                "role": "user",
                "content": f"Observation: {observation}"
            })

        # 超过最大步数，强制结束
        return "抱歉，思考步骤超过了限制。请尝试把问题拆分成更小的子问题。"

    def _call_llm(self, messages: list) -> str:
        """
        调用 LLM，拿到它的回复文本。

        这里用的是 DeepSeek 的 API，但换成 OpenAI / 智谱 / Moonshot
        只需要改 client 的 base_url 和 api_key，代码完全不用动。
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.0,  # 温度设为 0，让输出更稳定、更可预测
                max_tokens=1024,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return (
                "Thought: 调用大模型失败，我无法继续使用工具。\n"
                "Action: Finish\n"
                f"Action Input: 调用大模型失败：{e}"
            )

    def _parse_response(self, response: str) -> dict | None:
        """
        解析 LLM 的输出，提取 Thought、Action、Action Input。

        这是 Agent 里最"脆弱"的环节——LLM 的输出是自然语言，
        格式可能不完全符合预期。真正的 Agent 框架会在这里做大量的
        容错处理和 retry 逻辑。

        我们先用正则表达式做最基础的解析。
        """
        result = {}

        # 提取 Thought
        thought_match = re.search(r"Thought:\s*(.+?)(?=\nAction:|\Z)", response, re.DOTALL)
        if thought_match:
            result["thought"] = thought_match.group(1).strip()

        # 提取 Action
        action_match = re.search(r"Action:\s*(.+?)(?=\nAction Input:|\Z)", response, re.DOTALL)
        if action_match:
            result["action"] = action_match.group(1).strip()

        # 提取 Action Input
        action_input_match = re.search(r"Action Input:\s*(.+)", response, re.DOTALL)
        if action_input_match:
            result["action_input"] = action_input_match.group(1).strip()

        # 两个关键字段缺一不可
        if not result.get("action"):
            print(f"  [DEBUG] 无法解析的 LLM 输出：\n{response}")
            return None

        # 如果没有 Thought，给个默认值
        if "thought" not in result:
            result["thought"] = "（未提供思考过程）"

        # 如果没有 Action Input，默认为空字符串
        if "action_input" not in result:
            result["action_input"] = ""

        return result


# ============================================================
# 自测：如果你直接运行这个文件
# ============================================================
if __name__ == "__main__":
    print("[TEST] 测试 Agent（请在 .env 文件中配置 DEEPSEEK_API_KEY）\n")

    agent = ReActAgent(verbose=True)

    # 测试一个简单的数学问题
    question = "3 乘以 5 加上 2 等于多少？"
    answer = agent.run(question)
    print(f"\n[ANSWER] 最终答案：{answer}")

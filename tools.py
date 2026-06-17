"""
tools.py —— Agent 的工具箱
============================
每个工具就是一个 Python 函数，Agent 可以调用它们来完成具体任务。

这就是博主说的 "function call" 的底层原理：
Agent 不是真的"调用"了函数，而是 LLM 输出了一段文字说"我要调用计算器"，
然后我们的 Python 代码解析这段文字，真正去执行对应的函数。

当你理解了这一点，你再去看任何 Agent 框架（LangChain、AutoGPT 等），
就会发现它们只是在这个核心逻辑外面包了层皮。
"""

import math
import datetime


# ============================================================
# 工具 1：计算器
# ============================================================
def calculator(expression: str) -> str:
    """
    安全的数学计算器。
    支持：加减乘除、幂运算、三角函数、sqrt、log 等。

    为什么不用 eval()？
    —— 因为 eval() 可以执行任意 Python 代码，太危险了。
    我们只允许数学运算，把危险的东西全部过滤掉。
    """
    # 白名单：只允许这些名字出现在表达式里
    allowed_names = {
        # 数学常量
        "pi": math.pi,
        "e": math.e,
        "tau": math.tau,
        # 数学函数
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "sqrt": math.sqrt,
        "log": math.log,
        "log2": math.log2,
        "log10": math.log10,
        "pow": pow,
        "abs": abs,
        "round": round,
        "ceil": math.ceil,
        "floor": math.floor,
        "factorial": math.factorial,
    }

    try:
        # 编译表达式，只允许 eval（数学运算），不允许 exec（执行语句）
        code = compile(expression, "<calculator>", "eval")

        # 安全检查：遍历表达式中用到的所有名字
        for name in code.co_names:
            if name not in allowed_names:
                return f"❌ 不允许使用 '{name}'，只能使用数学运算"

        # 在安全的名字空间里执行
        result = eval(code, {"__builtins__": {}}, allowed_names)
        return f"计算结果：{result}"

    except ZeroDivisionError:
        return "❌ 错误：不能除以零"
    except Exception as e:
        return f"❌ 计算出错：{e}"


# ============================================================
# 工具 2：模拟搜索
# ============================================================
def search(query: str) -> str:
    """
    模拟的网络搜索工具。

    在真实项目中，这里会调用 SerpAPI / Google Search API / Tavily 等。
    现在我们用模拟数据，让你先理解 Agent 的循环逻辑。
    """
    # 模拟的知识库
    knowledge_base = {
        "北京天气": "北京今天晴，25°C，微风。明天多云转阴，22°C。",
        "python": "Python 是一种解释型、面向对象的高级编程语言，由 Guido van Rossum 于 1991 年发布。",
        "react agent": "ReAct（Reasoning + Acting）是一种让 LLM 交替进行推理和行动的 Agent 架构，由 Google DeepMind 在 2022 年提出。",
        "deepseek": "DeepSeek（深度求索）是一家中国 AI 公司，发布了 DeepSeek-V3 和 DeepSeek-R1 等开源大模型，API 兼容 OpenAI 格式。",
        "transformer": "Transformer 是 Google 在 2017 年提出的神经网络架构，基于自注意力机制（Self-Attention），是现代 LLM 的基础。",
        "故宫": "故宫位于北京中轴线中心，是中国明清两代的皇家宫殿，世界文化遗产。开放时间：8:30-17:00，周一闭馆。",
        "国家博物馆": "中国国家博物馆位于北京天安门广场东侧，是世界上单体建筑面积最大的博物馆，免费参观。",
    }

    # 模糊匹配
    query_lower = query.lower()
    for key, value in knowledge_base.items():
        if key.lower() in query_lower or query_lower in key.lower():
            return f"搜索结果（关于「{key}」）：{value}"

    return f"搜索结果（关于「{query}」）：未找到相关信息。这是一个模拟搜索工具，知识库有限。"


# ============================================================
# 工具 3：获取当前时间
# ============================================================
def get_current_time(_unused: str = "") -> str:
    """获取当前日期和时间。参数被忽略。"""
    now = datetime.datetime.now()
    return f"当前时间：{now.strftime('%Y年%m月%d日 %H:%M:%S')}，星期{['一','二','三','四','五','六','日'][now.weekday()]}"


# ============================================================
# 工具注册表 —— 告诉 Agent 有哪些工具可以用
# ============================================================
# 这就是 "function call" 的底层版本。
# 每个工具有三个要素：
#   1. name：工具的名字（LLM 用它来指定要调用哪个工具）
#   2. func：真正执行的 Python 函数
#   3. description：工具的说明（会被写进 prompt，告诉 LLM 这个工具能干什么）

TOOLS = {
    "calculator": {
        "func": calculator,
        "description": "数学计算器。输入一个数学表达式（如 '2+3*4' 或 'sqrt(16)'），返回计算结果。支持加减乘除、三角函数、开方、对数等。",
    },
    "search": {
        "func": search,
        "description": "网络搜索工具。输入一个搜索关键词，返回相关信息。可以用来查天气、百科知识、新闻等。",
    },
    "get_current_time": {
        "func": get_current_time,
        "description": "获取当前的日期和时间。不需要输入参数。",
    },
}


def execute_tool(tool_name: str, tool_input: str) -> str:
    """
    执行一个工具，返回结果字符串。
    如果工具不存在，返回错误信息。
    """
    if tool_name not in TOOLS:
        return f"❌ 未知工具：'{tool_name}'。可用的工具有：{', '.join(TOOLS.keys())}"

    try:
        result = TOOLS[tool_name]["func"](tool_input.strip())
        return str(result)
    except Exception as e:
        return f"❌ 工具执行失败：{e}"


def get_tools_description() -> str:
    """
    生成工具的文本描述，用来放进 system prompt。
    这是最原始也最灵活的 "function definition" 方式——
    比 OpenAI 的 function calling JSON Schema 更自由。
    """
    lines = []
    for name, info in TOOLS.items():
        lines.append(f"- **{name}**：{info['description']}")
    return "\n".join(lines)


# ============================================================
# 自测：如果你直接运行这个文件，会测试每个工具
# ============================================================
if __name__ == "__main__":
    print("🧪 测试工具：calculator")
    print("  2 + 3 * 4 =", calculator("2 + 3 * 4"))
    print("  sqrt(16) =", calculator("sqrt(16)"))

    print("\n🧪 测试工具：search")
    print("  北京天气 →", search("北京天气"))
    print("  OpenAI →", search("OpenAI"))

    print("\n🧪 测试工具：get_current_time")
    print("  ", get_current_time())

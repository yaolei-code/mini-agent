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
import json
import os
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ============================================================
# Coding Agent 的工作区配置
# ============================================================
# 默认把当前运行目录当成工作区。以后运行 agent 时，可以通过
# AGENT_WORKSPACE 指向一个 Java/Spring Boot 项目目录。
WORKSPACE_ROOT = Path(os.getenv("AGENT_WORKSPACE", os.getcwd())).resolve()

IGNORED_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "node_modules",
    "target",
    "dist",
    "build",
}

IGNORED_FILES = {
    ".env",
}

TEXT_FILE_SUFFIXES = {
    ".py",
    ".java",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".vue",
    ".html",
    ".css",
    ".scss",
    ".xml",
    ".json",
    ".yaml",
    ".yml",
    ".properties",
    ".md",
    ".txt",
    ".sql",
    ".gradle",
}


def _resolve_workspace_path(path_text: str) -> Path:
    """
    把 Agent 给出的路径转换成工作区内的绝对路径。
    这是 coding agent 的安全边界：工具只能读取 AGENT_WORKSPACE 里面的文件。
    """
    raw_path = path_text.strip() or "."
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = WORKSPACE_ROOT / candidate

    resolved = candidate.resolve()
    if resolved != WORKSPACE_ROOT and WORKSPACE_ROOT not in resolved.parents:
        raise ValueError(f"路径越界：{path_text}")
    return resolved


def _is_ignored(path: Path) -> bool:
    return path.name in IGNORED_FILES or any(part in IGNORED_DIRS for part in path.parts)


def _is_text_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_FILE_SUFFIXES or path.name in {
        "pom.xml",
        "package.json",
        "requirements.txt",
        ".gitignore",
    }


# ============================================================
# Coding 工具 1：列出文件
# ============================================================
def list_files(path_text: str = ".") -> str:
    """
    列出工作区中的文件和目录。
    输入相对路径，比如 "." 或 "src/main/java"。
    """
    try:
        root = _resolve_workspace_path(path_text)
        if not root.exists():
            return f"路径不存在：{path_text}"
        if root.is_file():
            return f"{root.relative_to(WORKSPACE_ROOT)}"

        lines = []
        for item in sorted(root.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
            if _is_ignored(item):
                continue
            rel = item.relative_to(WORKSPACE_ROOT)
            suffix = "/" if item.is_dir() else ""
            lines.append(f"{rel}{suffix}")

        if not lines:
            return f"{path_text} 目录为空，或只包含被忽略的文件。"
        return "工作区文件列表：\n" + "\n".join(lines)
    except Exception as e:
        return f"列出文件失败：{e}"


# ============================================================
# Coding 工具 2：读取文件
# ============================================================
def read_file(path_text: str) -> str:
    """
    读取工作区中的文本文件。
    输入相对路径，比如 "src/main/java/com/example/UserService.java"。
    """
    try:
        path = _resolve_workspace_path(path_text)
        if not path.exists():
            return f"文件不存在：{path_text}"
        if not path.is_file():
            return f"这不是文件：{path_text}"
        if _is_ignored(path):
            return f"拒绝读取被忽略目录中的文件：{path_text}"
        if not _is_text_file(path):
            return f"暂不读取非文本文件：{path_text}"

        content = path.read_text(encoding="utf-8", errors="replace")
        max_chars = 12000
        if len(content) > max_chars:
            content = content[:max_chars] + "\n\n[文件过长，已截断]"

        return f"文件：{path.relative_to(WORKSPACE_ROOT)}\n\n{content}"
    except Exception as e:
        return f"读取文件失败：{e}"


# ============================================================
# Coding 工具 3：搜索代码
# ============================================================
def search_code(query: str) -> str:
    """
    在工作区文本文件中搜索关键词。
    输入关键词，比如 "login"、"UserService"、"password"。
    """
    query = query.strip()
    if not query:
        return "搜索关键词不能为空。"

    matches = []
    max_matches = 50

    try:
        for path in WORKSPACE_ROOT.rglob("*"):
            if len(matches) >= max_matches:
                break
            if not path.is_file() or _is_ignored(path) or not _is_text_file(path):
                continue

            try:
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            except Exception:
                continue

            for line_no, line in enumerate(lines, start=1):
                if query.lower() in line.lower():
                    rel = path.relative_to(WORKSPACE_ROOT)
                    matches.append(f"{rel}:{line_no}: {line.strip()}")
                    if len(matches) >= max_matches:
                        break

        if not matches:
            return f"没有搜索到关键词：{query}"

        extra = "\n[结果过多，已截断]" if len(matches) >= max_matches else ""
        return "搜索结果：\n" + "\n".join(matches) + extra
    except Exception as e:
        return f"搜索代码失败：{e}"


# ============================================================
# Coding 工具 4：修改文件
# ============================================================
def _parse_json_input(input_text: str) -> dict:
    """
    解析工具的 JSON 输入。
    允许模型把 JSON 包在 ```json ... ``` 代码块里。
    """
    text = input_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return json.loads(text)


def apply_patch(input_text: str) -> str:
    """
    对工作区内的文本文件做安全替换。

    输入 JSON：
    {
      "file": "相对路径",
      "old_text": "要替换的原文",
      "new_text": "替换后的文本"
    }
    """
    try:
        data = _parse_json_input(input_text)
        file_path = data.get("file", "").strip()
        old_text = data.get("old_text", "")
        new_text = data.get("new_text", "")

        if not file_path:
            return "修改失败：缺少 file 字段。"
        if old_text == "":
            return "修改失败：old_text 不能为空。"

        path = _resolve_workspace_path(file_path)
        if not path.exists():
            return f"修改失败，文件不存在：{file_path}"
        if not path.is_file():
            return f"修改失败，这不是文件：{file_path}"
        if _is_ignored(path):
            return f"修改失败，拒绝修改被忽略或敏感文件：{file_path}"
        if not _is_text_file(path):
            return f"修改失败，暂不修改非文本文件：{file_path}"

        content = path.read_text(encoding="utf-8", errors="replace")
        count = content.count(old_text)
        if count == 0:
            return "修改失败：old_text 在文件中没有找到。请先 read_file 确认原文。"
        if count > 1:
            return f"修改失败：old_text 在文件中出现 {count} 次。请提供更长、更精确的上下文，避免误改。"

        updated = content.replace(old_text, new_text, 1)
        path.write_text(updated, encoding="utf-8")
        return f"修改成功：{path.relative_to(WORKSPACE_ROOT)}"
    except json.JSONDecodeError as e:
        return f"修改失败：Action Input 必须是 JSON。解析错误：{e}"
    except Exception as e:
        return f"修改失败：{e}"


# ============================================================
# Coding 工具 5：查看 Git diff
# ============================================================
def git_diff(path_text: str = "") -> str:
    """
    查看工作区 Git diff。
    输入可以为空，也可以是相对文件路径。
    """
    try:
        command = ["git", "diff", "--"]
        target = path_text.strip()
        if target:
            path = _resolve_workspace_path(target)
            command.append(str(path.relative_to(WORKSPACE_ROOT)))

        result = subprocess.run(
            command,
            cwd=str(WORKSPACE_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )

        if result.returncode != 0:
            message = result.stderr.strip() or result.stdout.strip()
            return f"查看 diff 失败：{message}"

        diff_text = result.stdout.strip()
        if not diff_text:
            return "当前没有未提交的 Git diff。"

        max_chars = 12000
        if len(diff_text) > max_chars:
            diff_text = diff_text[:max_chars] + "\n\n[diff 过长，已截断]"
        return "Git diff：\n" + diff_text
    except Exception as e:
        return f"查看 diff 失败：{e}"


# ============================================================
# Coding 工具 6：运行命令
# ============================================================
DANGEROUS_PATTERNS = [
    "rm -rf /",
    "rm -r /",
    "rm -fr /",
    "rm -rf ~",
    "rm -rf .",
    "find . -delete",
    "sudo ",
    "su ",
    ":(){ :|:& };:",
    "mkfs.",
    "dd if=",
    "> /dev/sda",
    "chmod 777 /",
    "chown -R /",
    "shutdown",
    "reboot",
    "halt",
    "poweroff",
    "systemctl poweroff",
]


def run_command(command: str) -> str:
    """
    在工作区目录中运行一个 shell 命令，返回 stdout 和 stderr。
    常用于运行测试（如 pytest、mvn test）、构建（如 npm run build）
    或版本控制命令（如 git status、git log）。
    """
    command = command.strip()
    if not command:
        return "运行命令失败：命令不能为空。"

    # 安全检查
    command_lower = command.lower()
    for pattern in DANGEROUS_PATTERNS:
        if pattern.lower() in command_lower:
            return f"运行命令失败：检测到危险操作（{pattern}），命令被拒绝。"

    try:
        result = subprocess.run(
            command,
            cwd=str(WORKSPACE_ROOT),
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )

        out = result.stdout.strip()
        err = result.stderr.strip()
        exit_code = result.returncode

        parts = []
        if out:
            max_out = 8000
            if len(out) > max_out:
                out = out[:max_out] + "\n\n[stdout 过长，已截断]"
            parts.append(f"[stdout]\n{out}")
        if err:
            max_err = 4000
            if len(err) > max_err:
                err = err[:max_err] + "\n\n[stderr 过长，已截断]"
            parts.append(f"[stderr]\n{err}")
        if not parts:
            parts.append("(无输出)")

        header = f"命令执行完成（exit code: {exit_code}）"
        return header + "\n" + "\n\n".join(parts)
    except subprocess.TimeoutExpired:
        return "运行命令失败：命令执行超时（60 秒）。"
    except Exception as e:
        return f"运行命令失败：{e}"


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
                return f"[错误] 不允许使用 '{name}'，只能使用数学运算"

        # 在安全的名字空间里执行
        result = eval(code, {"__builtins__": {}}, allowed_names)
        return f"计算结果：{result}"

    except ZeroDivisionError:
        return "[错误] 不能除以零"
    except Exception as e:
        return f"[错误] 计算出错：{e}"


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
    time_text = now.strftime("%Y-%m-%d %H:%M:%S")
    weekday = ["一", "二", "三", "四", "五", "六", "日"][now.weekday()]
    return f"当前时间：{time_text}，星期{weekday}"


# ============================================================
# 工具注册表 —— 告诉 Agent 有哪些工具可以用
# ============================================================
# 这就是 "function call" 的底层版本。
# 每个工具有三个要素：
#   1. name：工具的名字（LLM 用它来指定要调用哪个工具）
#   2. func：真正执行的 Python 函数
#   3. description：工具的说明（会被写进 prompt，告诉 LLM 这个工具能干什么）

TOOLS = {
    "list_files": {
        "func": list_files,
        "description": "列出代码工作区中的文件和目录。输入相对路径，如 '.'、'src'、'src/main/java'。这是理解项目结构的第一步。",
    },
    "read_file": {
        "func": read_file,
        "description": "读取代码工作区中的文本文件。输入相对文件路径，如 'pom.xml' 或 'src/main/java/com/example/UserService.java'。",
    },
    "search_code": {
        "func": search_code,
        "description": "在代码工作区中搜索关键词。输入关键词，如 'login'、'password'、'UserService'，返回匹配的文件、行号和代码行。",
    },
    "apply_patch": {
        "func": apply_patch,
        "description": "修改工作区中的文本文件。输入 JSON：{\"file\":\"相对路径\",\"old_text\":\"要替换的原文\",\"new_text\":\"替换后的文本\"}。old_text 必须在文件中只出现一次。修改前应先 read_file 确认内容。",
    },
    "git_diff": {
        "func": git_diff,
        "description": "查看当前未提交的 Git diff。输入可以为空，查看全部 diff；也可以输入相对文件路径，只查看某个文件的 diff。",
    },
    "run_command": {
        "func": run_command,
        "description": "在工作区目录中运行一个 shell 命令。输入完整命令，如 'pytest'、'mvn test'、'npm run build'、'git status'。禁止危险操作（如 rm -rf、sudo）。超时 60 秒。",
    },
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
        return f"[错误] 未知工具：'{tool_name}'。可用的工具有：{', '.join(TOOLS.keys())}"

    try:
        result = TOOLS[tool_name]["func"](tool_input.strip())
        return str(result)
    except Exception as e:
        return f"[错误] 工具执行失败：{e}"


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
    print("[TEST] list_files")
    print(list_files("."))

    print("\n[TEST] search_code")
    print(search_code("ReActAgent"))

    print("\n[TEST] read_file")
    print(read_file("main.py")[:500])

    print("\n[TEST] calculator")
    print("  2 + 3 * 4 =", calculator("2 + 3 * 4"))
    print("  sqrt(16) =", calculator("sqrt(16)"))

    print("\n[TEST] search")
    print("  北京天气 ->", search("北京天气"))
    print("  OpenAI ->", search("OpenAI"))

    print("\n[TEST] get_current_time")
    print("  ", get_current_time())

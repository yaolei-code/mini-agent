# 🤖 Mini ReAct Agent —— 从零手搓你的第一个 AI Agent

> 🎯 **目标**：用纯 Python + DeepSeek API，手写一个 ReAct Agent，理解 Agent 的底层原理。
>
> ⚡ **不做的事**：不使用 LangChain、AutoGPT、CrewAI 等任何 Agent 框架。
>
> 💡 **核心理念**：框架是别人写的，原理才是你的。理解了原理之后，任何框架都是一层窗户纸。

---

## 🧠 什么是 ReAct Agent？

**ReAct = Reasoning（推理）+ Acting（行动）**

普通的聊天 AI：你问 → 它答（一步到位）
ReAct Agent：你问 → 它思考 → 它行动 → 它观察结果 → 它再思考 → ... → 它回答

就像一个会"自言自语"的 AI：
```
💭 我需要先算 3×5...
🔧 调计算器：3*5=15
💭 结果是 15，接下来 15+2...
🔧 调计算器：15+2=17
💭 答案是 17，任务完成
✅ 3乘以5加2等于17
```

---

## 📁 项目结构

```
mini-agent/
├── .env.example      # API Key 模板（复制为 .env 后填入真实 key）
├── requirements.txt  # 依赖：openai, python-dotenv
├── tools.py          # 🔧 工具定义（计算器、搜索、时间）
├── agent.py          # 🧠 Agent 核心循环（★ 最重要的文件）
├── main.py           # 🚀 启动入口
└── README.md         # 📖 本文件
```

---

## 🧩 当前进度：Mini Coding Agent v1

这个项目已经从通用 ReAct Agent 迈出了第一步，开始升级为 **AI Coding Agent**。

当前版本是 **只读 Coding Agent**，它可以：

- `list_files`：查看代码项目结构
- `search_code`：搜索代码关键词
- `read_file`：读取关键源码文件

当前版本暂时不会修改文件。下一步会继续加入：

- `apply_patch`：用 patch 修改代码
- `run_command`：运行测试或构建命令
- `git_diff`：查看 agent 修改了哪些内容

---

## 🚀 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置 API Key
```bash
# 复制模板
cp .env.example .env

# 编辑 .env 文件，把 your-api-key-here 替换成你的 DeepSeek API Key
# 去 https://platform.deepseek.com 注册获取
```

### 3. 运行
```bash
python main.py
```

### 4. 试试这些问题
- "这个项目是什么结构？"
- "帮我找一下 ReActAgent 类在哪里"
- "搜索 password 相关代码，并告诉我可能的问题"

### 5. 分析其他代码项目
默认情况下，Agent 会分析当前目录。你也可以设置 `AGENT_WORKSPACE` 指向另一个项目：

```bash
set AGENT_WORKSPACE=E:\path\to\your\java-project
python main.py
```

---

## 📖 学习路径建议

### 第一步：跑通（10 分钟）
把代码跑通，观察 Agent 的每一步输出。**不要改代码**，先感受 ReAct 循环长什么样。

### 第二步：理解（30 分钟）
打开 `agent.py`，从头读到尾。每一行我都写了中文注释。
读完之后，回答这三个问题：
1. Agent 的 while 循环在什么时候结束？
2. messages 列表是干嘛的？为什么每次都要往里面加东西？
3. 如果 LLM 输出格式错了，Agent 怎么处理？

### 第三步：修改实验（1 小时）
- 把 `temperature` 从 0 改成 0.7，观察 Agent 的行为变化
- 在 `tools.py` 里加一个新工具（比如"翻译工具"或"随机数工具"）
- 修改 `SYSTEM_PROMPT`，让 Agent 用不同的语气说话

### 第四步：考自己（30 分钟）
关掉代码，拿出一张白纸，画出 ReAct Agent 的流程图。
如果你能画出来，说明你真的理解了。

---

## 🎓 从这个小项目出发，你还应该看什么？

| 方向 | 下一步学什么 |
|------|-------------|
| Agent 架构 | SWE-Agent 论文、OpenClaw 源码 |
| Function Call | OpenAI Function Calling 的 JSON Schema 格式 |
| Memory | 向量数据库（ChromaDB）、RAG、上下文压缩 |
| Multi-Agent | CrewAI、AutoGen、多 Agent 通信模式 |
| Agent 评估 | SWE-bench、Agent 的成功率和成本评估 |

---

## 📝 学习笔记模板

今天做了什么：
- 我理解了 / 还没理解的：

卡住的地方：

最让我兴奋的发现：

下一步想探索的：

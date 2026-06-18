# Mini Coding Agent

一个从零实现的本地 AI Coding Agent 学习项目。

当前项目使用 Python + DeepSeek API 实现 ReAct 循环，不依赖 LangChain、AutoGPT、CrewAI 等 Agent 框架。项目目标不是训练大模型，而是手写一个能让大模型调用工具、观察结果、继续推理的 Agent Runtime。

## 项目目标

这个项目用于学习和展示 AI Agent 的底层结构：

- 如何把用户任务交给大模型分析
- 如何让大模型输出可解析的 Action
- 如何注册和执行工具
- 如何把工具结果作为 Observation 回传给大模型
- 如何通过循环完成多步骤任务
- 如何逐步升级为可以阅读、修改、验证代码的 Coding Agent

## 当前能力

当前版本是 Mini Coding Agent v2，支持查看、搜索、读取和小范围修改文本文件。

Agent 可以使用这些代码工具：

- `list_files`：查看工作区文件结构
- `search_code`：搜索代码关键词
- `read_file`：读取指定源码文件
- `apply_patch`：用 old/new 文本替换方式修改文件
- `git_diff`：查看当前未提交的 Git diff

当前版本还不会执行测试命令。它适合用来理解代码仓库结构、定位关键文件、修改小范围文本内容，并通过 Git diff 检查修改结果。

## 工作流程

Agent 的核心流程如下：

```text
用户输入任务
-> agent.py 调用大模型
-> 大模型输出 Thought / Action / Action Input
-> agent.py 解析 Action
-> tools.py 执行对应工具
-> 工具结果作为 Observation 回到上下文
-> 循环继续，直到 Action 为 Finish
```

如果任务需要修改代码，推荐流程是：

```text
list_files
-> search_code
-> read_file
-> apply_patch
-> git_diff
-> Finish
```

示例：

```text
用户：这个项目是什么结构？

Thought: 我需要先查看项目根目录。
Action: list_files
Action Input: .

Observation: 工作区文件列表...

Thought: 我需要阅读 README 和入口文件。
Action: read_file
Action Input: README.md

Observation: 文件内容...

Action: Finish
Action Input: 项目结构总结...
```

## 项目结构

```text
mini-agent/
├── .env.example      # API Key 配置模板
├── .gitignore        # Git 忽略规则
├── requirements.txt  # Python 依赖
├── tools.py          # 工具层：文件列表、代码搜索、文件读取等
├── agent.py          # Agent 核心循环
├── main.py           # 命令行入口
└── README.md         # 项目说明
```

可以类比 Spring Boot 项目理解：

```text
Spring Boot: Controller -> Service -> Repository
AI Agent:   main.py    -> agent.py -> tools.py
```

- `main.py`：接收用户输入，相当于入口层
- `agent.py`：管理 ReAct 循环，相当于核心业务层
- `tools.py`：真正执行文件读取、搜索等动作，相当于工具/外部资源访问层

## 环境要求

推荐使用 Python 3.10 或更高版本。

如果系统默认 Python 太旧，可以使用一个新版本 Python 为本项目创建独立虚拟环境，避免影响学校旧项目。

## 快速开始

安装依赖：

```powershell
pip install -r requirements.txt
```

复制环境变量模板：

```powershell
copy .env.example .env
```

编辑 `.env`，填入 DeepSeek API Key：

```env
DEEPSEEK_API_KEY=你的真实 API Key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

运行：

```powershell
python main.py
```

如果你的系统 Python 版本太旧，可以临时使用 Codex 自带的 Python：

```powershell
& "C:\Users\29480\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" main.py
```

## 可以尝试的问题

```text
这个项目是什么结构？
```

```text
帮我找一下 ReActAgent 类在哪里
```

```text
搜索 search_code 相关代码，并解释它是怎么工作的
```

```text
把 README 里某一句话改得更简洁，然后查看 diff
```

## 分析其他项目

默认情况下，Agent 会分析当前目录。也可以设置 `AGENT_WORKSPACE` 指向另一个代码项目：

```powershell
$env:AGENT_WORKSPACE="E:\path\to\your\java-project"
python main.py
```

然后可以提问：

```text
帮我找一下登录逻辑在哪里
```

```text
搜索 password 相关代码，并告诉我可能的问题
```

## 下一步计划

当前已经支持：

- `apply_patch`：通过 patch 修改文件
- `git_diff`：查看 Agent 修改了哪些内容

后续会逐步加入：

- `run_command`：运行测试或构建命令
- 权限控制：限制危险命令和越界文件访问
- 执行轨迹记录：记录每一步工具调用、耗时、结果和失败原因

最终目标是实现一个可以辅助修复 Java/Spring Boot 项目简单问题的本地 Coding Agent。

## 学习重点

读这个项目时，重点理解三件事：

- 大模型不直接操作文件，它只输出要调用的工具和参数
- Python 程序负责解析 Action，并真正执行工具
- 工具返回的 Observation 会进入下一轮上下文，让模型继续推理

一句话总结：

```text
AI Agent = 大模型 + 工具 + 循环 + 状态
```

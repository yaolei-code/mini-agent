"""
main.py —— 启动你的第一个 AI Coding Agent！
==========================================
使用方法：
  1. 复制 .env.example 为 .env，填入你的 DeepSeek API Key
  2. pip install -r requirements.txt
  3. 可选：设置 AGENT_WORKSPACE 指向你想分析的代码项目
  4. python main.py
  5. 输入代码分析任务，看 Agent 一步步观察代码仓库！
"""

import sys

from agent import ReActAgent

if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    print("=" * 60)
    print("[Mini Coding Agent] 欢迎使用你的第一个 AI Coding Agent！")
    print("=" * 60)
    print()
    print("[能力] 我能帮你：")
    print("  - 查看项目结构（list_files 工具）")
    print("  - 搜索代码关键词（search_code 工具）")
    print("  - 读取关键源码文件（read_file 工具）")
    print("  - 分析代码问题并给出修改建议（当前阶段只读，不会改文件）")
    print()
    print("[示例] 试试这些问题：")
    print("  1. 这个项目是什么结构？")
    print("  2. 帮我找一下登录逻辑在哪里")
    print("  3. 搜索 password 相关代码，并告诉我可能的问题")
    print()
    print("[提示] 如果要分析别的项目，可以先设置 AGENT_WORKSPACE 环境变量。")
    print("输入 'quit' 或 'exit' 退出")
    print()

    # 创建 Agent（只创建一次，可以反复使用）
    agent = ReActAgent(verbose=True)

    # 交互循环
    while True:
        try:
            user_input = input("[YOU] 你：").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "q"):
            print("再见！")
            break

        # 运行 Agent
        print()
        answer = agent.run(user_input)
        print(f"\n[AGENT] Agent 最终回答：\n{answer}")
        print()


if __name__ == "__main__":
    main()

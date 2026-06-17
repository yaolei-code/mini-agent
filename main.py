"""
main.py —— 启动你的第一个 ReAct Agent！
==========================================
使用方法：
  1. 复制 .env.example 为 .env，填入你的 DeepSeek API Key
  2. pip install -r requirements.txt
  3. python main.py
  4. 输入问题，看 Agent 一步步思考和行动！
"""

from agent import ReActAgent


def main():
    print("=" * 60)
    print("🤖 欢迎使用你的第一个 ReAct Agent！")
    print("=" * 60)
    print()
    print("📌 我能帮你：")
    print("  - 数学计算（calculator 工具）")
    print("  - 查资料（search 工具——模拟的）")
    print("  - 查时间（get_current_time 工具）")
    print()
    print("💡 试试这些问题：")
    print("  1. 根号 16 加上 3 的平方等于多少？")
    print("  2. 北京今天天气怎么样？故宫什么时候开放？")
    print("  3. 现在几点了？Python 是谁发明的？")
    print()
    print("输入 'quit' 或 'exit' 退出")
    print()

    # 创建 Agent（只创建一次，可以反复使用）
    agent = ReActAgent(verbose=True)

    # 交互循环
    while True:
        try:
            user_input = input("👤 你：").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 再见！")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "q"):
            print("👋 再见！")
            break

        # 运行 Agent
        print()
        answer = agent.run(user_input)
        print(f"\n🤖 Agent 最终回答：\n{answer}")
        print()


if __name__ == "__main__":
    main()

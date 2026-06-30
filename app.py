"""
app.py -- Gradio web UI for Mini Coding Agent.

This file is only the presentation layer. The Agent runtime still lives in
agent.py, so the web demo and command-line demo share the same core logic.
"""

import html
import os
import socket
import time

os.environ.setdefault("NO_PROXY", "127.0.0.1,localhost")
os.environ.setdefault("no_proxy", "127.0.0.1,localhost")

import gradio as gr
from dotenv import load_dotenv

from agent import ReActAgent

load_dotenv()

DEFAULT_PORT = 7860
MAX_PORT = 7870


EXAMPLES = [
    "这个项目是什么结构？",
    "帮我找一下 ReActAgent 类在哪里",
    "搜索 run_command 相关代码，并解释它是怎么工作的",
    "运行 python -m py_compile tools.py agent.py main.py 检查语法",
]


def _shorten(text: str, max_chars: int = 900) -> str:
    text = text or ""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[内容较长，已截断]"


def _has_api_key() -> bool:
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    return bool(api_key and api_key != "your-api-key-here")


def _error_result(message: str):
    safe_message = html.escape(message).replace("\n", "<br>")
    return message, [], f"<p>{safe_message}</p>", "运行失败"


def _find_free_port(start_port: int = DEFAULT_PORT, max_port: int = MAX_PORT) -> int:
    for port in range(start_port, max_port + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise OSError(f"Cannot find empty port in range: {start_port}-{max_port}.")


def _get_server_port() -> int:
    port_text = os.getenv("GRADIO_SERVER_PORT", "").strip()
    if port_text:
        return int(port_text)
    return _find_free_port()


def _build_trace_rows(agent: ReActAgent) -> list[list[str]]:
    rows = []
    for step in agent.traces:
        rows.append([
            step.step_number,
            "成功" if step.success else "失败",
            step.action,
            _shorten(step.action_input, 160),
            f"{step.duration_ms:.0f} ms",
        ])
    return rows


def _build_trace_detail(agent: ReActAgent) -> str:
    if not agent.traces:
        return "<p>暂无执行步骤。</p>"

    blocks = []
    for step in agent.traces:
        status = "成功" if step.success else "失败"
        thought = html.escape(_shorten(step.thought, 500))
        action_input = html.escape(_shorten(step.action_input, 700))
        observation = html.escape(_shorten(step.observation, 1200))

        blocks.append(
            f"""
            <details class="trace-step" open>
              <summary>步骤 {step.step_number} · {html.escape(step.action)} · {status} · {step.duration_ms:.0f} ms</summary>
              <div class="trace-grid">
                <div>
                  <h4>Thought</h4>
                  <pre>{thought}</pre>
                </div>
                <div>
                  <h4>Action Input</h4>
                  <pre>{action_input}</pre>
                </div>
                <div>
                  <h4>Observation</h4>
                  <pre>{observation}</pre>
                </div>
              </div>
            </details>
            """
        )

    return "\n".join(blocks)


def run_agent(question: str, max_steps: int):
    question = (question or "").strip()
    if not question:
        return "请输入一个任务。", [], "<p>暂无执行步骤。</p>", "未运行"

    if not _has_api_key():
        return _error_result(
            "还没有配置 DeepSeek API Key。\n\n"
            "请复制 .env.example 为 .env，然后把 DEEPSEEK_API_KEY 改成你的真实 key。"
        )

    started_at = time.time()
    try:
        agent = ReActAgent(verbose=False)
        answer = agent.run(question, max_steps=max_steps)
    except Exception as exc:
        return _error_result(
            "Agent 运行失败。\n\n"
            f"错误信息：{exc}\n\n"
            "请检查 .env 配置、网络连接，以及当前项目依赖是否安装完整。"
        )
    total_ms = (time.time() - started_at) * 1000

    success_count = sum(1 for trace in agent.traces if trace.success)
    summary = (
        f"总步数：{len(agent.traces)} | "
        f"成功：{success_count} | "
        f"失败：{len(agent.traces) - success_count} | "
        f"总耗时：{total_ms:.0f} ms"
    )

    return answer, _build_trace_rows(agent), _build_trace_detail(agent), summary


CUSTOM_CSS = """
.gradio-container {
  max-width: 1180px !important;
}
.trace-step {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  margin: 10px 0;
  padding: 10px 12px;
  background: #ffffff;
}
.trace-step summary {
  cursor: pointer;
  font-weight: 700;
}
.trace-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 10px;
  margin-top: 10px;
}
.trace-grid h4 {
  margin: 4px 0;
}
.trace-grid pre {
  white-space: pre-wrap;
  word-break: break-word;
  background: #f8fafc;
  border-radius: 6px;
  padding: 10px;
  margin: 0;
}
"""


with gr.Blocks(title="Mini Coding Agent") as demo:
    gr.Markdown(
        """
        # Mini Coding Agent
        本地 ReAct Coding Agent 演示：输入任务后，网页会展示最终回答、工具调用步骤和每一步 Observation。
        """
    )

    with gr.Row():
        with gr.Column(scale=3):
            question_box = gr.Textbox(
                label="任务",
                placeholder="例如：这个项目是什么结构？",
                lines=4,
            )
        with gr.Column(scale=1):
            max_steps_slider = gr.Slider(
                minimum=1,
                maximum=12,
                value=6,
                step=1,
                label="最大步骤数",
            )
            run_button = gr.Button("运行 Agent", variant="primary")

    gr.Examples(
        examples=EXAMPLES,
        inputs=question_box,
        label="演示问题",
    )

    status_text = gr.Textbox(label="运行摘要", value="未运行", interactive=False)
    answer_box = gr.Textbox(label="最终回答", lines=8, interactive=False)

    trace_table = gr.Dataframe(
        headers=["步骤", "状态", "Action", "Action Input", "耗时"],
        datatype=["number", "str", "str", "str", "str"],
        label="步骤总览",
        interactive=False,
    )
    trace_detail = gr.HTML(label="步骤详情", value="<p>暂无执行步骤。</p>")

    run_button.click(
        fn=run_agent,
        inputs=[question_box, max_steps_slider],
        outputs=[answer_box, trace_table, trace_detail, status_text],
    )


if __name__ == "__main__":
    port = _get_server_port()
    print(f"Mini Coding Agent web UI: http://127.0.0.1:{port}")
    demo.launch(server_name="127.0.0.1", server_port=port, css=CUSTOM_CSS)

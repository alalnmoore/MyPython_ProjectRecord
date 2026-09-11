"""
三个节点函数 + StateGraph 构造 + State 定义，都在这一个文件里
"""
import os
import sys
from pathlib import Path
from typing import TypedDict

# 让 main.py 中的绝对导入可用（如果被当作脚本运行）
_PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(_PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(_PROJECT_DIR))

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.types import interrupt

load_dotenv()

llm = ChatOpenAI(
    model=os.getenv("QWEN_MODEL", "qwen-plus"),
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url=os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
    temperature=0,
)


# ===== State 定义（题目要求的字段）=====
class OverAllState(TypedDict, total=False):
    amount: float | None
    reason: str | None
    need_review: bool | None
    review_result: str | None
    process_status: str | None
    process_result: str | None


# ===== 三个节点 =====
def parse_expense(state: OverAllState) -> dict:
    """解析报销信息：调用 LLM 处理用户输入，设置 need_review"""
    amount = state["amount"]
    reason = state["reason"]

    # 用 ChatOpenAI 对用户输入做语义处理
    prompt = f"请确认以下报销申请并给出简短处理意见（不超过30字）：金额 {amount} 元，原因：{reason}"
    try:
        response = llm.invoke(prompt)
        # 查看当前对象response有没有这个content这个属性
        _hint = response.content if hasattr(response, "content") else str(response)
    except Exception as e:
        _hint = f"LLM 调用失败：{e}"

    need_review = amount is not None and amount > 1000
    return {
        "amount": amount,
        "reason": reason,
        "need_review": need_review,
    }


def wait_review(state: OverAllState) -> dict:
    """人工审批节点：第一次中断等待 resume"""
    amount = state["amount"]
    reason = state["reason"] or ""
    prompt = (
        f"该报销金额较高，需要人工审批。"
        f"金额：{amount}，原因：{reason}。"
        f"请输入 approved 或 rejected"
    )
    answer = interrupt(prompt)
    return {"review_result": answer}


def process_expense(state: OverAllState) -> dict:
    """生成最终处理结果"""
    need_review = bool(state.get("need_review"))
    amount = state.get("amount")
    reason = state.get("reason") or ""
    review_result = state.get("review_result")

    if not need_review:
        status = "AUTO_APPROVED"
        result = f"报销金额较低，系统自动审批通过，进入财务打款流程。金额：{amount}，原因：{reason}"
    elif review_result == "approved":
        status = "MANUAL_APPROVED"
        result = f"报销申请已通过人工审批，进入财务打款流程。金额：{amount}，原因：{reason}"
    else:
        status = "REJECTED"
        result = f"报销申请已被人工审批拒绝。金额：{amount}，原因：{reason}"

    return {
        "process_status": status,
        "process_result": result,
    }


# ===== 编排 graph =====
expense_graph = StateGraph(OverAllState)
expense_graph.add_node("parse_expense", parse_expense)
expense_graph.add_node("wait_review", wait_review)
expense_graph.add_node("process_expense", process_expense)

expense_graph.add_edge(START, "parse_expense")

expense_graph.add_conditional_edges(
    "parse_expense",
    lambda state: "wait_review" if state["need_review"] else "process_expense",
    {
        "wait_review": "wait_review",
        "process_expense": "process_expense",
    },
)

expense_graph.add_edge("wait_review", "process_expense")
expense_graph.add_edge("process_expense", END)

compiled_expense_graph = expense_graph.compile(checkpointer=MemorySaver())
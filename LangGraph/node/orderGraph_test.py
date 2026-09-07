# 这个简单的测试是有三个节点，receive_node,confirm_order，dispatch_order
from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.types import interrupt

from LangGraph.model.OrderState import OrderState


def receive_node(state:OrderState)->dict:
    # 首先获取用户传进来的信息
    message = state["raw_message"]
    # 这个暂时是一个示例数据，后续会用LLM来处理，进行一个萝卜一个坑按照状态字典的属性去进行添值！！！！
    return {"dish":"爆炒羊肚，牛肚","address":"土卫三上的一个陨石坑"}

def confirm_node(state:OrderState)->dict:
    prompt = f"您的订单:{state['raw_message']},配送的地址是:{state['address']},请问你这个傻逼确认要下单吗? (yes/no)"
    # 发生了中断
    answer = interrupt(prompt)
    return {"confirmed":answer.strip().low in ("yes","是的","是","没错")}

def dispatch_order(state:OrderState)->dict:
    return {"dispatch_result":f"您的订单已经送达了:{state["address"]},卧槽累死你爹了！！玛德"}


order_graph = StateGraph(OrderState)
# 添加节点:
order_graph.add_node("receive_node",receive_node)
order_graph.add_node("confirm_node",confirm_node)
order_graph.add_node("dispatch_order",dispatch_order)

# 添加边
order_graph.add_edge(START,"receive_node")
order_graph.add_edge("receive_node","confirm_node")
# 添加条件边
order_graph.add_conditional_edges("confirm_node",
                                  lambda state:"dispatch" if state["confirmed"]==True else "cancel",
                      {
                                    "cancel":END,
                                    "dispatch":"dispatch_order"
                              })
order_graph.add_edge("dispatch_order",END)

# 编译图
compiled_order_graph = order_graph.compile(checkpointer=MemorySaver())



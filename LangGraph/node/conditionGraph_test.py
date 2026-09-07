from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.types import interrupt, Command

from LangGraph.model.StyleChatState import StyleChatState


# 定义emotion分析节点
def analyze_emotion_nod(state:StyleChatState)->dict:
    if "难过" in str(state["user_input"]) or "伤心" in str(state["user_input"]):
        return {"emotion":"sad"}
    return {"emotion":"normal"}
# 定义中断节点
def ask_style_node(state:StyleChatState)->dict:
    answer = interrupt("你希望的回答是温柔:gentle，还是直接:direct一点？？？")
    return {"reply_style":answer}

# 根据用户回复的style选择回复的语气
def generate_reply_node(state:StyleChatState)->dict:
    if str(state["emotion"])=="sad" and str(state["reply_style"])=="gentle":
        reply = "我的宝贝乖，不哭不哭，不闹不闹，我帮你解决滴~~~"
    elif str(state["emotion"])=="sad" and str(state["reply_style"])=="direct":
        reply = "操你妈的，滚蛋，一边凉快一边呆着去，草泥马的，你自己解决，傻逼！！！"
    else:
        reply = "好的，祝你以后一直保持这个心情！！"
    return {"reply":reply}

# 定义测试的方法
def interrupt_graph_test():
    graph_builder = StateGraph(StyleChatState)
    # 添加边
    graph_builder.add_node("analyze_emotion_nod",analyze_emotion_nod)
    graph_builder.add_node("ask_style_node",ask_style_node)
    graph_builder.add_node("generate_reply_node",generate_reply_node)
    # 添加边
    graph_builder.add_edge(START,"analyze_emotion_nod")
    graph_builder.add_edge("analyze_emotion_nod","ask_style_node")
    graph_builder.add_edge("ask_style_node","generate_reply_node")
    graph_builder.add_edge("generate_reply_node",END)

    # 编译图
    builder_compiled_graph = graph_builder.compile(checkpointer=MemorySaver())
    config = {"configurable":{"thread_id":"cskaoyan001"}}
    input_dict = {"user_input":"我他妈今天有点难过，靠了！！"}
    result = builder_compiled_graph.invoke(input_dict,config)
    print(result)
    print("*" * 300)
    print("*" * 300)
    # 进行图的第二次回复执行
    second_result = builder_compiled_graph.invoke(Command(resume="direct"), config)
    print(second_result)


if __name__ == "__main__":
    interrupt_graph_test()





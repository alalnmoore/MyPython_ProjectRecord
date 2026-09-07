from langgraph.constants import START, END
from langgraph.graph import StateGraph

from LangGraph.model.ChatState import ChatState
# 定义节点
def analyze_emotion_node(state:ChatState):
    # 从state中按照键取出input的内容
    user_input = state["user_input"]
    if "难过" in user_input or "伤心" in user_input:
        emotion = "sad"
    else:
        emotion = "normal"
    return {"emotion":emotion}

def generate_reply_node(state:ChatState):
    # 从state中取出键所对应的值来进行判断
    if state["emotion"]=="sad":
        reply = "听起来你今天有些低落，先别急着否定自己，我愿意听你慢慢说。"
    else:
        reply = "收到，我会继续陪你聊下去。"
    return {"reply":reply}

# 开始对节点进行测试
def simple_test():
    # 创建节点图对象
    graph = StateGraph(ChatState)
    # 添加节点
    graph.add_node("analyze_emotion_node",analyze_emotion_node)
    graph.add_node("generate_reply_node",generate_reply_node)

    # 添加边
    graph.add_edge(START,"analyze_emotion_node")
    graph.add_edge("analyze_emotion_node","generate_reply_node")
    graph.add_edge("generate_reply_node",END)

    # 编译图
    compiled_graph = graph.compile()
    # 非流式响应
    # result = compiled_graph.invoke({"user_input": "我靠了，我今天感觉有点伤心！！！"})
    # print(result)
    # 流式响应
    for response in compiled_graph.stream({"user_input":"我他妈今天有点难过！！！"}):
        print(response)


if __name__ == "__main__":
    simple_test()




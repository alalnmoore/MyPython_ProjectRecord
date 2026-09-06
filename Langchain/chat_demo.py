from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from Langchain.tools import get_weather_message
import os


def user_message():
    ai_llm = ChatOpenAI(base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                    api_key=os.getenv("Alibaba_Key"),
                    model="qwen-plus")
    response = ai_llm.invoke("你是傻逼！！！！")
    content = response.content
    print(content)

# 添加提示词模板
def user_template_message():
    ai_llm = ChatOpenAI(base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                        api_key=os.getenv("Alibaba_Key"),
                        model="qwen-plus")
    prompt = ChatPromptTemplate.from_messages([
        ("system","你是一个热心的温柔的斯坦福数学女教师，你要耐心温柔的回答学生咨询的数学问题"),
        ("user","{question}")
    ])
    response = prompt.invoke({"question": "什么是挂谷猜想？"})
    # 再交给llm去回答
    invoke_response = ai_llm.invoke(response)
    content = invoke_response.content
    print(content)


def user_template_message_another():
    ai_llm = ChatOpenAI(
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key=os.getenv("Alibaba_Key"),
        model="qwen-plus"
    )

    # ✅ 正确的写法：列表包含 SystemMessage 和 HumanMessage 对象
    messages = [
        SystemMessage(content="你是一位专业的客服助手，请耐心、礼貌地回答用户问题。"),
        HumanMessage(content="你好啊！！")
    ]
    # 直接传入消息列表
    response = ai_llm.invoke(messages)
    print(response.content)

# 工具调用的示例
def tools_llm_call():
    ai_llm = ChatOpenAI(
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key=os.getenv("Alibaba_Key"),
        model="qwen-plus"
    )

    # 告诉大模型，你有这些工具可以调用！！
    llm_with_tools = ai_llm.bind_tools([get_weather_message])
    message = [(HumanMessage(content="北京的天气如何？？"))]
    # 这个大模型返回工具要执行的动作，也就是说，大模型将参数传给工具，委托工具去帮我执行，执行完后将结果给我！！
    response = llm_with_tools.invoke(message)
    print(response.tool_calls)
    message.append(response)
    for tool_call in response.tool_calls:
        # 取出工具的名称以及参数
        tool_name = tool_call["name"]
        tool_value = tool_call["args"]
        if tool_name == "get_weather":
            # 工具执行方法
            tool_result = get_weather_message.invoke(tool_value)
            message.append(ToolMessage(content=tool_result,tool_call_id = tool_call["id"]))
            # 最后经过大模型的审阅最终输出
            final_result = llm_with_tools.invoke(message)
            content = final_result.content
            print(content)


# main方法运行
if __name__ == "__main__":
    # user_message()
    # 运行有提示词模板的方法
    # user_template_message()
    # user_template_message_another()
    tools_llm_call()


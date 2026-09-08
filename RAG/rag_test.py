import os

from langchain_chroma import Chroma
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_community.document_loaders import TextLoader
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter


def rag_build_test():
    loader = TextLoader("doc/员工请假管理制度.md", encoding="utf-8")
    # 转换为document对象
    documents = loader.load()
    # 文档的切分
    spliter = RecursiveCharacterTextSplitter(
        chunk_size=200,
        chunk_overlap=30,
        separators=["\n\n", "\n", "。", "；", "，", ""])
    split_documents = spliter.split_documents(documents)
    print(split_documents)
    # 被切成了多个document对象个数
    print(split_documents.__len__())

    embedding = OpenAIEmbeddings(
        model="text-embedding-v4",
        api_key=os.getenv("Alibaba_Key"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        check_embedding_ctx_length=False  # 解决云百炼平台的embedding模型兼容性问题
    )
  # 实现向量转化，以及向量的保存
    Chroma.from_documents(
        documents=split_documents,
        embedding=embedding,
        collection_name="leave_policy",
        host="192.168.74.100",
        port=8000,
    )


def retrieve():
    # 创建出实现向量化的embedding对象
    embedding = OpenAIEmbeddings(
        model="text-embedding-v4",
        api_key=os.getenv("Alibaba_Key"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        check_embedding_ctx_length=False  # 解决云百炼平台的embedding模型兼容性问题
    )
    # 创建用于检索的chroma对象
    vector_store = Chroma(
        collection_name="leave_policy",
        embedding_function=embedding,
        host="192.168.74.100",
        port=8000
    )

    # 进行问题的检索
    # search = vector_store.similarity_search("事假一年最多能请多少天？", k=2)
    # 第二种方式是用retriever方式进行检索
    retriever = vector_store.as_retriever(search_kwargs={"k": 2})
    search = retriever.invoke("事假一周最多能请多少天？")
    # for doc in search:
    #     print(doc.page_content)
    #     print("==" * 200)
    print(doc_format(search))

#定义一个生成其函数用于规范化文档的内容,其中形参docs是一个列表,doc是列表中的每一个对象元素
def doc_format(docs)->str:
    return "\n\n".join(doc.page_content for doc in docs)

# 大模型进行阅读检索后的文章进行判断
def documents_inject():
    # 创建出实现向量化的embedding对象
    embedding = OpenAIEmbeddings(
        model="text-embedding-v4",
        api_key=os.getenv("Alibaba_Key"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        check_embedding_ctx_length=False  # 解决云百炼平台的embedding模型兼容性问题
    )

    # 创建用于检索的chroma对象
    vector_store = Chroma(
        collection_name="leave_policy",
        embedding_function=embedding,
        host="192.168.74.100",
        port=8000
    )

    llm = ChatOpenAI(base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                     api_key=os.getenv("Alibaba_Key"),
                     model="qwen-plus")
    # 设置回复的模板
    prompt = ChatPromptTemplate.from_messages(
     [
    ("system", """你是公司HR助手，请严格根据下面提供的制度内容回答员工问题。
    如果制度内容里没有相关规定，就如实说"制度中未提及"，不要编造。
    制度内容：{context}"""),
    ("human", "{question}"),
    ])
    # 进行问题的检索
    retriever = vector_store.as_retriever(search_kwargs={"k": 2})
    docs = retriever.invoke("丧假有几种类型,分别可以请多少天假？？")
    # 构造链
    chain = prompt | llm | StrOutputParser()
    llm_response = chain.invoke({"question": "丧假有几种类型,分别可以请多少天假？？", "context": doc_format(docs)})
    print(llm_response)


# 构造一个自动装配question,context的方法
def auto_retrieve_and_inject():
    # 创建出实现向量化的embedding对象
    embedding = OpenAIEmbeddings(
        model="text-embedding-v4",
        api_key=os.getenv("Alibaba_Key"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        check_embedding_ctx_length=False  # 解决云百炼平台的embedding模型兼容性问题
    )

    # 创建用于检索的chroma对象
    vector_store = Chroma(
        collection_name="leave_policy",
        embedding_function=embedding,
        host="192.168.74.100",
        port=8000
    )

    # 将检索出的知识，填充到提示词模版
    # 提示词：检索到的内容放进 {context}，用户问题放进 {question}
    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是公司HR助手，请严格根据下面提供的制度内容回答员工问题。
    如果制度内容里没有相关规定，就如实说"制度中未提及"，不要编造。
    制度内容：
    {context}"""),("human", "{question}")])

    # 实现与模型的交互
    llm = ChatOpenAI(base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                     api_key=os.getenv("Alibaba_Key"),
                     model="qwen-plus" )
    retriever = vector_store.as_retriever(search_kwargs={"k": 2})
    # 这个就是将大模型，提示词模板，以及根据问题检索出来的内容统一用大模型来进行处理，然后输出内容
    doc_chain =create_stuff_documents_chain(llm,prompt,document_variable_name="context")
    # 将用户所问的问题，用来进行检索，提取出其中的"question"这个键
    retrieve_chain =RunnableLambda(lambda value: value["question"]) | retriever
    # 将检索出来的context内容，作为键添加到字典中
    final_chain = RunnablePassthrough.assign(context = retrieve_chain) | doc_chain
    # 最后是运行，提取用户所问的信息
    result = final_chain.invoke({"question": "丧假有几种类型,分别可以请多少天假？？"})
    print(result)


if __name__ == "__main__":
    # rag_build_test()
    # retrieve()
    # documents_inject()
    auto_retrieve_and_inject()
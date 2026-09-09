import uvicorn
from fastapi import FastAPI
from langchain_chroma import Chroma
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_community.document_loaders import TextLoader
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os

from RAG.补9月7号作业.model.RagSearchRequest import RagSearchRequest
from RAG.补9月7号作业.model.RagSearchResponse import RagSearchResponse

app = FastAPI()
# 构建向量数据库接口
@app.post("/api/rag/build")
def rag_build():
    # 是当前文件夹下的相对路径！但是不用写当前文件夹的名字
    loader = TextLoader("作业文档素材/新生图书馆咨询助手.md", encoding="utf-8")
    # 转换为document对象
    documents = loader.load()
    # 文档的切分
    spliter = RecursiveCharacterTextSplitter(
        chunk_size=200,
        chunk_overlap=30,
        separators=["\n\n", "\n", "。", "；", "，", ""])
    split_documents = spliter.split_documents(documents)

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
        collection_name="library_policy",
        host="192.168.74.100",
        port=8000,
    )
    return {
    "message": "图书馆知识库创建完毕",
    "chunkCount": split_documents.__len__()
    }
# 检索问答接口
@app.post("/api/rag/search")
def rag_search(req:RagSearchRequest):
    embedding = OpenAIEmbeddings(
        model="text-embedding-v4",
        api_key=os.getenv("Alibaba_Key"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        check_embedding_ctx_length=False  # 解决云百炼平台的embedding模型兼容性问题
    )

    # 创建用于检索的chroma对象
    vector_store = Chroma(
        collection_name="library_policy",
        embedding_function=embedding,
        host="192.168.74.100",
        port=8000
    )
    llm = ChatOpenAI(base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                     api_key=os.getenv("Alibaba_Key"),
                     model="qwen-plus")
    # 提示词模板
    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是星河大学图书馆的新生咨询助手。
    请严格根据下面提供的图书馆服务文档回答问题。
    如果文档中没有相关规定，就回答“图书馆服务文档中未提及”，不要编造。
    图书馆服务文档：
    {context}"""),("human", "{query}"),])

    retriever = vector_store.as_retriever(search_kwargs={"k": 2})
    # 这个就是将大模型，提示词模板，以及根据问题检索出来的内容统一用大模型来进行处理，然后输出内容
    doc_chain = create_stuff_documents_chain(llm, prompt, document_variable_name="context")
    # 将用户所问的问题，用来进行检索，提取出其中的"question"这个键
    retrieve_chain = RunnableLambda(lambda value: value["query"]) | retriever
    # 将检索出来的context内容，作为键添加到字典中
    final_chain = RunnablePassthrough.assign(context=retrieve_chain) | doc_chain
    # 最后是运行，提取用户所问的信息
    result = final_chain.invoke({"query": req.query})
    return RagSearchResponse(query=req.query,answer=result)


if __name__ == "__main__":
    print("🚀 启动 FastAPI 服务...")
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=9999,
        log_level="info"  # 显示详细日志
    )
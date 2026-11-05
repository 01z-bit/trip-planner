import os
from typing import Annotated, TypedDict
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from app.agents.tools import get_weather, search_poi

load_dotenv()

# 1. 初始化大模型
llm = ChatOpenAI(
    model="glm-4-flash",
    api_key=os.getenv("ZHIPUAI_API_KEY"),
    base_url=os.getenv("ZHIPUAI_BASE_URL"),
    temperature=0.7
)

# 把工具绑定给大模型，让它知道自己有哪些武器
tools = [get_weather, search_poi]
llm_with_tools = llm.bind_tools(tools)

# 2. 定义状态（State）：用来在节点之间传递消息
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

# 3. 定义节点（Nodes）
def chatbot(state: AgentState):
    """大模型节点：负责思考并决定是否要调用工具"""
    return {"messages": [llm_with_tools.invoke(state["messages"])]}

# 工具节点：LangGraph 内置的，会自动执行大模型指定的工具
tool_node = ToolNode(tools=tools)

# 4. 构建图（Graph）
builder = StateGraph(AgentState)

# 添加节点
builder.add_node("chatbot", chatbot)
builder.add_node("tools", tool_node)

# 设置入口：从 chatbot 开始
builder.add_edge(START, "chatbot")

# 核心逻辑：条件边（Conditional Edge）
# 它会检查 chatbot 的回复，如果里面包含了工具调用（tool_calls），就去 "tools" 节点；
# 如果没有，说明思考结束了，直接去 END。
builder.add_conditional_edges(
    "chatbot",
    tools_condition,
)

# 工具执行完之后，必须把结果还给 chatbot，让它做最终总结
builder.add_edge("tools", "chatbot")

# 编译成可运行的图
graph = builder.compile()
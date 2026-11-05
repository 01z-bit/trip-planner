import os
import json
from typing import TypedDict, Annotated
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from app.agents.tools import get_weather, search_poi

load_dotenv()

llm = ChatOpenAI(
    model="glm-4-flash",
    api_key=os.getenv("ZHIPUAI_API_KEY"),
    base_url=os.getenv("ZHIPUAI_BASE_URL"),
    temperature=0.7
)

tools = [get_weather, search_poi]
llm_with_tools = llm.bind_tools(tools)

class TripState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    origin: str
    destination: str
    start_date: str
    end_date: str
    budget: str
    next_agent: str
    research_data: str
    draft_plan: str
    review_feedback: str
    review_passed: bool
    retry_count: int  # 👈 新增：用来记录被打回的次数

def supervisor_node(state: TripState):
    # 👈 核心修复：如果被打回了 2 次，不管合不合格，直接强行结束，防止死循环！
    if state.get("retry_count", 0) >= 2 and state.get("draft_plan"):
        return {"next_agent": "FINISH"}

    if not state.get("research_data"):
        return {"next_agent": "Researcher"}
    elif not state.get("draft_plan"):
        return {"next_agent": "Planner"}
    elif not state.get("review_passed"):
        if state.get("review_feedback"):
            return {"next_agent": "Planner"}
        else:
            return {"next_agent": "Auditor"}
    else:
        return {"next_agent": "FINISH"}

def researcher_node(state: TripState):
    prompt = f"""你是一个旅游情报专家。请使用你的工具查一下：
1. 从{state['origin']}到{state['destination']}的交通方式。
2. {state['destination']}的近期天气。
3. {state['destination']}的特色景点。
请把查到的真实信息整理好输出。"""
    
    response = llm_with_tools.invoke([HumanMessage(content=prompt)])
    return {"messages": [response]}

def collect_research_node(state: TripState):
    latest_msg = state["messages"][-1].content
    return {"research_data": latest_msg, "messages": [AIMessage(content="情报收集完毕！")]}

def planner_node(state: TripState):
    feedback = state.get("review_feedback", "")
    feedback_prompt = f"\n注意！上次审核员提了意见，请务必修改：{feedback}" if feedback else ""
    
    prompt = f"""你是一个资深旅游规划师。请根据以下信息排一份行程：
出发地：{state['origin']}
目的地：{state['destination']}
时间：{state['start_date']} 至 {state['end_date']}
预算：{state['budget']}元

以下是情报官查到的真实数据：
{state['research_data']}
{feedback_prompt}

【强制要求】必须考虑从{state['origin']}到{state['destination']}的往返交通费用，并在行程中体现！
必须输出纯 JSON 格式，不能有 markdown 标记：
{{
  "summary": "一句话总结",
  "daily_plans": [
    {{"day": "第一天", "morning": "安排", "afternoon": "安排", "evening": "安排"}}
  ]
}}"""
    
    response = llm.invoke([HumanMessage(content=prompt)])
    return {"draft_plan": response.content, "review_feedback": ""}

def auditor_node(state: TripState):
    prompt = f"""你是一个严格的财务和行程审核员。
用户的出发地是：{state['origin']}，目的地是：{state['destination']}。
用户的预算上限是：{state['budget']}元。
以下是规划师写的行程草案：
{state['draft_plan']}

请严格审核：
1. 预算是否超标（千万不要忽略往返大交通费用）？
2. 安排是否太赶或不符合实际？
如果完全合理，直接输出 "PASS"。
如果不合理，请输出具体的修改意见。"""
    
    response = llm.invoke([HumanMessage(content=prompt)])
    
    # 👈 修复：忽略大小写匹配，防止大模型输出 "Pass" 导致匹配失败
    if "PASS" in response.content.upper():
        return {"review_passed": True, "messages": [AIMessage(content="审核员：行程合格，准予通过！")]}
    else:
        return {
            "review_feedback": response.content, 
            "review_passed": False, 
            "retry_count": state.get("retry_count", 0) + 1, # 👈 失败次数+1
            "messages": [AIMessage(content=f"审核员打回修改：{response.content}")]
        }

builder = StateGraph(TripState)

builder.add_node("Supervisor", supervisor_node)
builder.add_node("Researcher", researcher_node)
builder.add_node("Tools", ToolNode(tools=tools))
builder.add_node("CollectResearch", collect_research_node)
builder.add_node("Planner", planner_node)
builder.add_node("Auditor", auditor_node)

builder.add_edge(START, "Supervisor")

def route_supervisor(state: TripState):
    if state["next_agent"] == "FINISH":
        return END
    return state["next_agent"]

builder.add_conditional_edges("Supervisor", route_supervisor, {"Researcher": "Researcher", "Planner": "Planner", "Auditor": "Auditor", END: END})

def route_researcher(state: TripState):
    if state["messages"][-1].tool_calls:
        return "Tools"
    return "CollectResearch"

builder.add_conditional_edges("Researcher", route_researcher, {"Tools": "Tools", "CollectResearch": "CollectResearch"})
builder.add_edge("Tools", "CollectResearch")
builder.add_edge("CollectResearch", "Supervisor")
builder.add_edge("Planner", "Supervisor")
builder.add_edge("Auditor", "Supervisor")

graph = builder.compile()
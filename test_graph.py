import asyncio
from langchain_core.messages import HumanMessage
from app.agents.graph import graph

async def main():
    # 咱们问一个需要查真实数据的问题
    user_query = "我下周想去杭州玩，查一下杭州未来三天的天气，另外帮我找一下西湖附近有哪些景点，给我列出来。"
    print(f"👤 用户提问：{user_query}\n")
    print("🤖 Agent 正在思考和调用工具，请稍候...\n")

    # 调用咱们编译好的图，传入用户消息
    inputs = {"messages": [HumanMessage(content=user_query)]}
    
    # astream 可以让我们看到 Agent 每一步的思考过程
    async for event in graph.astream(inputs):
        for node_name, node_output in event.items():
            print(f"--- 节点: {node_name} ---")
            if "messages" in node_output:
                # 打印大模型或工具的输出
                for msg in node_output["messages"]:
                    msg.pretty_print()
            print("\n")

if __name__ == "__main__":
    asyncio.run(main())
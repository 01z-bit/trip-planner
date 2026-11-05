import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# 1. 加载 .env
load_dotenv()

# 打印出来确认一下
print("✅ 成功读取到 Key:", os.getenv("ZHIPUAI_API_KEY")[:10] + "...") 

# 2. 初始化大模型
llm = ChatOpenAI(
    model="glm-4-flash", 
    api_key=os.getenv("ZHIPUAI_API_KEY"), 
    base_url=os.getenv("ZHIPUAI_BASE_URL"),
    temperature=0.7,
    max_tokens=200
)

print("正在向智谱AI发送请求，请稍候...\n")

try:
    # 3. 发送消息
    response = llm.invoke("你好，你是一个专业的旅游规划师，请用一句话简短地向我打个招呼。")
    
    # 4. 打印回复
    print("🤖 AI 回复：")
    print(response.content)

except Exception as e:
    print(f"\n❌ 请求失败，错误原因：{e}")
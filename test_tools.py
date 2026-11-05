import asyncio
from app.agents.tools import get_weather, search_poi

async def main():
    print("测试查天气...")
    # 注意：用 .ainvoke 调用 @tool 装饰的异步函数
    weather = await get_weather.ainvoke("杭州")
    print(weather)
    
    print("\n测试搜景点...")
    pois = await search_poi.ainvoke({"keywords": "西湖", "city": "杭州"})
    print(pois)

if __name__ == "__main__":
    asyncio.run(main())
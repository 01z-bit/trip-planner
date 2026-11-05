import os
import httpx
from langchain_core.tools import tool
from dotenv import load_dotenv

load_dotenv()

AMAP_KEY = os.getenv("AMAP_API_KEY")

@tool
async def get_weather(city: str) -> str:
    """查询指定城市的实时天气和未来天气预报。输入参数为城市名称，例如：杭州、北京。"""
    url = f"https://restapi.amap.com/v3/weather/weatherInfo?key={AMAP_KEY}&city={city}&extensions=all"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        data = resp.json()
        
        if data.get("status") != "1":
            return f"查询天气失败：{data.get('info')}"
            
        forecasts = data.get("forecasts", [])
        if not forecasts:
            return "未查到该城市的天气信息。"
            
        result = f"【{city}天气】\n"
        for day in forecasts[0].get("casts", [])[:3]: # 只取未来3天
            result += f"日期：{day['date']}，白天天气：{day['dayweather']}，夜间天气：{day['nightweather']}，气温：{day['nighttemp']}~{day['daytemp']}℃\n"
        return result

@tool
async def search_poi(keywords: str, city: str) -> str:
    """根据关键词搜索指定城市的景点、餐厅或酒店。输入参数为：搜索关键词（如：西湖、五星级酒店）和城市名称（如：杭州）。"""
    url = f"https://restapi.amap.com/v3/place/text?key={AMAP_KEY}&keywords={keywords}&city={city}&citylimit=true&offset=5&page=1&extensions=base"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        data = resp.json()
        
        if data.get("status") != "1":
            return f"搜索地点失败：{data.get('info')}"
            
        pois = data.get("pois", [])
        if not pois:
            return f"在{city}没有找到关于'{keywords}'的地点。"
            
        result = f"【{city}关于'{keywords}'的搜索结果】\n"
        for poi in pois:
            result += f"- {poi['name']}：地址是{poi['address']}（类型：{poi.get('type', '未知')}）\n"
        return result
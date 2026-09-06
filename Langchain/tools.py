from langchain_core import tools
from langchain_core.tools import tool
from pydantic import BaseModel, Field


class GetWeatherArgs(BaseModel):
    city:str = Field(description="城市名称，例如：北京、上海")
@tool("get_weather",args_schema=GetWeatherArgs)
def get_weather_message(city:str)->str:
    """查询指定城市的实时天气。当用户询问某个城市的天气时调用。"""
    demo_city_data={
        "北京": "晴，22°C，东南风3级",
        "上海": "多云，25°C，无风",
        "杭州": "小雨，20°C，南风2级"
    }
    # 调用的字典的get方法:dict.get(key,default)
    return demo_city_data.get(city,f"{city}没有相关天气信息")



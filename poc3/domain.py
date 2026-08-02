from typing import Literal


MaterialCategory = Literal[
    "crude_oil",
    "food_price_index",
    "surface_weather",
]
MATERIAL_CATEGORIES: tuple[MaterialCategory, ...] = (
    "crude_oil",
    "food_price_index",
    "surface_weather",
)

SearchTimeLimit = Literal["d", "w", "m", "y"]
WebSearchProvider = Literal["tavily", "ddgs"]
TavilySearchDepth = Literal["basic", "advanced", "fast", "ultra-fast"]
TavilySearchTopic = Literal["general", "news", "finance"]

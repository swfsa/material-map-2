from typing import Literal


MaterialCategory = Literal[
    "crude_oil",
    "diesel",
    "food_price_index",
    "gasoline",
    "natural_gas",
    "natural_gas_storage",
    "natural_gas_storage_nonsalt",
    "natural_gas_storage_salt",
    "surface_weather",
]
MATERIAL_CATEGORIES: tuple[MaterialCategory, ...] = (
    "crude_oil",
    "diesel",
    "food_price_index",
    "gasoline",
    "natural_gas",
    "natural_gas_storage",
    "natural_gas_storage_nonsalt",
    "natural_gas_storage_salt",
    "surface_weather",
)

SearchTimeLimit = Literal["d", "w", "m", "y"]
WebSearchProvider = Literal["tavily", "ddgs"]
TavilySearchDepth = Literal["basic", "advanced", "fast", "ultra-fast"]
TavilySearchTopic = Literal["general", "news", "finance"]

from dataclasses import dataclass

from .repository import MaterialQueryRepository
from .search_models import WebSearchClient


@dataclass
class AppDeps:
    material_repo: MaterialQueryRepository
    web_search_client: WebSearchClient

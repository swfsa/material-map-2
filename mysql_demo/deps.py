from dataclasses import dataclass

from repository import MaterialRepository



@dataclass
class AppDeps:

    material_repo:MaterialRepository
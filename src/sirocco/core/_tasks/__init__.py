# - ML - Maybe his behavior is too user-oriented and we could maintain an
#        explicit list of imports
from pathlib import Path

__all__ = [
    p.name[:-3] for p in Path(__file__).parent.glob("*.py") if p.is_file() and not p.name.endswith("__init__.py")
]

from . import *  # noqa [F403] still need to import all plugin tasks but no need
#            to know their name as they get registered in Plugin.classes

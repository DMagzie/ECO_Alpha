"""
Base Adapter Module
Abstract base class for format adapters
"""

from abc import ABC, abstractmethod
from typing import List, Any
import xml.etree.ElementTree as ET
from eco_tools.core.internal_repr import InternalRepresentation, Zone, Surface, Opening
from eco_tools.core.id_registry import IDRegistry


class BaseAdapter(ABC):
    """Abstract base for format-specific adapters"""
    
    def __init__(self, schema=None, id_registry: IDRegistry = None):
        self.schema = schema
        self.id_registry = id_registry or IDRegistry()
    
    @abstractmethod
    def parse(self, file_path: str) -> InternalRepresentation:
        """Parse file to internal representation"""
        pass
    
    @abstractmethod
    def serialize(self, internal: InternalRepresentation) -> Any:
        """Serialize internal representation to format"""
        pass
    
    @abstractmethod
    def get_name(self, element: ET.Element) -> str:
        """Extract name from element (format-specific)"""
        pass
    
    @abstractmethod
    def get_property(self, element: ET.Element, prop_name: str) -> Any:
        """Extract property from element (format-specific)"""
        pass
    
    def _local_tag(self, tag: str) -> str:
        """Strip namespace from tag"""
        return tag.split('}', 1)[-1] if '}' in tag else tag
    
    def _to_float(self, value: Any) -> float:
        """Safe float conversion"""
        if value is None:
            return None
        try:
            return float(str(value).replace(',', ''))
        except:
            return None
    
    def _to_int(self, value: Any) -> int:
        """Safe int conversion"""
        if value is None:
            return None
        try:
            return int(float(str(value)))
        except:
            return None

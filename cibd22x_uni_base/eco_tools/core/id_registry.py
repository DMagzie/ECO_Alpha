"""
ID Registry Module
Manages stable ID generation and tracking across translations
"""

from typing import Dict, Set, Optional
import hashlib


class IDRegistry:
    """
    Registry for generating and tracking stable IDs across format translations.
    Ensures consistent IDs for objects in round-trip translations.
    """
    
    def __init__(self):
        self.registry: Dict[str, str] = {}  # key -> id mapping
        self.reverse: Dict[str, str] = {}   # id -> key mapping
        self.used_ids: Set[str] = set()
        self.counters: Dict[str, int] = {}  # prefix -> counter
    
    def generate_id(self, 
                   prefix: str,
                   name: str,
                    context: str = "",
                   source_format: str = "") -> str:
        """
        Generate stable ID for an object.
        
        Args:
            prefix: ID prefix (Z=zone, S=surface, O=opening, etc)
            name: Object name
            context: Context string (e.g., zone name for surfaces)
            source_format: Source format for tracking
            
        Returns:
            Stable ID string (e.g., "Z_001", "S_Zone1_Wall1")
        """
        # Create registry key
        key = f"{prefix}:{context}:{name}:{source_format}"
        
        # Check if we've seen this before
        if key in self.registry:
            return self.registry[key]
        
        # Generate new ID
        if name:
            # Use name-based ID for readability
            slug = self._slugify(name)
            if context:
                ctx_slug = self._slugify(context)
                base_id = f"{prefix}_{ctx_slug}_{slug}"
            else:
                base_id = f"{prefix}_{slug}"
        else:
            # Use counter for unnamed objects
            counter = self.counters.get(prefix, 0) + 1
            self.counters[prefix] = counter
            base_id = f"{prefix}_{counter:03d}"
        
        # Ensure uniqueness
        final_id = base_id
        suffix = 1
        while final_id in self.used_ids:
            final_id = f"{base_id}_{suffix}"
            suffix += 1
        
        # Register
        self.registry[key] = final_id
        self.reverse[final_id] = key
        self.used_ids.add(final_id)
        
        return final_id
    
    def _slugify(self, text: str) -> str:
        """Convert text to slug format"""
        import re
        text = text.lower().strip()
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[-\s]+', '_', text)
        return text[:30]  # Limit length
    
    def get_id(self, key: str) -> Optional[str]:
        """Get existing ID for key"""
        return self.registry.get(key)
    
    def export_registry(self) -> Dict[str, str]:
        """Export registry for serialization"""
        return dict(self.registry)
    
    def import_registry(self, registry: Dict[str, str]):
        """Import registry from previous translation"""
        self.registry.update(registry)
        self.reverse.update({v: k for k, v in registry.items()})
        self.used_ids.update(registry.values())


if __name__ == '__main__':
    # Test
    registry = IDRegistry()
    z1 = registry.generate_id('Z', 'Living Room', '', 'CIBD22X')
    z2 = registry.generate_id('Z', 'Living Room', '', 'CIBD22X')  # Should be same
    print(f"Zone ID 1: {z1}")
    print(f"Zone ID 2: {z2}")
    print(f"Same? {z1 == z2}")

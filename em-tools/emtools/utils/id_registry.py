from __future__ import annotations
import hashlib
import re
from typing import Dict, Any, Optional


class IDRegistry:
    """Generate stable, deterministic IDs for EMJSON v6."""

    def __init__(self):
        self.forward_map: Dict[str, str] = {}  # source_key -> emjson_id
        self.reverse_map: Dict[str, Dict] = {}  # emjson_id -> metadata

    def generate_id(
            self,
            prefix: str,
            source_id: str,
            context: str = "",
            source_format: str = "CIBD22X"
    ) -> str:
        """
        Generate stable ID with format: PREFIX-HASH8-NAME

        Args:
            prefix: ID prefix (Z, S, O, WIN, CONST, SYS, DHW)
            source_id: Original ID/name from source file
            context: Additional context (e.g., parent zone name)
            source_format: Source file format (CIBD22X, HBJSON, etc.)

        Returns:
            Stable EMJSON ID (e.g., "Z-a3b4c5d6-living_room")
        """
        # Create lookup key for stability across imports
        lookup_key = f"{source_format}:{source_id}:{context}"

        # Return existing if already generated
        if lookup_key in self.forward_map:
            return self.forward_map[lookup_key]

        # Generate hash from prefix + source_id + context
        hash_input = f"{prefix}:{source_id}:{context}"
        stable_hash = hashlib.md5(hash_input.encode()).hexdigest()[:8]

        # Sanitize name for readability
        clean_name = self._sanitize(source_id)

        # Construct ID: PREFIX-HASH-NAME
        emjson_id = f"{prefix}-{stable_hash}-{clean_name}"

        # Register in both directions
        self.forward_map[lookup_key] = emjson_id
        self.reverse_map[emjson_id] = {
            "source_format": source_format,
            "source_id": source_id,
            "context": context,
            "lookup_key": lookup_key
        }

        return emjson_id

    def _sanitize(self, name: str, max_length: int = 20) -> str:
        """Clean name for ID suffix."""
        # Convert to lowercase
        clean = name.lower().strip()

        # Replace non-alphanumeric with underscore
        clean = re.sub(r'[^a-z0-9_-]', '_', clean)

        # Collapse multiple underscores
        clean = re.sub(r'_+', '_', clean)

        # Remove leading/trailing underscores
        clean = clean.strip('_')

        # Limit length
        if len(clean) > max_length:
            clean = clean[:max_length].rstrip('_')

        # Fallback if empty
        return clean or "item"

    def resolve(self, emjson_id: str) -> Optional[Dict[str, Any]]:
        """Get source metadata for an EMJSON ID."""
        return self.reverse_map.get(emjson_id)

    def export_registry(self) -> Dict[str, Any]:
        """Export registry for storage in EMJSON."""
        return {
            "forward_map": self.forward_map,
            "reverse_map": self.reverse_map
        }

    def import_registry(self, registry_data: Dict[str, Any]) -> None:
        """Import registry from stored EMJSON."""
        self.forward_map = registry_data.get("forward_map", {})
        self.reverse_map = registry_data.get("reverse_map", {})
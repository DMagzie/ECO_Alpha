# FILE 9: em-tools/emtools/parsers/constants.py
# ============================================================================
"""
Constants and taxonomies used across parsers.
"""

# Surface bucket taxonomy - maps XML tags to categories
SURFACE_BUCKETS = {
    "walls": ["ExtWall", "ExteriorWall", "PartyWall", "ResExtWall", "ComExtWall"],
    "roofs": ["Roof", "ExteriorRoof", "ResRoof", "ComRoof"],
    "floors": ["ExtFlr", "ExteriorFloor", "RaisedFloor", "ResExtFlr", "ComExtFlr"]
}

# Opening type mappings
OPENING_TYPES = {
    "windows": ["ResWin", "ComWin", "Window"],
    "doors": ["Door", "ExteriorDoor"],
    "skylights": ["Skylight", "TubularDaylightDevice"]
}
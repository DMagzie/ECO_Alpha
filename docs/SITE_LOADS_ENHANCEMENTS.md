# Site Loads Calculator - Enhancement Requests

**Date:** 2024-12-31
**Source:** User Testing Feedback

## Priority Enhancements

### 1. Outdoor Lighting
- Align inputs with NRCC-LTO form requirements
- Add fields matching interim calculator structure
- Consider importing data directly from NRCC-LTO if available

### 2. Pools and Spas
- Enable **multiple entries** for projects with more than one pool/spa
- Support different pool types (lap pool, amenity pool, spa, etc.)
- Allow individual configuration per entry

### 3. Miscellaneous Loads
Add support for occasional/specialized loads:
- Fire pumps
- Water softeners
- Commercial kitchens
- Other building-specific equipment
- Consider a "custom load" entry option

### 4. EV Charging
- Enable **multiple entries** for different configurations:
  - Level 1, Level 2, DCFC charging stations
  - Different parking areas (resident, guest, commercial)
  - Various quantities per level
- Support mixed charging configurations per project

### 5. IT Loads - Visual Guidance
- Add **visual guide to IT kW slider** showing typical ranges by building type:
  - Affordable housing: Lower IT needs (basic connectivity)
  - Market-rate residential: Moderate IT needs
  - Luxury/tech-focused: Higher IT needs (smart home, multiple devices)
  - Commercial: Varies by use type
- Include tooltip or link to guidance documentation
- Help users estimate when IT team input unavailable

## Implementation Notes

These enhancements support more accurate site load calculations for:
- Affordable housing projects (CUAC/TCAC compliance)
- Mixed-use developments
- Projects with complex amenity packages
- California Title 24 compliance documentation

## Related Files
- `eco_tools/lcca/site_loads/` - Core calculators
- `gui/pages/site_loads_page.py` - GUI implementation

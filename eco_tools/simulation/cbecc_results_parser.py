"""
CBECC-Com Results Parser
========================

Parses CBECC-Com AnalysisResults.xml files to extract energy metrics.

This module provides:
- XML parsing for CBECC AnalysisResults
- Energy end use extraction
- Compliance status parsing
- Comparison metrics calculation

Author: ECO Tools Team
Version: 7.0.0
Date: November 11, 2025
"""

from typing import Dict, List, Optional, Any
from pathlib import Path
import xml.etree.ElementTree as ET


class CBECCResultsParser:
    """
    Parse CBECC-Com AnalysisResults.xml files.

    Example:
        >>> parser = CBECCResultsParser("model - AnalysisResults.xml")
        >>> results = parser.parse()
        >>> print(f"Compliance: {results['compliance_status']}")
        >>> print(f"Total TDV: {results['total_tdv']}")
    """

    def __init__(self, xml_file: str):
        """
        Initialize CBECC results parser.

        Args:
            xml_file: Path to AnalysisResults.xml file
        """
        self.xml_file = Path(xml_file)
        self.tree = None
        self.root = None

    def parse(self) -> Dict[str, Any]:
        """
        Parse CBECC AnalysisResults.xml and extract metrics.

        Returns:
            Dict with parsed results:
                - status: "success" or "error"
                - compliance_status: Pass/Fail
                - climate_zone: California climate zone
                - total_tdv: Total TDV (kBtu/ft²/yr)
                - proposed_tdv: Proposed design TDV
                - standard_tdv: Standard design TDV
                - tdv_margin: Percent better than standard
                - end_uses: Dict of end use categories
                - building_area: Conditioned floor area (sqft)
                - building_type: Building type
        """
        if not self.xml_file.exists():
            return {
                "status": "error",
                "message": f"File not found: {self.xml_file}"
            }

        try:
            self.tree = ET.parse(str(self.xml_file))
            self.root = self.tree.getroot()

            result = {
                "status": "success",
                "xml_file": str(self.xml_file)
            }

            # Extract project information
            proj = self.root.find(".//Proj")
            if proj is not None:
                result["project_name"] = self._get_text(proj, "Name")
                result["climate_zone"] = self._parse_climate_zone(self._get_text(proj, "CliZn"))
                result["weather_station"] = self._get_text(proj, "WeatherStation")
                result["compliance_type"] = self._get_text(proj, "CompType")
                result["software_version"] = self._get_text(proj, "SoftwareVersion")

            # Extract building area
            result["building_area"] = self._extract_building_area()

            # Extract RunResults headers (end use categories)
            result["end_use_categories"] = self._extract_run_results_headers()

            # Extract energy results (if available in XML)
            # Note: Full energy tables may be in separate sections
            result["end_uses"] = self._extract_end_uses()

            # Extract compliance results
            compliance = self._extract_compliance()
            result.update(compliance)

            # Calculate EUI if possible
            if result.get("building_area") and result.get("total_energy_kwh"):
                # Convert kWh to kBtu (1 kWh = 3.412 kBtu)
                total_kbtu = result["total_energy_kwh"] * 3.412
                result["eui_kbtu_per_sqft_yr"] = total_kbtu / result["building_area"]

            return result

        except ET.ParseError as e:
            return {
                "status": "error",
                "message": f"XML parse error: {e}"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Parse error: {e}"
            }

    def _get_text(self, element: ET.Element, tag: str, default: str = "") -> str:
        """Get text from XML element."""
        child = element.find(tag)
        return child.text if child is not None and child.text else default

    def _parse_climate_zone(self, cz_text: str) -> str:
        """
        Parse climate zone from text.

        Examples:
            "ClimateZone4" → "CZ04"
            "Climate Zone 12" → "CZ12"
        """
        if not cz_text:
            return "Unknown"

        # Extract number from various formats
        import re
        match = re.search(r'(\d+)', cz_text)
        if match:
            zone_num = int(match.group(1))
            return f"CZ{zone_num:02d}"

        return cz_text

    def _extract_building_area(self) -> Optional[float]:
        """Extract total conditioned floor area."""
        # Try various locations where area might be stored
        area_tags = [
            ".//Proj/CondFloorArea",
            ".//Proj/TotFloorArea",
            ".//LtgInfo02Total_SpacesConditionedArea"
        ]

        for tag in area_tags:
            elem = self.root.find(tag)
            if elem is not None and elem.text:
                try:
                    return float(elem.text)
                except ValueError:
                    continue

        return None

    def _extract_run_results_headers(self) -> List[str]:
        """
        Extract RunResults headers (end use category names).

        Returns list like:
        - Space Heating
        - Space Cooling
        - Indoor Fans
        - etc.
        """
        headers = []
        for result in self.root.findall(".//RunResults"):
            index = result.get("index")
            text = result.text
            if text:
                headers.append(text.strip())

        return headers

    def _extract_end_uses(self) -> Dict[str, float]:
        """
        Extract end use energy values if available.

        Returns dict with end use categories as keys (kBtu/ft²/yr).

        Note: CBECC AnalysisResults.xml contains results ONLY if simulation
        completed successfully. Failed/incomplete simulations only have input data.
        """
        end_uses = {}

        # Try to find RunResultsTable sections which contain actual energy values
        # These are typically only present in successfully completed simulations

        # Look for annual totals
        annual_results = self.root.find(".//AnnualResults")
        if annual_results is not None:
            # Try to extract space heating
            space_heat = annual_results.find(".//SpaceHeating")
            if space_heat is not None and space_heat.text:
                try:
                    end_uses["space_heating"] = float(space_heat.text)
                except ValueError:
                    pass

            # Try to extract space cooling
            space_cool = annual_results.find(".//SpaceCooling")
            if space_cool is not None and space_cool.text:
                try:
                    end_uses["space_cooling"] = float(space_cool.text)
                except ValueError:
                    pass

            # Try to extract indoor fans
            indoor_fans = annual_results.find(".//IndoorFans")
            if indoor_fans is not None and indoor_fans.text:
                try:
                    end_uses["indoor_fans"] = float(indoor_fans.text)
                except ValueError:
                    pass

            # Try to extract DHW
            dhw = annual_results.find(".//DomesticHotWater")
            if dhw is not None and dhw.text:
                try:
                    end_uses["dhw"] = float(dhw.text)
                except ValueError:
                    pass

            # Try to extract lighting
            lighting = annual_results.find(".//IndoorLighting")
            if lighting is not None and lighting.text:
                try:
                    end_uses["indoor_lighting"] = float(lighting.text)
                except ValueError:
                    pass

        return end_uses

    def _extract_compliance(self) -> Dict[str, Any]:
        """
        Extract Title 24 compliance results.

        Returns:
            Dict with compliance metrics:
                - compliance_status: "Pass", "Fail", or "Unknown"
                - compliance_margin: Percentage better/worse than standard
                - proposed_tdv: Proposed design TDV (kBtu/ft²/yr)
                - standard_tdv: Standard design TDV (kBtu/ft²/yr)
                - compliance_type: e.g., "Performance"
        """
        compliance = {}

        # Look for compliance results elements
        # CBECC typically stores these in ComplianceResult or similar tags

        # Try to find compliance status
        comp_status = self.root.find(".//ComplianceStatus")
        if comp_status is not None and comp_status.text:
            status_text = comp_status.text.strip().lower()
            if "pass" in status_text or "comply" in status_text:
                compliance["compliance_status"] = "Pass"
            elif "fail" in status_text or "not comply" in status_text:
                compliance["compliance_status"] = "Fail"
            else:
                compliance["compliance_status"] = status_text
        else:
            compliance["compliance_status"] = "Unknown"

        # Try to find TDV values
        proposed_tdv = self.root.find(".//ProposedTDV")
        if proposed_tdv is not None and proposed_tdv.text:
            try:
                compliance["proposed_tdv"] = float(proposed_tdv.text)
            except ValueError:
                pass

        standard_tdv = self.root.find(".//StandardTDV")
        if standard_tdv is not None and standard_tdv.text:
            try:
                compliance["standard_tdv"] = float(standard_tdv.text)
            except ValueError:
                pass

        # Calculate compliance margin if we have both TDV values
        if "proposed_tdv" in compliance and "standard_tdv" in compliance:
            if compliance["standard_tdv"] > 0:
                margin = ((compliance["standard_tdv"] - compliance["proposed_tdv"]) /
                         compliance["standard_tdv"]) * 100
                compliance["compliance_margin"] = round(margin, 2)

        # Try to find compliance type
        comp_type = self.root.find(".//CompType")
        if comp_type is not None and comp_type.text:
            compliance["compliance_type"] = comp_type.text.strip()

        # Add message if we couldn't find results
        if compliance["compliance_status"] == "Unknown":
            compliance["compliance_message"] = (
                "No compliance results found in XML. "
                "File may contain only input data (simulation not completed)."
            )

        return compliance

    def compare_with_energyplus(
        self,
        energyplus_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compare CBECC results with EnergyPlus results.

        Args:
            energyplus_result: Dict from EnergyPlusRunner.run_simulation()

        Returns:
            Dict with comparison metrics
        """
        cbecc_result = self.parse()

        comparison = {
            "cbecc": {
                "status": cbecc_result.get("status"),
                "eui": cbecc_result.get("eui_kbtu_per_sqft_yr"),
                "building_area": cbecc_result.get("building_area"),
                "climate_zone": cbecc_result.get("climate_zone"),
                "compliance": cbecc_result.get("compliance_status")
            },
            "energyplus": {
                "status": energyplus_result.get("status"),
                "eui": energyplus_result.get("eui_kbtu_per_sqft_yr"),
                "total_energy": energyplus_result.get("total_site_energy_kwh")
            },
            "comparison": {}
        }

        # Calculate differences if both have EUI
        cbecc_eui = cbecc_result.get("eui_kbtu_per_sqft_yr")
        ep_eui = energyplus_result.get("eui_kbtu_per_sqft_yr")

        if cbecc_eui and ep_eui:
            delta = ep_eui - cbecc_eui
            percent_diff = (delta / cbecc_eui) * 100

            comparison["comparison"] = {
                "eui_delta": delta,
                "eui_percent_difference": percent_diff,
                "agreement": "Good" if abs(percent_diff) < 10 else "Fair" if abs(percent_diff) < 20 else "Poor"
            }

        return comparison


def extract_compliance_summary(xml_file: str) -> Dict[str, Any]:
    """
    Quick extraction of compliance summary without full parsing.

    Args:
        xml_file: Path to AnalysisResults.xml

    Returns:
        Dict with basic compliance info
    """
    parser = CBECCResultsParser(xml_file)
    result = parser.parse()

    return {
        "project_name": result.get("project_name", "Unknown"),
        "climate_zone": result.get("climate_zone", "Unknown"),
        "building_area": result.get("building_area"),
        "compliance_status": result.get("compliance_status", "Unknown"),
        "software_version": result.get("software_version", "Unknown")
    }


if __name__ == "__main__":
    # Test parser
    import sys

    if len(sys.argv) < 2:
        print("Usage: python cbecc_results_parser.py <AnalysisResults.xml>")
        print("\nExample:")
        print("  python cbecc_results_parser.py 'model - AnalysisResults.xml'")
        sys.exit(1)

    xml_file = sys.argv[1]
    parser = CBECCResultsParser(xml_file)
    results = parser.parse()

    print("\n" + "="*60)
    print("CBECC-Com Results Parser")
    print("="*60)

    if results["status"] == "success":
        print(f"\n✅ Successfully parsed: {xml_file}")
        print(f"\nProject: {results.get('project_name', 'N/A')}")
        print(f"Climate Zone: {results.get('climate_zone', 'N/A')}")
        print(f"Building Area: {results.get('building_area', 'N/A'):,.0f} sqft" if results.get('building_area') else "Building Area: N/A")
        print(f"Compliance: {results.get('compliance_status', 'N/A')}")

        if results.get("end_use_categories"):
            print(f"\nEnd Use Categories ({len(results['end_use_categories'])}):")
            for i, category in enumerate(results['end_use_categories'], 1):
                print(f"  {i}. {category}")

    else:
        print(f"\n❌ Error: {results.get('message', 'Unknown error')}")

    print("\n" + "="*60 + "\n")

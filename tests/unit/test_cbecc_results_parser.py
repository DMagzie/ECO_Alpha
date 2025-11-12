"""
Unit Tests for CBECC Results Parser
===================================

Tests for eco_tools.simulation.cbecc_results_parser module
"""

import pytest
from pathlib import Path
from eco_tools.simulation.cbecc_results_parser import CBECCResultsParser


# Fixtures

@pytest.fixture
def sample_xml_complete():
    """Sample complete CBECC AnalysisResults.xml with all sections"""
    return """<?xml version="1.0" encoding="UTF-8"?>
<CBECCAnalysisResult>
    <Proj>
        <Name>Test Building</Name>
        <CliZn>12</CliZn>
        <WeatherStation>Sacramento</WeatherStation>
        <CompType>Performance</CompType>
        <SoftwareVersion>2022.1.0</SoftwareVersion>
        <CondFloorArea>10000.0</CondFloorArea>
    </Proj>
    <ComplianceStatus>Pass</ComplianceStatus>
    <ProposedTDV>50000.0</ProposedTDV>
    <StandardTDV>60000.0</StandardTDV>
    <AnnualResults>
        <SpaceHeating>15.5</SpaceHeating>
        <SpaceCooling>12.3</SpaceCooling>
        <IndoorLighting>8.7</IndoorLighting>
        <IndoorFans>4.2</IndoorFans>
        <DomesticHotWater>2.5</DomesticHotWater>
    </AnnualResults>
</CBECCAnalysisResult>"""


@pytest.fixture
def sample_xml_incomplete():
    """Sample incomplete CBECC XML (simulation not run, only input data)"""
    return """<?xml version="1.0" encoding="UTF-8"?>
<CBECCAnalysisResult>
    <Proj>
        <Name>Incomplete Building</Name>
        <CliZn>6</CliZn>
        <CondFloorArea>5000.0</CondFloorArea>
    </Proj>
</CBECCAnalysisResult>"""


@pytest.fixture
def sample_xml_minimal():
    """Minimal CBECC XML with only project name"""
    return """<?xml version="1.0" encoding="UTF-8"?>
<CBECCAnalysisResult>
    <Proj>
        <Name>Minimal Building</Name>
    </Proj>
</CBECCAnalysisResult>"""


# Test Class

class TestCBECCResultsParser:
    """Test suite for CBECCResultsParser"""

    def test_init_with_valid_file(self, tmp_path, sample_xml_complete):
        """Test initialization with valid XML file"""
        xml_file = tmp_path / "results.xml"
        xml_file.write_text(sample_xml_complete)

        parser = CBECCResultsParser(str(xml_file))
        assert parser.xml_file == Path(xml_file)
        assert parser.tree is None  # Not parsed until parse() is called
        assert parser.root is None

    def test_init_stores_path(self, tmp_path):
        """Test that init stores path without parsing"""
        xml_file = tmp_path / "test.xml"
        parser = CBECCResultsParser(str(xml_file))

        # Path stored but file doesn't need to exist yet
        assert parser.xml_file == Path(xml_file)

    def test_parse_nonexistent_file(self):
        """Test parsing non-existent file returns error status"""
        parser = CBECCResultsParser("/nonexistent/file.xml")
        result = parser.parse()

        assert result["status"] == "error"
        assert "not found" in result["message"].lower()

    def test_parse_invalid_xml(self, tmp_path):
        """Test parsing invalid XML returns error status"""
        xml_file = tmp_path / "invalid.xml"
        xml_file.write_text("<invalid><xml>")

        parser = CBECCResultsParser(str(xml_file))
        result = parser.parse()

        assert result["status"] == "error"
        assert "parse error" in result["message"].lower()

    def test_parse_complete_results(self, tmp_path, sample_xml_complete):
        """Test parsing complete CBECC results"""
        xml_file = tmp_path / "complete.xml"
        xml_file.write_text(sample_xml_complete)

        parser = CBECCResultsParser(str(xml_file))
        results = parser.parse()

        assert results["status"] == "success"
        assert results["project_name"] == "Test Building"
        assert results["climate_zone"] == "CZ12"
        assert results["building_area"] == 10000.0
        assert results["compliance_status"] == "Pass"
        assert results["proposed_tdv"] == 50000.0
        assert results["standard_tdv"] == 60000.0
        assert results["compliance_margin"] == pytest.approx(16.67, rel=0.01)
        assert "space_heating" in results["end_uses"]
        assert results["end_uses"]["space_heating"] == 15.5

    def test_parse_incomplete_results(self, tmp_path, sample_xml_incomplete):
        """Test parsing incomplete CBECC results (no simulation run)"""
        xml_file = tmp_path / "incomplete.xml"
        xml_file.write_text(sample_xml_incomplete)

        parser = CBECCResultsParser(str(xml_file))
        results = parser.parse()

        assert results["status"] == "success"
        assert results["project_name"] == "Incomplete Building"
        assert results["climate_zone"] == "CZ06"
        assert results["building_area"] == 5000.0
        assert results["compliance_status"] == "Unknown"
        assert results["end_uses"] == {}

    def test_parse_minimal_results(self, tmp_path, sample_xml_minimal):
        """Test parsing minimal CBECC XML"""
        xml_file = tmp_path / "minimal.xml"
        xml_file.write_text(sample_xml_minimal)

        parser = CBECCResultsParser(str(xml_file))
        results = parser.parse()

        assert results["status"] == "success"
        assert results["project_name"] == "Minimal Building"
        assert results["climate_zone"] == "Unknown"
        assert results["building_area"] is None
        assert results["compliance_status"] == "Unknown"

    def test_parse_climate_zone_conversion(self):
        """Test climate zone text conversion"""
        parser = CBECCResultsParser("/dummy/path")

        assert parser._parse_climate_zone("1") == "CZ01"
        assert parser._parse_climate_zone("12") == "CZ12"
        assert parser._parse_climate_zone("16") == "CZ16"
        assert parser._parse_climate_zone("ClimateZone4") == "CZ04"
        assert parser._parse_climate_zone("") == "Unknown"

    def test_parse_returns_expected_keys(self, tmp_path, sample_xml_complete):
        """Test that parse() returns expected dictionary keys"""
        xml_file = tmp_path / "keys_test.xml"
        xml_file.write_text(sample_xml_complete)

        parser = CBECCResultsParser(str(xml_file))
        results = parser.parse()

        expected_keys = [
            "status", "project_name", "climate_zone", "building_area",
            "compliance_status", "end_uses", "xml_file"
        ]

        for key in expected_keys:
            assert key in results, f"Missing key: {key}"

    def test_parse_with_special_characters(self, tmp_path):
        """Test parsing with special characters in project name"""
        xml_special = """<?xml version="1.0" encoding="UTF-8"?>
<CBECCAnalysisResult>
    <Proj>
        <Name>Building &amp; Office (2025)</Name>
        <CliZn>3</CliZn>
    </Proj>
</CBECCAnalysisResult>"""

        xml_file = tmp_path / "special.xml"
        xml_file.write_text(xml_special)

        parser = CBECCResultsParser(str(xml_file))
        results = parser.parse()

        assert results["project_name"] == "Building & Office (2025)"
        assert results["climate_zone"] == "CZ03"


# Integration Tests

class TestCBECCResultsParserIntegration:
    """Integration tests using real-world scenarios"""

    def test_parse_typical_office_building(self, tmp_path):
        """Test parsing typical office building results"""
        xml_office = """<?xml version="1.0" encoding="UTF-8"?>
<CBECCAnalysisResult>
    <Proj>
        <Name>Typical Office Building</Name>
        <CliZn>12</CliZn>
        <CondFloorArea>50000.0</CondFloorArea>
    </Proj>
    <ComplianceStatus>Pass - Complies with Performance Standard</ComplianceStatus>
    <ProposedTDV>250000.0</ProposedTDV>
    <StandardTDV>280000.0</StandardTDV>
    <AnnualResults>
        <SpaceHeating>8.5</SpaceHeating>
        <SpaceCooling>18.2</SpaceCooling>
        <IndoorFans>4.3</IndoorFans>
        <IndoorLighting>10.5</IndoorLighting>
        <DomesticHotWater>2.1</DomesticHotWater>
    </AnnualResults>
</CBECCAnalysisResult>"""

        xml_file = tmp_path / "office.xml"
        xml_file.write_text(xml_office)

        parser = CBECCResultsParser(str(xml_file))
        results = parser.parse()

        # Verify all key metrics
        assert results["project_name"] == "Typical Office Building"
        assert results["climate_zone"] == "CZ12"
        assert results["building_area"] == 50000.0
        assert results["compliance_status"] == "Pass"
        assert results["compliance_margin"] > 0  # Passing margin

        # Verify end uses present
        assert len(results["end_uses"]) >= 3
        assert "space_heating" in results["end_uses"]
        assert "space_cooling" in results["end_uses"]

    def test_parse_failing_building(self, tmp_path):
        """Test parsing building that fails compliance"""
        xml_fail = """<?xml version="1.0" encoding="UTF-8"?>
<CBECCAnalysisResult>
    <Proj>
        <Name>Non-Compliant Building</Name>
        <CliZn>6</CliZn>
        <CondFloorArea>25000.0</CondFloorArea>
    </Proj>
    <ComplianceStatus>fail - Does not comply</ComplianceStatus>
    <ProposedTDV>350000.0</ProposedTDV>
    <StandardTDV>280000.0</StandardTDV>
</CBECCAnalysisResult>"""

        xml_file = tmp_path / "fail.xml"
        xml_file.write_text(xml_fail)

        parser = CBECCResultsParser(str(xml_file))
        results = parser.parse()

        assert results["compliance_status"] == "Fail"
        assert results["compliance_margin"] < 0  # Failing margin

    def test_extract_compliance_summary_function(self, tmp_path, sample_xml_complete):
        """Test extract_compliance_summary() helper function"""
        from eco_tools.simulation.cbecc_results_parser import extract_compliance_summary

        xml_file = tmp_path / "summary_test.xml"
        xml_file.write_text(sample_xml_complete)

        summary = extract_compliance_summary(str(xml_file))

        assert summary["project_name"] == "Test Building"
        assert summary["climate_zone"] == "CZ12"
        assert summary["building_area"] == 10000.0
        assert summary["compliance_status"] == "Pass"


# Edge Cases

class TestCBECCResultsParserEdgeCases:
    """Test edge cases and error handling"""

    def test_parse_with_missing_climate_zone(self, tmp_path):
        """Test parsing when climate zone is missing"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<CBECCAnalysisResult>
    <Proj>
        <Name>No Climate Zone</Name>
    </Proj>
</CBECCAnalysisResult>"""

        xml_file = tmp_path / "no_cz.xml"
        xml_file.write_text(xml)

        parser = CBECCResultsParser(str(xml_file))
        results = parser.parse()

        assert results["climate_zone"] == "Unknown"

    def test_parse_with_zero_standard_tdv(self, tmp_path):
        """Test compliance margin calculation with zero standard TDV"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<CBECCAnalysisResult>
    <Proj><Name>Zero Test</Name></Proj>
    <ComplianceStatus>Pass</ComplianceStatus>
    <ProposedTDV>1000.0</ProposedTDV>
    <StandardTDV>0.0</StandardTDV>
</CBECCAnalysisResult>"""

        xml_file = tmp_path / "zero.xml"
        xml_file.write_text(xml)

        parser = CBECCResultsParser(str(xml_file))
        results = parser.parse()

        # Should handle division by zero - no margin calculated
        assert "compliance_margin" not in results or results.get("compliance_margin") is None

    def test_parse_with_missing_end_uses(self, tmp_path):
        """Test parsing when end uses section is missing"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<CBECCAnalysisResult>
    <Proj>
        <Name>No End Uses</Name>
        <CliZn>12</CliZn>
    </Proj>
    <ComplianceStatus>Pass</ComplianceStatus>
</CBECCAnalysisResult>"""

        xml_file = tmp_path / "no_end_uses.xml"
        xml_file.write_text(xml)

        parser = CBECCResultsParser(str(xml_file))
        results = parser.parse()

        assert results["end_uses"] == {}

    def test_parse_exception_handling(self, tmp_path):
        """Test that parser handles exceptions gracefully"""
        xml_file = tmp_path / "test.xml"
        xml_file.write_text("<?xml version='1.0'?><root></root>")

        parser = CBECCResultsParser(str(xml_file))
        results = parser.parse()

        # Should return success status for valid XML even if content is minimal
        assert "status" in results

    def test_parser_with_path_object(self, tmp_path, sample_xml_complete):
        """Test that parser works with Path objects"""
        xml_file = tmp_path / "path_test.xml"
        xml_file.write_text(sample_xml_complete)

        # Pass Path object instead of string
        parser = CBECCResultsParser(xml_file)
        results = parser.parse()

        assert results["status"] == "success"

    def test_multiple_parses(self, tmp_path, sample_xml_complete):
        """Test that parser can be called multiple times"""
        xml_file = tmp_path / "multi.xml"
        xml_file.write_text(sample_xml_complete)

        parser = CBECCResultsParser(str(xml_file))

        results1 = parser.parse()
        results2 = parser.parse()

        # Both should succeed and return same data
        assert results1["status"] == "success"
        assert results2["status"] == "success"
        assert results1["project_name"] == results2["project_name"]

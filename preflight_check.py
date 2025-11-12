#!/usr/bin/env python3
"""
ECO_Alpha v7 Pre-Flight Check
==============================

Verifies that all components are properly installed and ready for testing.
Run this before starting your testing session.

Usage:
    python3 preflight_check.py
"""

import sys
from pathlib import Path

def print_header(text):
    """Print formatted header"""
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)

def check_module(module_name, package_name=None):
    """Check if a module can be imported"""
    try:
        __import__(module_name)
        print(f"✅ {package_name or module_name}")
        return True
    except ImportError as e:
        print(f"❌ {package_name or module_name} - NOT FOUND")
        print(f"   Install with: pip install {package_name or module_name}")
        return False

def check_path(path, description):
    """Check if a path exists"""
    p = Path(path)
    if p.exists():
        print(f"✅ {description}: {path}")
        return True
    else:
        print(f"❌ {description}: {path} - NOT FOUND")
        return False

def main():
    print_header("ECO_Alpha v7 Pre-Flight Check")
    print("Verifying installation and dependencies...\n")

    all_passed = True

    # Python version check
    print_header("Python Version")
    version = sys.version_info
    if version.major == 3 and version.minor >= 11:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    else:
        print(f"⚠️  Python {version.major}.{version.minor}.{version.micro}")
        print("   Recommended: Python 3.11+")
        all_passed = False

    # Core dependencies
    print_header("Core Dependencies")
    all_passed &= check_module("streamlit")
    all_passed &= check_module("plotly")

    # Optional but recommended
    print_header("Simulation Dependencies (Optional)")
    has_honeybee = check_module("honeybee_energy", "honeybee-energy")
    has_ladybug = check_module("ladybug", "ladybug-comfort")

    if not has_honeybee or not has_ladybug:
        print("\n   Note: EnergyPlus simulations require honeybee-energy")
        print("   Install with: pip install honeybee-energy ladybug-comfort")

    # ECO_Alpha modules
    print_header("ECO_Alpha v7 Modules")
    sys.path.insert(0, str(Path(__file__).parent))

    all_passed &= check_module("eco_tools.visualization.charts", "Visualization Module")
    all_passed &= check_module("eco_tools.reporting.csv_exporter", "CSV Export Module")
    all_passed &= check_module("eco_tools.simulation.cbecc_results_parser", "CBECC Parser Module")

    # Check for GUI
    print_header("GUI Components")
    all_passed &= check_path("gui/main.py", "Main GUI")
    all_passed &= check_path("gui/pages/simulation_page.py", "Simulation Page")

    # Check for test directories
    print_header("Test Infrastructure")
    check_path("tests/unit", "Unit Tests")
    check_path("tests/integration", "Integration Tests")

    # Check for documentation
    print_header("Documentation")
    check_path("docs/USER_GUIDE.md", "User Guide")
    check_path("docs/API_REFERENCE.md", "API Reference")
    check_path("docs/TESTING_CHECKLIST.md", "Testing Checklist")

    # Check for test output directory
    print_header("Output Directories")
    output_dir = Path("test_output")
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"✅ Created test_output directory")
    else:
        print(f"✅ test_output directory exists")

    # Summary
    print_header("Pre-Flight Check Summary")
    if all_passed:
        print("✅ ALL CHECKS PASSED")
        print("\nECO_Alpha v7 is ready for testing!")
        print("\nTo launch GUI:")
        print("  streamlit run gui/main.py")
        print("\nTo run tests:")
        print("  python3 -m pytest tests/unit/ -v")
        print("\nSee docs/TESTING_CHECKLIST.md for testing guide")
        return 0
    else:
        print("⚠️  SOME CHECKS FAILED")
        print("\nPlease install missing dependencies before testing.")
        print("Most issues can be resolved with:")
        print("  pip install streamlit plotly honeybee-energy ladybug-comfort")
        return 1

if __name__ == "__main__":
    exit(main())

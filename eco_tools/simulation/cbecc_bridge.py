"""
CBECC-COM Simulation Bridge with Wine Support for macOS

This module provides a bridge to run CBECC-COM (California Building Energy Code Compliance)
simulations on macOS using Wine, and native execution on Windows/Linux.

Key Features:
- Cross-platform support (Windows native, macOS via Wine, Linux via Wine)
- Automatic Wine installation detection
- CBECC-COM installation helpers
- CLI simulation execution
- Results parsing (CF1R compliance reports)
- Pre-flight validation

Author: ECO Tools Development Team
Date: October 2025
"""

import subprocess
import platform
import shutil
from pathlib import Path
from typing import Tuple, Optional, Dict, List
import xml.etree.ElementTree as ET
import json


class CBECCWineBridge:
    """
    Bridge to CBECC-Com for Title 24 compliance simulation.
    Supports Windows (native), macOS (via Wine), and Linux (via Wine).
    """
    
    # CBECC-COM CLI command line arguments (based on typical usage)
    # Note: Actual flags may vary by version - adjust as needed
    CBECC_CLI_FLAGS = {
        'input': '-i',           # Input file path
        'output': '-o',          # Output directory
        'analysis': '-a',        # Analysis type
        'climate': '-z',         # Climate zone
        'ruleset': '-r',         # Ruleset year (2022, 2019, etc.)
        'batch': '-b',           # Batch mode (no GUI)
        'verbose': '-v',         # Verbose output
    }
    
    def __init__(self, cbecc_path: Optional[str] = None, wine_path: Optional[str] = None):
        """
        Initialize CBECC bridge with automatic platform detection.
        
        Args:
            cbecc_path: Path to CBECC-Com executable (Windows .exe)
                       If None, will attempt to find in standard locations
            wine_path: Path to Wine executable (macOS/Linux only)
                      If None, will attempt to find Wine automatically
        """
        self.platform = platform.system()
        self.is_mac = self.platform == "Darwin"
        self.is_windows = self.platform == "Windows"
        self.is_linux = self.platform == "Linux"
        
        # Find Wine if needed
        self.wine_path = None
        if not self.is_windows:
            self.wine_path = wine_path or self._find_wine()
            if not self.wine_path:
                raise FileNotFoundError(
                    f"Wine not found on {self.platform}. "
                    f"CBECC-Com is Windows-only and requires Wine to run on macOS/Linux.\n\n"
                    f"Install Wine:\n"
                    f"  macOS:  brew install --cask wine-stable\n"
                    f"  Linux:  sudo apt-get install wine  (or use your package manager)\n"
                )
        
        # Find CBECC executable
        self.cbecc_path = cbecc_path or self._find_cbecc_executable()
        if not self.cbecc_path:
            raise FileNotFoundError(
                "CBECC-Com not found. Please install from:\n"
                "https://www.energy.ca.gov/programs-and-topics/programs/"
                "building-energy-efficiency-standards/compliance-software-tools\n\n"
                f"Installation instructions for {self.platform}:\n"
                f"{self._get_install_instructions()}"
            )
        
        print(f"✅ CBECC Bridge initialized")
        print(f"   Platform: {self.platform}")
        if not self.is_windows:
            print(f"   Wine: {self.wine_path}")
        print(f"   CBECC: {self.cbecc_path}")
    
    def _find_wine(self) -> Optional[str]:
        """
        Find Wine executable on macOS/Linux.
        
        Returns:
            Path to Wine executable or None if not found
        """
        # Check common Wine locations
        wine_candidates = [
            'wine',  # In PATH
            'wine64',  # 64-bit Wine
            '/usr/local/bin/wine',
            '/opt/homebrew/bin/wine',  # M1 Mac Homebrew
            '/usr/bin/wine',
        ]
        
        for candidate in wine_candidates:
            wine_path = shutil.which(candidate)
            if wine_path:
                # Verify it works
                try:
                    result = subprocess.run(
                        [wine_path, '--version'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        return wine_path
                except:
                    continue
        
        return None
    
    def _find_cbecc_executable(self) -> Optional[str]:
        """
        Find CBECC-Com executable in standard installation locations.
        Searches for the Windows .exe file regardless of platform.
        
        Returns:
            Path to CBECC-Com executable (.exe) or None if not found
        """
        search_paths = []
        
        if self.is_windows:
            # Native Windows paths
            search_paths = [
                r"C:\Program Files\CBECC-Com 2022\CBECC-Com.exe",
                r"C:\Program Files\CBECC-Com 2022\CBECCcom.exe",
                r"C:\Program Files (x86)\CBECC-Com 2022\CBECC-Com.exe",
                r"C:\Program Files (x86)\CBECC-Com 2022\CBECCcom.exe",
                r"C:\CBECC-Com\CBECC-Com.exe",
                r"C:\CBECC-Com\CBECCcom.exe",
            ]
        else:
            # Wine prefix paths (macOS/Linux)
            wine_prefix = Path.home() / ".wine"
            wine_c_drive = wine_prefix / "drive_c"
            
            # Check if Wine prefix exists
            if wine_c_drive.exists():
                search_paths = [
                    wine_c_drive / "Program Files/CBECC-Com 2022/CBECC-Com.exe",
                    wine_c_drive / "Program Files/CBECC-Com 2022/CBECCcom.exe",
                    wine_c_drive / "Program Files (x86)/CBECC-Com 2022/CBECC-Com.exe",
                    wine_c_drive / "Program Files (x86)/CBECC-Com 2022/CBECCcom.exe",
                    wine_c_drive / "CBECC-Com/CBECC-Com.exe",
                    wine_c_drive / "CBECC-Com/CBECCcom.exe",
                ]
            
            # Also check common macOS application locations
            mac_apps = [
                Path.home() / "Applications/CBECC-Com/CBECC-Com.exe",
                Path("/Applications/CBECC-Com/CBECC-Com.exe"),
            ]
            search_paths.extend(mac_apps)
        
        for path in search_paths:
            path_obj = Path(path) if not isinstance(path, Path) else path
            if path_obj.exists():
                return str(path_obj)
        
        return None
    
    def _get_install_instructions(self) -> str:
        """Get platform-specific installation instructions for CBECC-COM."""
        if self.is_windows:
            return """
Windows:
  1. Download installer from California Energy Commission
  2. Run CBECCcom_2022_Setup.exe
  3. Follow installation wizard
  4. Default install: C:\\Program Files\\CBECC-Com 2022\\
"""
        else:
            return f"""
{self.platform}:
  1. Install Wine (see above)
  2. Download CBECC-Com Windows installer (.exe)
  3. Install via Wine:
     wine CBECCcom_2022_Setup.exe
  4. CBECC will be installed in Wine's Program Files:
     ~/.wine/drive_c/Program Files/CBECC-Com 2022/
  
  Alternative: Manual installation
  1. Extract CBECC-Com files from installer
  2. Place in: ~/Applications/CBECC-Com/
  3. Ensure CBECC-Com.exe is present
"""
    
    def _build_command(self, args: List[str]) -> List[str]:
        """
        Build the command to execute CBECC-COM, with or without Wine.
        
        Args:
            args: Command line arguments for CBECC-COM
        
        Returns:
            Complete command as list of strings
        """
        if self.is_windows:
            # Windows: Direct execution
            return [str(self.cbecc_path)] + args
        else:
            # macOS/Linux: Via Wine
            return [self.wine_path, str(self.cbecc_path)] + args
    
    def validate_cibd22x(self, cibd_path: str) -> Tuple[bool, List[str]]:
        """
        Validate CIBD22X file before simulation.
        Checks for required elements and proper structure.
        
        Args:
            cibd_path: Path to CIBD22X XML file
        
        Returns:
            (is_valid, error_list) tuple
        """
        errors = []
        
        try:
            tree = ET.parse(cibd_path)
            root = tree.getroot()
            
            # Check required elements
            if not root.find('.//Proj'):
                errors.append("Missing <Proj> (Project) element")
            
            if not root.find('.//Bldg'):
                errors.append("Missing <Bldg> (Building) element")
            
            zones = root.findall('.//Zone')
            if not zones:
                errors.append("No zones defined - at least one <Zone> required")
            
            hvac_systems = root.findall('.//ZnSys')
            if not hvac_systems:
                errors.append("No HVAC systems defined - at least one <ZnSys> required")
            
            # Check zone-HVAC assignments
            unassigned_systems = []
            for hvac in hvac_systems:
                zone_refs = hvac.findall('.//Zone')
                if not zone_refs:
                    hvac_id = hvac.get('id', 'unknown')
                    unassigned_systems.append(hvac_id)
            
            if unassigned_systems:
                errors.append(
                    f"HVAC system(s) with no zones assigned: {', '.join(unassigned_systems)}"
                )
            
            # Check for geometry
            surfaces = root.findall('.//ExtWall') + root.findall('.//Roof') + \
                      root.findall('.//UndgrFlr') + root.findall('.//IntFlr')
            if not surfaces:
                errors.append("No building surfaces found - geometry may be missing")
            
            # Check for schedules
            schedules = root.findall('.//SchDay') + root.findall('.//SchWeek')
            if not schedules:
                errors.append("No schedules defined - required for simulation")
            
            return len(errors) == 0, errors
            
        except ET.ParseError as e:
            return False, [f"XML parse error: {str(e)}"]
        except FileNotFoundError:
            return False, [f"File not found: {cibd_path}"]
        except Exception as e:
            return False, [f"Validation error: {str(e)}"]
    
    def run_simulation(
        self,
        cibd_path: str,
        output_dir: Optional[str] = None,
        analysis_type: str = "compliance",
        climate_zone: str = "CZ06",
        ruleset: str = "2022",
        verbose: bool = True,
        timeout: int = 600
    ) -> Dict[str, any]:
        """
        Run CBECC-Com simulation via CLI.
        
        Args:
            cibd_path: Path to input CIBD22X file
            output_dir: Directory for output files (default: same as input)
            analysis_type: Type of analysis:
                          - "compliance" = Title 24 compliance check
                          - "design" = Design development analysis  
                          - "sizing" = HVAC sizing calculations
            climate_zone: California climate zone (CZ01-CZ16)
            ruleset: Code year (2022, 2019, 2016, etc.)
            verbose: Show detailed CBECC output
            timeout: Maximum simulation time in seconds (default: 10 minutes)
        
        Returns:
            dict with:
                - success (bool): True if simulation completed
                - output_files (list): Generated output files
                - messages (list): CBECC console output
                - compliance_results (dict): Parsed results if available
                - return_code (int): Process exit code
                - execution_time (float): Simulation time in seconds
        """
        import time
        start_time = time.time()
        
        cibd_path = Path(cibd_path).resolve()
        if not cibd_path.exists():
            return {
                "success": False,
                "messages": [f"❌ Input file not found: {cibd_path}"],
                "execution_time": 0
            }
        
        # Validate before running
        print("\n🔍 Validating input file...")
        is_valid, errors = self.validate_cibd22x(str(cibd_path))
        if not is_valid:
            return {
                "success": False,
                "messages": ["❌ Validation failed:"] + [f"  • {e}" for e in errors],
                "execution_time": time.time() - start_time
            }
        print("✅ Validation passed")
        
        # Set output directory
        if output_dir is None:
            output_dir = cibd_path.parent / "cbecc_output"
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Build CBECC command
        # NOTE: These flags are based on typical CBECC CLI usage
        # Adjust if your CBECC version uses different syntax
        args = [
            '-i', str(cibd_path),           # Input file
            '-o', str(output_dir),          # Output directory
            '-b',                           # Batch mode (no GUI)
        ]
        
        # Add optional parameters based on CBECC version
        # Different versions may support different flags
        if verbose:
            args.append('-v')  # Verbose output
        
        cmd = self._build_command(args)
        
        print(f"\n🚀 Running CBECC-Com simulation...")
        print(f"   Input: {cibd_path.name}")
        print(f"   Output: {output_dir}")
        print(f"   Climate Zone: {climate_zone}")
        print(f"   Analysis: {analysis_type}")
        print(f"   Ruleset: {ruleset}")
        if not self.is_windows:
            print(f"   Execution: via Wine")
        
        # Run simulation
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(cibd_path.parent)  # Run from input file directory
            )
            
            execution_time = time.time() - start_time
            
            # Collect messages
            messages = []
            if result.stdout:
                messages.extend([line for line in result.stdout.split('\n') if line.strip()])
            if result.stderr:
                stderr_lines = [line for line in result.stderr.split('\n') if line.strip()]
                # Filter out Wine-specific warnings that are harmless
                if not self.is_windows:
                    stderr_lines = [
                        line for line in stderr_lines 
                        if not any(x in line.lower() for x in ['fixme:', 'wine:', 'err:'])
                    ]
                messages.extend(stderr_lines)
            
            # Find output files
            output_files = []
            for pattern in ['*.xml', '*.pdf', '*.csv', '*.html', '*.txt']:
                output_files.extend(list(output_dir.glob(pattern)))
            
            # Parse compliance results if available
            compliance_results = None
            cf1r_files = list(output_dir.glob("*CF1R*.xml"))
            if cf1r_files:
                compliance_results = self._parse_cf1r(cf1r_files[0])
            
            success = result.returncode == 0
            
            if success:
                print(f"\n✅ Simulation completed in {execution_time:.1f}s")
                print(f"   Output files: {len(output_files)}")
            else:
                print(f"\n❌ Simulation failed (exit code: {result.returncode})")
            
            return {
                "success": success,
                "output_files": [str(f) for f in output_files],
                "messages": messages,
                "compliance_results": compliance_results,
                "return_code": result.returncode,
                "execution_time": execution_time
            }
            
        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            print(f"\n⏱️ Simulation timed out after {timeout}s")
            return {
                "success": False,
                "messages": [f"⏱️ Simulation timed out after {timeout} seconds"],
                "execution_time": execution_time
            }
        except Exception as e:
            execution_time = time.time() - start_time
            print(f"\n❌ Error: {str(e)}")
            return {
                "success": False,
                "messages": [f"❌ Simulation error: {str(e)}"],
                "execution_time": execution_time
            }
    
    def _parse_cf1r(self, cf1r_path: Path) -> Dict:
        """
        Parse CF1R compliance report XML.
        Extracts key compliance metrics from CBECC output.
        
        Args:
            cf1r_path: Path to CF1R XML file
        
        Returns:
            Dictionary of compliance metrics
        """
        try:
            tree = ET.parse(cf1r_path)
            root = tree.getroot()
            
            # Extract key compliance metrics
            # Note: Actual XML structure may vary by CBECC version
            results = {
                "complies": root.findtext('.//ComplianceStatus', 'Unknown') == "Pass",
                "tdu_proposed": self._safe_float(root.findtext('.//TDU_Proposed', '0')),
                "tdu_standard": self._safe_float(root.findtext('.//TDU_Standard', '0')),
                "tdu_margin": self._safe_float(root.findtext('.//TDU_Margin', '0')),
                "eui_proposed": self._safe_float(root.findtext('.//EUI_Proposed', '0')),
                "eui_standard": self._safe_float(root.findtext('.//EUI_Standard', '0')),
            }
            
            return results
            
        except Exception as e:
            return {"error": f"Failed to parse CF1R: {str(e)}"}
    
    def _safe_float(self, value: str) -> float:
        """Safely convert string to float, return 0.0 if conversion fails."""
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0
    
    def get_version(self) -> str:
        """
        Get CBECC-Com version by running with --version flag.
        
        Returns:
            Version string or "Unknown" if detection fails
        """
        try:
            cmd = self._build_command(['--version'])
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Parse version from output
            version_str = result.stdout.strip() or result.stderr.strip()
            
            # Clean up Wine output if present
            if not self.is_windows:
                lines = [l for l in version_str.split('\n') 
                        if not any(x in l.lower() for x in ['wine:', 'fixme:', 'err:'])]
                version_str = '\n'.join(lines).strip()
            
            return version_str if version_str else "Unknown"
            
        except Exception as e:
            return f"Unknown (error: {str(e)})"
    
    def test_installation(self) -> Dict[str, any]:
        """
        Test CBECC-COM installation and Wine configuration.
        
        Returns:
            Dictionary with test results
        """
        results = {
            "platform": self.platform,
            "wine_installed": self.wine_path is not None if not self.is_windows else "N/A",
            "wine_path": self.wine_path if not self.is_windows else "N/A",
            "cbecc_found": self.cbecc_path is not None,
            "cbecc_path": self.cbecc_path,
            "version": None,
            "can_execute": False,
            "errors": []
        }
        
        if not results["cbecc_found"]:
            results["errors"].append("CBECC-COM executable not found")
            return results
        
        # Try to get version
        try:
            version = self.get_version()
            results["version"] = version
            results["can_execute"] = version != "Unknown"
        except Exception as e:
            results["errors"].append(f"Cannot execute CBECC: {str(e)}")
        
        return results


def print_installation_guide():
    """Print detailed installation guide for CBECC-COM with Wine."""
    system = platform.system()
    
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║               CBECC-COM Installation Guide for ECO Tools                     ║
╚══════════════════════════════════════════════════════════════════════════════╝
""")
    
    if system == "Darwin":  # macOS
        print("""
🍎 macOS Installation Steps:

1️⃣  Install Homebrew (if not already installed):
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

2️⃣  Install Wine:
   brew install --cask wine-stable
   
   Or for M1/M2 Macs (Apple Silicon):
   brew install --cask wine-crossover
   
3️⃣  Download CBECC-COM:
   Visit: https://www.energy.ca.gov/programs-and-topics/programs/building-energy-efficiency-standards/compliance-software-tools
   Download: CBECC-Com 2022 Windows Installer (.exe)

4️⃣  Install CBECC-COM via Wine:
   wine ~/Downloads/CBECCcom_2022_Setup.exe
   
   Follow the installation wizard. Files will be installed to:
   ~/.wine/drive_c/Program Files/CBECC-Com 2022/

5️⃣  Verify Installation:
   python3 cbecc_wine_bridge.py --test

Alternative: Manual Installation
   1. Extract CBECC files from installer
   2. Create directory: ~/Applications/CBECC-Com/
   3. Copy CBECC-Com.exe and all DLLs to that directory
   4. Update cbecc_path when initializing bridge
""")
    
    elif system == "Linux":
        print("""
🐧 Linux Installation Steps:

1️⃣  Install Wine:
   Ubuntu/Debian:
   sudo apt-get update
   sudo apt-get install wine wine64
   
   Fedora/RHEL:
   sudo dnf install wine
   
   Arch:
   sudo pacman -S wine

2️⃣  Download CBECC-COM:
   Visit: https://www.energy.ca.gov/programs-and-topics/programs/building-energy-efficiency-standards/compliance-software-tools
   Download: CBECC-Com 2022 Windows Installer (.exe)

3️⃣  Install CBECC-COM via Wine:
   wine ~/Downloads/CBECCcom_2022_Setup.exe
   
   Files will be installed to:
   ~/.wine/drive_c/Program Files/CBECC-Com 2022/

4️⃣  Verify Installation:
   python3 cbecc_wine_bridge.py --test
""")
    
    else:  # Windows
        print("""
🪟 Windows Installation Steps:

1️⃣  Download CBECC-COM:
   Visit: https://www.energy.ca.gov/programs-and-topics/programs/building-energy-efficiency-standards/compliance-software-tools
   Download: CBECC-Com 2022 Installer (.exe)

2️⃣  Run Installer:
   Double-click CBECCcom_2022_Setup.exe
   Follow installation wizard
   
   Default location: C:\\Program Files\\CBECC-Com 2022\\

3️⃣  Verify Installation:
   python cbecc_wine_bridge.py --test

Note: Wine is not needed on Windows - CBECC runs natively.
""")
    
    print("""
═══════════════════════════════════════════════════════════════════════════════

📋 Troubleshooting:

Wine Issues (macOS/Linux):
  • If Wine won't install: Try using Wine Stable or Crossover
  • If CBECC won't run: Check Wine version compatibility
  • Missing DLLs: Install winetricks and add required Windows components
  
CBECC Issues:
  • Simulation fails: Check input file validation errors
  • No output files: Verify write permissions on output directory
  • Timeout errors: Increase timeout parameter in run_simulation()

Getting Help:
  • ECO Tools Documentation: [Your docs URL]
  • CBECC Support: https://www.energy.ca.gov/programs-and-topics/programs/building-energy-efficiency-standards
  • Wine AppDB: https://appdb.winehq.org/

═══════════════════════════════════════════════════════════════════════════════
""")


# ============================================================================
# CLI Interface
# ============================================================================

if __name__ == "__main__":
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(
        description="CBECC-COM Simulation Bridge with Wine Support",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test installation
  python cbecc_wine_bridge.py --test
  
  # Show installation guide
  python cbecc_wine_bridge.py --install-guide
  
  # Run simulation
  python cbecc_wine_bridge.py --input building.cibd22x --output ./results
  
  # Validate file only
  python cbecc_wine_bridge.py --validate building.cibd22x
"""
    )
    
    parser.add_argument('--test', action='store_true',
                       help='Test CBECC and Wine installation')
    parser.add_argument('--install-guide', action='store_true',
                       help='Show installation guide')
    parser.add_argument('--input', '-i', type=str,
                       help='Input CIBD22X file path')
    parser.add_argument('--output', '-o', type=str,
                       help='Output directory for results')
    parser.add_argument('--validate', type=str,
                       help='Validate CIBD22X file without running simulation')
    parser.add_argument('--climate-zone', '-z', type=str, default='CZ06',
                       help='California climate zone (default: CZ06)')
    parser.add_argument('--analysis', '-a', type=str, default='compliance',
                       choices=['compliance', 'design', 'sizing'],
                       help='Analysis type (default: compliance)')
    parser.add_argument('--cbecc-path', type=str,
                       help='Path to CBECC-Com.exe (optional)')
    parser.add_argument('--wine-path', type=str,
                       help='Path to Wine executable (optional)')
    
    args = parser.parse_args()
    
    # Show installation guide
    if args.install_guide:
        print_installation_guide()
        sys.exit(0)
    
    # Test installation
    if args.test:
        print("\n🔧 Testing CBECC-COM Installation...\n")
        try:
            bridge = CBECCWineBridge(
                cbecc_path=args.cbecc_path,
                wine_path=args.wine_path
            )
            results = bridge.test_installation()
            
            print("\n" + "="*80)
            print("Installation Test Results:")
            print("="*80)
            print(f"Platform: {results['platform']}")
            if results['wine_installed'] != 'N/A':
                print(f"Wine Installed: {'✅ Yes' if results['wine_installed'] else '❌ No'}")
                if results['wine_path'] != 'N/A':
                    print(f"Wine Path: {results['wine_path']}")
            print(f"CBECC Found: {'✅ Yes' if results['cbecc_found'] else '❌ No'}")
            if results['cbecc_path']:
                print(f"CBECC Path: {results['cbecc_path']}")
            if results['version']:
                print(f"CBECC Version: {results['version']}")
            print(f"Can Execute: {'✅ Yes' if results['can_execute'] else '❌ No'}")
            
            if results['errors']:
                print("\n⚠️  Errors:")
                for error in results['errors']:
                    print(f"  • {error}")
            
            print("="*80)
            
            if results['can_execute']:
                print("\n✅ Installation test PASSED - Ready to run simulations!")
                sys.exit(0)
            else:
                print("\n❌ Installation test FAILED")
                print("\nRun with --install-guide for setup instructions")
                sys.exit(1)
                
        except Exception as e:
            print(f"\n❌ Installation test failed: {str(e)}")
            print("\nRun with --install-guide for setup instructions")
            sys.exit(1)
    
    # Validate file
    if args.validate:
        try:
            bridge = CBECCWineBridge(
                cbecc_path=args.cbecc_path,
                wine_path=args.wine_path
            )
            print(f"\n🔍 Validating: {args.validate}\n")
            is_valid, errors = bridge.validate_cibd22x(args.validate)
            
            if is_valid:
                print("✅ Validation PASSED - File is ready for simulation")
                sys.exit(0)
            else:
                print("❌ Validation FAILED\n")
                print("Errors found:")
                for error in errors:
                    print(f"  • {error}")
                sys.exit(1)
                
        except Exception as e:
            print(f"❌ Validation error: {str(e)}")
            sys.exit(1)
    
    # Run simulation
    if args.input:
        if not args.output:
            print("❌ Error: --output directory required for simulation")
            sys.exit(1)
        
        try:
            bridge = CBECCWineBridge(
                cbecc_path=args.cbecc_path,
                wine_path=args.wine_path
            )
            
            result = bridge.run_simulation(
                cibd_path=args.input,
                output_dir=args.output,
                climate_zone=args.climate_zone,
                analysis_type=args.analysis
            )
            
            # Print results
            print("\n" + "="*80)
            print("Simulation Results:")
            print("="*80)
            print(f"Status: {'✅ SUCCESS' if result['success'] else '❌ FAILED'}")
            print(f"Execution Time: {result.get('execution_time', 0):.1f}s")
            print(f"Output Files: {len(result.get('output_files', []))}")
            
            if result.get('compliance_results'):
                comp = result['compliance_results']
                print(f"\nCompliance: {'✅ PASS' if comp.get('complies') else '❌ FAIL'}")
                print(f"TDU Proposed: {comp.get('tdu_proposed', 0):.2f}")
                print(f"TDU Standard: {comp.get('tdu_standard', 0):.2f}")
                print(f"TDU Margin: {comp.get('tdu_margin', 0):.2f}")
            
            if result.get('messages'):
                print("\nMessages:")
                for msg in result['messages'][:10]:  # Show first 10
                    print(f"  {msg}")
                if len(result['messages']) > 10:
                    print(f"  ... ({len(result['messages']) - 10} more messages)")
            
            print("="*80)
            
            sys.exit(0 if result['success'] else 1)
            
        except Exception as e:
            print(f"\n❌ Simulation error: {str(e)}")
            sys.exit(1)
    
    # No arguments provided
    if not any([args.test, args.install_guide, args.input, args.validate]):
        parser.print_help()
        sys.exit(0)

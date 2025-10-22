# CBECC Compliance Manager Review & Python Integration Plan

**Date:** October 21, 2025  
**Project:** ECO Tools Suite - CBECC Integration  
**Status:** Phase 1 Complete - Ready for Python Wrapper Development

---

## Executive Summary

This review consolidates the analysis of the CBECC-CLI ecosystem and compliance manager (BEMCmpMgr) DLL architecture. The foundation has been laid for building a comprehensive Python interface to CBECC for automated Title 24 compliance analysis within the EM-Tools ecosystem.

**Key Findings:**
- ✅ CBECC-CLI provides robust command-line interface for batch processing
- ✅ BEMCmpMgr DLL exposes comprehensive C API for deep integration
- ✅ Clear data flow: EMJSON → CIBD22X → CBECC → Results → EMJSON
- ✅ Multiple integration paths identified (CLI wrapper vs. DLL binding)
- 🔄 Next step: Build Python wrapper starting with CLI approach

---

## 1. Architecture Overview

### 1.1 Component Ecosystem

```
┌─────────────────────────────────────────────────────────┐
│                     EM-Tools (Python)                    │
│  ┌────────────┐  ┌────────────┐  ┌──────────────────┐  │
│  │   EMJSON   │  │  Geometry  │  │  Analysis        │  │
│  │   Schema   │  │  Validator │  │  Orchestrator    │  │
│  └─────┬──────┘  └──────┬─────┘  └────────┬─────────┘  │
│        │                │                  │             │
└────────┼────────────────┼──────────────────┼─────────────┘
         │                │                  │
         ▼                ▼                  ▼
┌─────────────────────────────────────────────────────────┐
│              Python CBECC Interface Layer                │
│  ┌───────────────────────────────────────────────────┐  │
│  │  CBECCEngine (Python)                             │  │
│  │  • Model translation (EMJSON → CIBD22X)          │  │
│  │  • Process orchestration                          │  │
│  │  • Result parsing & integration                   │  │
│  └──────────────┬────────────────────────────────────┘  │
└─────────────────┼───────────────────────────────────────┘
                  │
                  ▼
         ┌────────────────┐
         │ Integration Path│
         │   Decision      │
         └────────┬────────┘
                  │
        ┌─────────┴──────────┐
        │                    │
        ▼                    ▼
┌───────────────┐    ┌──────────────────┐
│ CLI Approach  │    │  DLL Approach    │
│ (Phase 1)     │    │  (Phase 2)       │
└───────┬───────┘    └────────┬─────────┘
        │                     │
        ▼                     ▼
┌─────────────────────────────────────────┐
│         CBECC-CLI Executable            │
│  • Command-line interface               │
│  • Batch processing                     │
│  • CSV options                          │
│  • Return codes & logging               │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│       BEMCmpMgr DLL (C/C++)            │
│  • Ruleset loading                      │
│  • Model processing                     │
│  • Compliance analysis                  │
│  • Result generation                    │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│      Simulation Engines                 │
│  • CSE (California Simulation Engine)   │
│  • EnergyPlus (via OpenStudio)         │
│  • DHW calculators                      │
└─────────────────────────────────────────┘
```

### 1.2 Data Flow

```
User Project (EMJSON)
    │
    ├─> Validation & Enrichment
    │       │
    │       ├─> Geometry validation
    │       ├─> Property completion
    │       └─> Metadata attachment
    │
    ├─> CIBD22X Export
    │       │
    │       └─> BEMBase-compliant XML
    │
    ├─> CBECC Analysis
    │       │
    │       ├─> Load BEMBase.bin
    │       ├─> Load Ruleset.bin (T24N_2022/2025)
    │       ├─> Load Weather (EPW)
    │       ├─> Execute simulations
    │       └─> Generate results
    │
    └─> Results Integration
            │
            ├─> Parse CSV summary
            ├─> Parse XML reports
            ├─> Extract compliance status
            └─> Update EMJSON with results
```

---

## 2. BEMCmpMgr DLL Architecture

### 2.1 Key Components Analyzed

#### **BEMCmpMgr.h** - Core API
- `CMX_LoadRuleset()` - Load compiled ruleset (.bin)
- `CMX_LoadDataModel()` - Initialize BEMBase data model
- `CMX_LoadModel()` - Load project file (CIBD22X)
- `CMX_PerformAnalysisCB_NonRes()` - Execute compliance analysis with callback
- `CMX_GenerateReport_CEC()` - Generate XML compliance reports
- `CMX_PopulateCSVResultSummary_NonRes()` - Extract result summaries

#### **BEMCmpMgrCom.h** - Commercial Building API
- `CMX_PerformAnalysis_CECNonRes()` - Primary analysis entry point
- `CMX_PerformBatchAnalysis_CECNonRes()` - Batch processing
- `CMX_PopulateResultsHeader_NonRes()` - CSV header generation
- `CMX_ExportCSVHourlyResults_CECNonRes()` - Hourly results export
- `CMX_GenerateWindowShades_CECNonRes()` - Geometry preprocessing

#### **CSERunMgr.h/cpp** - Simulation Engine Manager
- Manages CSE (California Simulation Engine) execution
- Handles multiple run types:
  - User models
  - Proposed design (with 4 orientations)
  - Standard design (baseline)
  - Design rating
  - HERS rating (residential)
- Process management via `exec_stream_t`
- Result file parsing (CSV, REP, ERR)

#### **EPlusRunMgr.h/cpp** - EnergyPlus Manager
- OpenStudio/EnergyPlus integration
- IDF generation and execution
- Result extraction and mapping
- Error handling and logging

#### **CUAC_Analysis.h/cpp** - Utility Rate Analysis
- California Utility Allowance Calculator integration
- Rate schedule downloads
- Bill calculation
- CUAC database import/export

### 2.2 Analysis Flow

```cpp
// Simplified analysis workflow from BEMCmpMgrCom.cpp

int CMX_PerformAnalysis_CECNonRes(
    const char* pszBEMBasePathFile,      // BEMBase.bin
    const char* pszRulesetPathFile,      // T24N_2022.bin
    const char* pszSimWeatherPath,       // EPW files
    const char* pszProcessingPath,       // Working directory
    const char* pszModelPathFile,        // Input .cibd22x
    const char* pszLogPathFile,          // Analysis log
    bool bLoadModelFile,                 // Load vs. use in-memory model
    const char* pszOptionsCSV,           // Analysis options
    char* pszErrorMsg,                   // Error output buffer
    char* pszResultsSummary              // Results output buffer
) {
    // 1. Initialize BEMProc
    BEMPX_InitData();
    
    // 2. Load BEMBase data model
    CMX_LoadDataModel(pszBEMBasePathFile);
    
    // 3. Load ruleset
    CMX_LoadRuleset(pszRulesetPathFile);
    
    // 4. Load project model
    if (bLoadModelFile)
        CMX_LoadModel(pszModelPathFile);
    
    // 5. Setup analysis parameters
    ParseOptionsCSV(pszOptionsCSV);
    
    // 6. Perform analysis
    iRetVal = PerformAnalysis_NonRes(
        pszSimWeatherPath,
        pszProcessingPath,
        ...
    );
    
    // 7. Generate results
    CMX_PopulateCSVResultSummary_NonRes(
        pszResultsSummary,
        pszModelPathFile
    );
    
    return iRetVal;
}
```

---

## 3. CBECC-CLI Interface

### 3.1 Command Structure

```bash
cbecc-cli22.exe [mode] [options]

Modes:
  -Compliance         # Full Title 24 compliance analysis
  -Translate          # Convert between formats (OSM/IDF/GBXML ↔ SDD)
  -CompileData        # Compile BEMBase text → binary
  -CompileRuleset     # Compile ruleset text → binary
  -BatchCompliance    # Batch processing from CSV

Key Options:
  -BEMBaseBin <path>           # Compiled data model
  -RulesetBin <path>           # Compiled ruleset
  -WeatherPath <path>          # Directory with EPW files
  -ProcessingPath <path>       # Working directory for outputs
  -ModelInput <file>           # Input model (.cibd22x)
  -OptionsCSV <csv_string>     # Analysis options as CSV
  -Verbose                     # Detailed logging
  -Silent                      # Suppress messages
```

### 3.2 Options CSV Format

```csv
Analysis options passed via -OptionsCSV:
"AnalysisType,3,ComplianceMarginPass,1,WeatherFileName,CZ03.epw,..."

Common Options:
- AnalysisType: 1=Preliminary, 2=Design, 3=Final
- ComplianceMarginPass: Pass threshold (typically 1%)
- WeatherFileName: Climate zone weather file
- LogAnalysisMsgs: 1=log all messages
- Silent: 1=no UI dialogs
- ReportGenVerbose: 1=detailed reports
- BypassCSESimulations: 1=skip simulations (testing)
- StoreHourlyResults: 1=export hourly data
```

### 3.3 Return Codes

```cpp
// From BEMCmpMgr.h

// Success
#define BEMAnal_CECRes_Success 0

// User Errors (1-99)
#define BEMAnal_CECRes_UserAbort 1
#define BEMAnal_CECRes_InputError 50
#define BEMAnal_CECRes_RulesetError 51

// Analysis Errors (100-199)  
#define BEMAnal_CECRes_SimulationError 100
#define BEMAnal_CECRes_CSEError 101
#define BEMAnal_CECRes_EnergyPlusError 102

// System Errors (200+)
#define BEMAnal_CECRes_FileNotFound 200
#define BEMAnal_CECRes_WriteError 201
#define BEMAnal_CECRes_MemoryError 202
```

### 3.4 Result Files

```
Output Directory Structure:
project_name/
├── project_name - AnalysisResults - Summary.csv    # Key metrics
├── project_name - AnalysisResults.xml              # Full report
├── project_name - AnalysisResults.pdf              # Formatted report
├── project_name.log                                # Detailed log
├── sim/                                            # Simulation files
│   ├── pp.cse                                      # Proposed model CSE input
│   ├── pp.csv                                      # Proposed results
│   ├── s.cse                                       # Standard model CSE input
│   ├── s.csv                                       # Standard results
│   └── *.err                                       # Error files
└── hourly/                                         # Hourly results (if requested)
    ├── pp_hourly.csv
    └── s_hourly.csv
```

---

## 4. Integration Strategy for Python

### 4.1 Phase 1: CLI Wrapper (Recommended Start)

**Advantages:**
- ✅ No C/C++ compilation required
- ✅ Works with existing CBECC installation
- ✅ Easier to debug and maintain
- ✅ Faster to implement
- ✅ Platform-independent (Windows primarily, but portable)

**Implementation:**

```python
# em_tools/engines/cbecc/cli_engine.py

from pathlib import Path
import subprocess
import csv
from typing import Dict, Optional, List
from dataclasses import dataclass

@dataclass
class CBECCConfig:
    """CBECC installation configuration"""
    cbecc_cli_path: Path
    bem_base_path: Path
    ruleset_path: Path
    weather_path: Path
    
    @classmethod
    def auto_detect(cls) -> 'CBECCConfig':
        """Auto-detect CBECC installation"""
        base_path = Path("C:/Program Files/CBECC/")
        
        return cls(
            cbecc_cli_path=base_path / "cbecc-cli22.exe",
            bem_base_path=base_path / "Data/Rulesets/T24N_2022/BEMBase.bin",
            ruleset_path=base_path / "Data/Rulesets/T24N_2022.bin",
            weather_path=base_path / "Data/EPW/"
        )

class CBECCCLIEngine:
    """
    Python wrapper for CBECC-CLI executable
    
    Provides programmatic access to Title 24 compliance analysis
    """
    
    def __init__(self, config: Optional[CBECCConfig] = None):
        self.config = config or CBECCConfig.auto_detect()
        self._validate_installation()
    
    def _validate_installation(self):
        """Verify CBECC files exist"""
        if not self.config.cbecc_cli_path.exists():
            raise FileNotFoundError(
                f"CBECC-CLI not found: {self.config.cbecc_cli_path}"
            )
    
    def run_compliance_analysis(
        self,
        cibd22_file: Path,
        output_dir: Path,
        climate_zone: int = 3,
        analysis_type: str = "final",
        options: Optional[Dict] = None
    ) -> Dict:
        """
        Execute Title 24 compliance analysis
        
        Args:
            cibd22_file: Input model file (.cibd22x)
            output_dir: Directory for processing and results
            climate_zone: CA climate zone (1-16)
            analysis_type: "preliminary", "design", or "final"
            options: Additional analysis options
        
        Returns:
            dict with:
                - success: bool
                - return_code: int
                - compliance_status: "Pass" | "Fail" | "Error"
                - compliance_margin: float (%)
                - energy_metrics: dict
                - error_message: str (if failed)
                - log_file: Path
                - result_files: dict of output file paths
        """
        
        # Prepare output directory
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Build options CSV
        options_csv = self._build_options_csv(
            climate_zone, analysis_type, options
        )
        
        # Construct command
        cmd = [
            str(self.config.cbecc_cli_path),
            "-Compliance",
            "-BEMBaseBin", str(self.config.bem_base_path),
            "-RulesetBin", str(self.config.ruleset_path),
            "-WeatherPath", str(self.config.weather_path),
            "-ProcessingPath", str(output_dir),
            "-ModelInput", str(cibd22_file),
            "-OptionsCSV", options_csv,
            "-Silent", "1",
            "-LogAnalysisMsgs", "1"
        ]
        
        # Execute CBECC
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout
            cwd=output_dir
        )
        
        # Parse results
        return self._parse_analysis_results(
            result, output_dir, cibd22_file
        )
    
    def _build_options_csv(
        self,
        climate_zone: int,
        analysis_type: str,
        options: Optional[Dict]
    ) -> str:
        """Build CSV options string"""
        
        # Map analysis types
        analysis_type_map = {
            "preliminary": 1,
            "design": 2,
            "final": 3
        }
        
        # Base options
        opts = {
            "AnalysisType": analysis_type_map.get(analysis_type, 3),
            "ComplianceMarginPass": 1,
            "WeatherFileName": f"CZ{climate_zone:02d}.epw",
            "LogAnalysisMsgs": 1,
            "Silent": 1,
            "ReportGenVerbose": 1,
            "StoreHourlyResults": 0
        }
        
        # Merge user options
        if options:
            opts.update(options)
        
        # Build CSV string
        csv_parts = []
        for key, value in opts.items():
            csv_parts.extend([key, str(value)])
        
        return ",".join(csv_parts)
    
    def _parse_analysis_results(
        self,
        result: subprocess.CompletedProcess,
        output_dir: Path,
        model_file: Path
    ) -> Dict:
        """Parse CBECC analysis results"""
        
        # Check return code
        return_code = result.returncode
        success = (return_code == 0)
        
        # Find result files
        model_name = model_file.stem
        summary_csv = output_dir / f"{model_name} - AnalysisResults - Summary.csv"
        results_xml = output_dir / f"{model_name} - AnalysisResults.xml"
        log_file = output_dir / f"{model_name}.log"
        
        # Parse CSV summary
        energy_metrics = {}
        compliance_status = "Error"
        compliance_margin = 0.0
        
        if summary_csv.exists():
            energy_metrics = self._parse_csv_summary(summary_csv)
            compliance_status = energy_metrics.get("ComplianceStatus", "Error")
            compliance_margin = energy_metrics.get("ComplianceMargin", 0.0)
        
        # Extract error message
        error_message = ""
        if not success:
            error_message = self._extract_error_message(
                result, log_file
            )
        
        return {
            "success": success,
            "return_code": return_code,
            "compliance_status": compliance_status,
            "compliance_margin": compliance_margin,
            "energy_metrics": energy_metrics,
            "error_message": error_message,
            "log_file": log_file,
            "result_files": {
                "summary_csv": summary_csv,
                "results_xml": results_xml,
                "log": log_file
            }
        }
    
    def _parse_csv_summary(self, csv_file: Path) -> Dict:
        """Parse CBECC CSV result summary"""
        
        metrics = {}
        
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                metrics = dict(row)
                break  # Only one data row
        
        # Convert numeric fields
        numeric_fields = [
            "ProposedTDV", "StandardTDV", "ComplianceMargin",
            "ProposedElec", "StandardElec",
            "ProposedGas", "StandardGas"
        ]
        
        for field in numeric_fields:
            if field in metrics:
                try:
                    metrics[field] = float(metrics[field])
                except ValueError:
                    pass
        
        return metrics
    
    def _extract_error_message(
        self,
        result: subprocess.CompletedProcess,
        log_file: Path
    ) -> str:
        """Extract error message from stderr or log"""
        
        # Try stderr first
        if result.stderr:
            return result.stderr.strip()
        
        # Fall back to log file
        if log_file.exists():
            with open(log_file, 'r') as f:
                lines = f.readlines()
                # Look for ERROR: lines
                errors = [
                    line.strip() 
                    for line in lines 
                    if "ERROR:" in line.upper()
                ]
                if errors:
                    return "\n".join(errors[-5:])  # Last 5 errors
        
        return "Unknown error"
    
    def run_batch_analysis(
        self,
        model_files: List[Path],
        output_dir: Path,
        **kwargs
    ) -> List[Dict]:
        """
        Run compliance analysis on multiple models
        
        Returns list of result dicts
        """
        
        results = []
        
        for model_file in model_files:
            try:
                result = self.run_compliance_analysis(
                    model_file, output_dir, **kwargs
                )
                results.append(result)
            except Exception as e:
                results.append({
                    "success": False,
                    "error_message": str(e),
                    "model_file": model_file
                })
        
        return results
    
    def run_climate_zone_study(
        self,
        cibd22_file: Path,
        output_dir: Path,
        climate_zones: Optional[List[int]] = None
    ) -> Dict[int, Dict]:
        """
        Run same model across multiple climate zones
        
        Returns dict mapping climate_zone → results
        """
        
        if climate_zones is None:
            climate_zones = range(1, 17)  # All 16 CA zones
        
        results = {}
        
        for cz in climate_zones:
            cz_output = output_dir / f"CZ{cz:02d}"
            
            result = self.run_compliance_analysis(
                cibd22_file,
                cz_output,
                climate_zone=cz
            )
            
            results[cz] = result
        
        return results
```

### 4.2 Phase 2: DLL Bindings (Advanced)

**For when deeper integration needed:**

```python
# em_tools/engines/cbecc/dll_engine.py

import ctypes
from ctypes import c_char_p, c_int, c_bool, c_void_p
from pathlib import Path

class BEMCmpMgrDLL:
    """
    Direct Python bindings to BEMCmpMgr DLL
    
    Provides low-level access to CBECC functionality
    """
    
    def __init__(self, dll_path: Path):
        self.dll = ctypes.CDLL(str(dll_path))
        self._setup_functions()
    
    def _setup_functions(self):
        """Define C function signatures"""
        
        # CMX_LoadRuleset
        self.dll.CMX_LoadRuleset.argtypes = [c_char_p, c_bool]
        self.dll.CMX_LoadRuleset.restype = c_bool
        
        # CMX_LoadDataModel
        self.dll.CMX_LoadDataModel.argtypes = [c_char_p, c_int, c_char_p]
        self.dll.CMX_LoadDataModel.restype = c_bool
        
        # CMX_LoadModel
        self.dll.CMX_LoadModel.argtypes = [
            c_char_p,  # BEMBase file
            c_char_p,  # Ruleset file
            c_char_p,  # Model file
            c_int,     # Max failures
            c_void_p,  # Failure counter
            c_bool,    # Suppress messages
            # ... additional parameters
        ]
        self.dll.CMX_LoadModel.restype = c_int
        
        # CMX_PerformAnalysisCB_NonRes
        self.dll.CMX_PerformAnalysisCB_NonRes.argtypes = [
            c_char_p,  # BEMBase path
            c_char_p,  # Ruleset path
            c_char_p,  # Weather path
            c_char_p,  # CmpMgr DLL path
            c_char_p,  # DHW weather
            c_char_p,  # Processing path
            c_char_p,  # Model path
            c_char_p,  # Log path
            c_char_p,  # UI version
            c_bool,    # Load model
            c_char_p,  # Options CSV
            c_char_p,  # Error msg buffer
            c_int,     # Error msg len
            c_bool,    # Display progress
            c_char_p,  # Results summary buffer
            c_int,     # Results summary len
            c_int,     # Security key index
            c_char_p,  # Security key
            c_void_p   # Callback function
        ]
        self.dll.CMX_PerformAnalysisCB_NonRes.restype = c_int
    
    def load_ruleset(self, ruleset_path: Path) -> bool:
        """Load compiled ruleset"""
        return self.dll.CMX_LoadRuleset(
            str(ruleset_path).encode('utf-8'),
            True  # Delete all objects
        )
    
    def perform_analysis(
        self,
        config: Dict,
        callback: Optional[Callable] = None
    ) -> Dict:
        """Execute compliance analysis via DLL"""
        
        # Prepare buffers
        error_msg = ctypes.create_string_buffer(2056)
        results_summary = ctypes.create_string_buffer(3200)
        
        # Setup callback if provided
        callback_func = None
        if callback:
            CALLBACK_TYPE = ctypes.CFUNCTYPE(c_int, c_int, c_int)
            callback_func = CALLBACK_TYPE(callback)
        
        # Call DLL function
        return_code = self.dll.CMX_PerformAnalysisCB_NonRes(
            config['bem_base_path'].encode('utf-8'),
            config['ruleset_path'].encode('utf-8'),
            config['weather_path'].encode('utf-8'),
            config['cmpmgr_dll_path'].encode('utf-8'),
            config['dhw_weather_path'].encode('utf-8'),
            config['processing_path'].encode('utf-8'),
            config['model_path'].encode('utf-8'),
            config['log_path'].encode('utf-8'),
            config['ui_version'].encode('utf-8'),
            True,  # Load model
            config['options_csv'].encode('utf-8'),
            error_msg,
            len(error_msg),
            False,  # No progress UI
            results_summary,
            len(results_summary),
            0,     # No security key
            None,
            callback_func
        )
        
        return {
            'return_code': return_code,
            'error_message': error_msg.value.decode('utf-8'),
            'results_summary': results_summary.value.decode('utf-8')
        }
```

### 4.3 Model Translation: EMJSON → CIBD22X

```python
# em_tools/translators/cbecc_translator.py

from lxml import etree as ET
from typing import Dict
from em_tools.schemas import EMJSONModel

class CBECCTranslator:
    """
    Translate EMJSON to CBECC CIBD22X format
    
    CIBD22X is XML-based building description format
    """
    
    def __init__(self, bem_base_path: Path):
        """Initialize with BEMBase for schema validation"""
        self.bem_base_path = bem_base_path
        # Could load BEMBase schema here for validation
    
    def translate(self, emjson: EMJSONModel) -> ET.Element:
        """
        Convert EMJSON to CIBD22X XML
        
        Returns lxml Element tree
        """
        
        # Root element
        root = ET.Element("SDDXML")
        root.set("xmlns", "http://www.lmn... aresystems.com/sdd")
        
        # Project info
        project = ET.SubElement(root, "Proj")
        ET.SubElement(project, "Name").text = emjson.project.name
        ET.SubElement(project, "SoftwareVersion").text = "EM-Tools v1.0"
        
        # Building
        bldg = self._translate_building(emjson.building)
        project.append(bldg)
        
        return root
    
    def _translate_building(self, building: Dict) -> ET.Element:
        """Translate building geometry and systems"""
        
        bldg = ET.Element("Bldg")
        ET.SubElement(bldg, "Name").text = building.get('name', 'Building')
        
        # Geometry
        area = building.get('floor_area', 0)
        ET.SubElement(bldg, "TotFlrArea").text = str(area)
        
        # Stories
        for story in building.get('stories', []):
            story_elem = self._translate_story(story)
            bldg.append(story_elem)
        
        # HVAC systems
        for system in building.get('hvac_systems', []):
            system_elem = self._translate_hvac(system)
            bldg.append(system_elem)
        
        return bldg
    
    def _translate_story(self, story: Dict) -> ET.Element:
        """Translate story geometry"""
        
        story_elem = ET.Element("Story")
        ET.SubElement(story_elem, "Name").text = story['name']
        ET.SubElement(story_elem, "Z").text = str(story.get('z', 0))
        ET.SubElement(story_elem, "FlrToFlrHgt").text = str(
            story.get('floor_to_floor_height', 13)
        )
        
        # Zones/Spaces
        for space in story.get('spaces', []):
            space_elem = self._translate_space(space)
            story_elem.append(space_elem)
        
        return story_elem
    
    def _translate_space(self, space: Dict) -> ET.Element:
        """Translate thermal zone/space"""
        
        space_elem = ET.Element("Spc")
        ET.SubElement(space_elem, "Name").text = space['name']
        ET.SubElement(space_elem, "FlrArea").text = str(space['area'])
        
        # Space type (for loads)
        space_type = space.get('space_type', 'Office')
        ET.SubElement(space_elem, "SpcFunc").text = self._map_space_type(
            space_type
        )
        
        # Envelope (walls, windows, etc.)
        for surface in space.get('surfaces', []):
            surface_elem = self._translate_surface(surface)
            space_elem.append(surface_elem)
        
        return space_elem
    
    def _translate_surface(self, surface: Dict) -> ET.Element:
        """Translate building surface (wall/roof/floor)"""
        
        # This is complex - need to map to CBECC construction types
        surf_type = surface.get('type', 'Wall')
        
        if surf_type == 'Wall':
            elem = ET.Element("ExtWall")
        elif surf_type == 'Roof':
            elem = ET.Element("Roof")
        elif surf_type == 'Floor':
            elem = ET.Element("FlrOnGrade")
        else:
            elem = ET.Element("UndgrndWall")
        
        ET.SubElement(elem, "Name").text = surface['name']
        ET.SubElement(elem, "Area").text = str(surface['area'])
        
        # Construction assembly
        construction = surface.get('construction', {})
        cons_name = construction.get('name', 'Default')
        ET.SubElement(elem, "ConsAssmRef").text = cons_name
        
        # Orientation
        if 'azimuth' in surface:
            ET.SubElement(elem, "Az").text = str(surface['azimuth'])
        
        # Fenestration (windows/skylights)
        for fenestration in surface.get('fenestrations', []):
            fen_elem = self._translate_fenestration(fenestration)
            elem.append(fen_elem)
        
        return elem
    
    def _translate_hvac(self, system: Dict) -> ET.Element:
        """Translate HVAC system"""
        
        hvac_elem = ET.Element("HVACSys")
        ET.SubElement(hvac_elem, "Name").text = system['name']
        
        # System type
        sys_type = system.get('type', 'PSZ-AC')
        ET.SubElement(hvac_elem, "Type").text = self._map_hvac_type(sys_type)
        
        # Efficiency
        if 'cooling_efficiency' in system:
            ET.SubElement(hvac_elem, "ClgEff").text = str(
                system['cooling_efficiency']
            )
        
        if 'heating_efficiency' in system:
            ET.SubElement(hvac_elem, "HtgEff").text = str(
                system['heating_efficiency']
            )
        
        # Zones served
        for zone_ref in system.get('zones_served', []):
            zone_elem = ET.SubElement(hvac_elem, "ZnSysRef")
            zone_elem.text = zone_ref
        
        return hvac_elem
    
    def _map_space_type(self, emjson_type: str) -> str:
        """Map EM-Tools space type to CBECC space function"""
        
        mapping = {
            'Office': 'Office - Open',
            'Conference': 'Conference/Meeting',
            'Corridor': 'Corridor - Office',
            'Classroom': 'Classroom - High School',
            # ... complete mapping
        }
        
        return mapping.get(emjson_type, 'Office - Open')
    
    def _map_hvac_type(self, emjson_type: str) -> str:
        """Map EM-Tools HVAC type to CBECC system type"""
        
        mapping = {
            'PSZ-AC': 'FPFC',  # Four-pipe fan coil
            'VAV': 'PVAVS',     # Packaged VAV with reheat
            'PTAC': 'PTAC',
            # ... complete mapping
        }
        
        return mapping.get(emjson_type, 'FPFC')
    
    def export_to_file(self, emjson: EMJSONModel, output_path: Path):
        """Export EMJSON as CIBD22X file"""
        
        tree = self.translate(emjson)
        
        # Pretty print XML
        xml_str = ET.tostring(
            tree,
            pretty_print=True,
            xml_declaration=True,
            encoding='UTF-8'
        )
        
        with open(output_path, 'wb') as f:
            f.write(xml_str)
```

---

## 5. Recommended Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)

**Week 1: Setup & Basic CLI Wrapper**
- [ ] Install and configure CBECC-CLI locally
- [ ] Create `CBECCConfig` with auto-detection
- [ ] Implement `CBECCCLIEngine` core class
- [ ] Basic `run_compliance_analysis()` method
- [ ] Result parsing from CSV

**Week 2: Model Translation**
- [ ] Design EMJSON → CIBD22X mapping
- [ ] Implement `CBECCTranslator` class
- [ ] Handle basic building geometry
- [ ] Handle space types and loads
- [ ] Validate against sample CIBD22X files

### Phase 2: Integration (Weeks 3-4)

**Week 3: End-to-End Workflow**
- [ ] EMJSON validation
- [ ] CIBD22X export
- [ ] CBECC execution
- [ ] Result parsing and integration
- [ ] Error handling and logging

**Week 4: Batch & Advanced Features**
- [ ] Batch processing implementation
- [ ] Climate zone studies
- [ ] Parametric analysis support
- [ ] Progress callbacks
- [ ] Hourly results handling

### Phase 3: Polish (Weeks 5-6)

**Week 5: Testing & Documentation**
- [ ] Unit tests for translator
- [ ] Integration tests with sample projects
- [ ] Performance testing
- [ ] API documentation
- [ ] Usage examples

**Week 6: Production Hardening**
- [ ] Error recovery strategies
- [ ] Timeout handling
- [ ] Resource cleanup
- [ ] Logging improvements
- [ ] User-facing documentation

### Phase 4 (Future): DLL Integration

**When CLI limitations become blockers:**
- Direct memory integration
- Custom analysis workflows
- Real-time progress updates
- Advanced debugging capabilities

---

## 6. Critical Implementation Notes

### 6.1 File Path Handling

CBECC has strict path requirements:
- All paths must be absolute
- Windows path separators (`\`)
- No spaces in some paths (use quotes)
- Processing directory must exist and be writable

```python
def prepare_paths(working_dir: Path) -> Dict[str, Path]:
    """Prepare all required paths for CBECC"""
    
    working_dir = working_dir.resolve()  # Make absolute
    working_dir.mkdir(parents=True, exist_ok=True)
    
    return {
        'processing': working_dir,
        'input': working_dir / 'input',
        'output': working_dir / 'output',
        'sim': working_dir / 'sim',
        'logs': working_dir / 'logs'
    }
```

### 6.2 Weather File Management

```python
def get_weather_file(climate_zone: int, weather_path: Path) -> Path:
    """Get appropriate weather file for climate zone"""
    
    epw_file = weather_path / f"CZ{climate_zone:02d}.epw"
    
    if not epw_file.exists():
        raise FileNotFoundError(
            f"Weather file not found for CZ {climate_zone}: {epw_file}"
        )
    
    return epw_file
```

### 6.3 Error Handling Strategy

```python
class CBECCError(Exception):
    """Base class for CBECC errors"""
    pass

class CBECCInstallationError(CBECCError):
    """CBECC installation not found or invalid"""
    pass

class CBECCAnalysisError(CBECCError):
    """Analysis failed"""
    def __init__(self, return_code: int, message: str):
        self.return_code = return_code
        self.message = message
        super().__init__(f"Analysis failed ({return_code}): {message}")

class CBECCTranslationError(CBECCError):
    """Model translation failed"""
    pass
```

### 6.4 Logging Integration

```python
import logging

logger = logging.getLogger('em_tools.cbecc')

class CBECCCLIEngine:
    def run_compliance_analysis(self, ...):
        logger.info(f"Starting CBECC analysis: {cibd22_file}")
        logger.debug(f"Climate Zone: {climate_zone}")
        logger.debug(f"Output Dir: {output_dir}")
        
        # ... execution ...
        
        if result.returncode != 0:
            logger.error(f"Analysis failed: {error_message}")
        else:
            logger.info(f"Analysis complete: {compliance_status}")
```

---

## 7. Testing Strategy

### 7.1 Unit Tests

```python
# tests/test_cbecc_translator.py

def test_basic_building_translation():
    """Test EMJSON → CIBD22X for simple building"""
    
    emjson = create_simple_building()
    translator = CBECCTranslator(bem_base_path)
    
    cibd22x = translator.translate(emjson)
    
    # Verify structure
    assert cibd22x.tag == "SDDXML"
    assert cibd22x.find(".//Bldg") is not None
    assert cibd22x.find(".//Story") is not None

def test_hvac_system_mapping():
    """Test HVAC system translation"""
    
    system = {
        'name': 'VAV System 1',
        'type': 'VAV',
        'cooling_efficiency': 3.2,
        'heating_efficiency': 0.8
    }
    
    translator = CBECCTranslator(bem_base_path)
    hvac_elem = translator._translate_hvac(system)
    
    assert hvac_elem.find("Type").text == "PVAVS"
    assert hvac_elem.find("ClgEff").text == "3.2"
```

### 7.2 Integration Tests

```python
# tests/test_cbecc_integration.py

def test_full_compliance_workflow(tmp_path):
    """Test complete EMJSON → CBECC → Results workflow"""
    
    # Setup
    emjson = load_test_project()
    translator = CBECCTranslator(bem_base_path)
    engine = CBECCCLIEngine()
    
    # Translate
    cibd22x_path = tmp_path / "test_project.cibd22x"
    translator.export_to_file(emjson, cibd22x_path)
    
    # Analyze
    result = engine.run_compliance_analysis(
        cibd22x_path,
        tmp_path / "output",
        climate_zone=3
    )
    
    # Verify
    assert result['success']
    assert result['compliance_status'] in ['Pass', 'Fail']
    assert 'energy_metrics' in result

def test_batch_climate_zones(tmp_path):
    """Test climate zone study"""
    
    engine = CBECCCLIEngine()
    cibd22x = create_test_model(tmp_path)
    
    results = engine.run_climate_zone_study(
        cibd22x,
        tmp_path / "cz_study",
        climate_zones=[1, 3, 6, 10, 16]
    )
    
    assert len(results) == 5
    for cz, result in results.items():
        assert result['success']
```

---

## 8. Documentation Requirements

### 8.1 API Documentation

```python
"""
CBECC Integration Module
========================

Provides Python interface to CBECC-CLI for Title 24 compliance analysis.

Quick Start
-----------

>>> from em_tools.engines.cbecc import CBECCCLIEngine
>>> from em_tools.translators import CBECCTranslator
>>>
>>> # Load your project
>>> project = load_emjson("my_building.emjson")
>>>
>>> # Translate to CBECC format
>>> translator = CBECCTranslator()
>>> cibd22x = translator.export(project, "temp/building.cibd22x")
>>>
>>> # Run compliance analysis
>>> engine = CBECCCLIEngine()
>>> result = engine.run_compliance_analysis(
...     cibd22x,
...     output_dir="results/",
...     climate_zone=3
... )
>>>
>>> print(f"Status: {result['compliance_status']}")
>>> print(f"Margin: {result['compliance_margin']:.1f}%")

Classes
-------

CBECCCLIEngine
    Main interface to CBECC-CLI executable
    
CBECCTranslator
    EMJSON to CIBD22X translation
    
CBECCConfig
    Configuration for CBECC installation

"""
```

### 8.2 User Guide

Create comprehensive guide covering:
- Installation requirements
- Configuration setup
- Basic usage examples
- Advanced workflows
- Troubleshooting
- Performance tips

---

## 9. Next Steps

### Immediate Actions

1. **Set up development environment**
   ```bash
   # Install CBECC-CLI
   # Download from California Energy Commission
   # Install to C:\Program Files\CBECC\
   
   # Setup Python project
   cd em-tools
   python -m venv venv
   venv\Scripts\activate
   pip install -e .[dev]
   ```

2. **Create initial project structure**
   ```
   em_tools/
   ├── engines/
   │   └── cbecc/
   │       ├── __init__.py
   │       ├── cli_engine.py
   │       ├── dll_engine.py  # Future
   │       └── config.py
   ├── translators/
   │   ├── __init__.py
   │   └── cbecc_translator.py
   └── tests/
       ├── test_cbecc_cli.py
       └── test_cbecc_translator.py
   ```

3. **Implement CBECCCLIEngine core**
   - Start with basic subprocess execution
   - Add result parsing
   - Test with sample CIBD22X files

4. **Build translator incrementally**
   - Start with minimal building model
   - Add geometry translation
   - Add HVAC systems
   - Validate against CBECC

### Decision Points

**Q: CLI wrapper vs. DLL binding first?**
**A:** CLI wrapper (Phase 1) - faster, easier, sufficient for most use cases

**Q: How complete should EMJSON → CIBD22X translation be initially?**
**A:** Focus on core building types (offices, retail) first, expand coverage iteratively

**Q: Where does CUAC integration fit?**
**A:** Phase 2 - after basic compliance analysis working

**Q: Cross-platform support?**
**A:** Windows-first (CBECC is Windows-only), consider Wine for Linux/Mac later

---

## 10. Success Criteria

### Minimum Viable Product (MVP)

- ✅ EMJSON project can be exported to CIBD22X
- ✅ CBECC-CLI can be executed programmatically
- ✅ Results can be parsed and returned as Python dict
- ✅ Compliance status and margin available
- ✅ Error messages are captured and reported
- ✅ Basic logging and debugging support

### Production Ready

- ✅ All California climate zones supported
- ✅ Batch processing implemented
- ✅ Comprehensive error handling
- ✅ Full test coverage (unit + integration)
- ✅ Complete API documentation
- ✅ User guide with examples
- ✅ Performance benchmarks documented
- ✅ Resource cleanup guaranteed

---

## 11. Resources & References

### Key Documentation

1. **CBECC-CLI User Manual** (California Energy Commission)
2. **BEMBase Schema Documentation** (data model reference)
3. **Title 24 Standards** (CA Energy Code)
4. **SDD Schema** (CIBD22X XML format)

### Code References

- `BEMCmpMgr.h` - Core API definitions
- `BEMCmpMgrCom.h` - Commercial analysis API
- `CSERunMgr.cpp` - CSE execution patterns
- Existing CIBD22X files - Translation examples

### Related Projects

- OpenStudio SDK (geometry modeling)
- EnergyPlus (simulation engine)
- CSE (California Simulation Engine)
- CUAC (Utility Allowance Calculator)

---

## Conclusion

The CBECC compliance manager analysis is complete and ready for Python integration. The recommended approach is to:

1. **Start with CLI wrapper** (fastest path to value)
2. **Build incrementally** (basic → comprehensive)
3. **Test continuously** (unit + integration)
4. **Document thoroughly** (API + user guide)
5. **Consider DLL binding later** (when CLI limitations emerge)

This foundation provides everything needed to begin implementation. The architecture is well-understood, integration points are clear, and a detailed roadmap exists.

**Ready to build the ECO Tools Suite CBECC integration!** 🚀

---

*Review completed: October 21, 2025*  
*Project: ECO Tools Suite*  
*Next: Begin Phase 1 implementation*

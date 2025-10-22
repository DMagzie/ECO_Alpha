# CBECC-CLI Analysis and Insights

## Executive Summary

The CBECC-CLI (California Building Energy Code Compliance - Command Line Interface) is a comprehensive command-line application for building energy code compliance analysis. This analysis examines the uploaded files to extract valuable technical information about the system's architecture, capabilities, and implementation details.

---

## 1. Project Overview

### Purpose
CBECC-CLI is a non-UI access tool that facilitates:
- Ruleset compilation
- Compliance analysis
- Batch processing of building energy models
- Data model compilation

### Code Base Information
- **Primary Language**: C++ (C++17 standard)
- **Platform**: Windows (x64 and Win32)
- **Build System**: Visual Studio (VS19, VS22, VS25 versions)
- **Creation Date**: October 18, 2024 (from source comments)
- **Latest Update**: February 12, 2025 (batch input generation)

---

## 2. Key Dependencies and Technologies

### Core Libraries
1. **Microsoft Foundation Classes (MFC)** - Dynamic linking
2. **Qt Framework** (Version 5.15.0)
   - Qt5Core/Qt5Cored libraries
   - Used for cross-platform string handling and file operations
3. **Boost** (Version 1.74.0)
   - Standard C++ library extensions

### Internal Dependencies
The application relies on several internal libraries:
- **BEMProc** (Building Energy Model Processor)
  - BEMProc22c.lib (Debug)
  - BEMProc22c.lib (Release)
- **BEMCmpMgr** (Building Energy Model Component Manager)
  - BEMCmpMgr22c.lib (Debug)
  - BEMCmpMgr22c.lib (Release)
- **BEMProcCompile** - Compilation utilities
- **BEMCmpMgrCom** - Component manager communications
- **OS_Wrap** - Operating system wrapper library

---

## 3. Primary Functions and Return Codes

### Core Functions
The application supports 5 primary function modes:

1. **Compile Data Model** (Function 1)
2. **Compile Ruleset** (Function 2)
3. **Compliance Analysis** (Function 3)
4. **Batch Runs** (Function 4)
5. **CUAC** (Function 5 - TBD)

### Return Code System
```
0     - Success
1     - Fatal Error: MFC initialization failed
2     - Fatal Error: GetModuleHandle failed
3     - Data model compilation failed
4     - Ruleset compilation failed
5     - Unrecognized primary function
6     - Batch processing error: unable to generate batch input/directives file
>1000 - Compliance analysis failed (1000 + return from CMX_PerformAnalysisCB_NonRes)
>2000 - Batch processing failed (2000 + return from CMX_PerformBatchAnalysis_CECNonRes)
```

---

## 4. Command-Line Interface

### Function 1: Compile Data Model
```bash
cbecc-cli22 -CompileDataModel \
  -sharedPath "C:/path/to/shared/" \
  -BEMBaseTxt "C:/path/to/BEMBase.txt" \
  -BEMEnumsTxt "C:/path/to/BEMEnums.txt" \
  -BEMBaseBin "C:/path/to/BEMBase.bin"
```

### Function 2: Compile Ruleset
```bash
cbecc-cli22 -CompileRuleset \
  -sharedPath "C:/path/to/shared/" \
  -BEMBaseBin "C:/path/to/BEMBase.bin" \
  -RulesetTxt "C:/path/to/Ruleset.txt" \
  -RulesetBin "C:/path/to/Ruleset.bin" \
  -LogFile "C:/path/to/log.out"
```

### Function 3: Compliance Analysis
```bash
cbecc-cli22 -Compliance \
  -BEMBaseBin "C:/path/to/BEMBase.bin" \
  -RulesetBin "C:/path/to/Ruleset.bin" \
  -WeatherPath "C:/path/to/EPW/" \
  -ProcessingPath "C:/path/to/run/" \
  -ModelInput "C:/path/to/model.cibd22" \
  -OptionsCSV "Silent,1,ReportGenVerbose,1,LogAnalysisMsgs,1,..."
```

---

## 5. Supported Code Types

The system supports multiple building energy code standards:

```cpp
enum CodeType {
    CT_T24N,    // California Title 24 Nonresidential
    CT_S901G,   // ASHRAE 90.1
    CT_ECBC,    // Energy Conservation Building Code (India)
    CT_360,     // ASHRAE/IES Standard 360
    CT_NumTypes
};
```

---

## 6. Configuration Options (CSV Format)

### Analysis Options
The application accepts numerous CSV-formatted options for compliance analysis:

```
Silent,1                          - Suppress verbose output
ReportGenVerbose,1               - Verbose reporting generation
LogAnalysisMsgs,1                - Log analysis messages
StoreBEMDetails,1                - Store BEM detailed data
AnalysisThruStep,8               - Run analysis through step 8
ModelRpt_ALL,1                   - Generate all model reports
SimulationStorage,4              - Simulation storage level
AnalysisStorage,3                - Analysis storage level
ExportHourlyResults_All,1        - Export all hourly results
PreAnalysisCheckPromptOption,3   - Pre-analysis check behavior
CompReportWarningOption,5        - Compliance report warning handling
AnalysisDialogTimeout,20         - Timeout for dialogs
```

---

## 7. Batch Processing Capabilities

### Batch Input Generation
The system can process multiple building models in batch mode with sophisticated features:

#### Key Capabilities:
1. **Multi-file Processing**: Iterate through directories to find project files
2. **Climate Zone Spanning**: Generate runs across all 16 California climate zones
3. **Subdirectory Support**: Optional recursive directory scanning
4. **Output Directory Management**: Automatic creation of output directories
5. **RunSet Files**: Support for pre-defined analysis action records

#### Batch File Structure:
```csv
Status,InputFile,OutputFile,DesignRatingName,EnergyCodeYearName,
WeatherFileName,AnalysisAction1,...,AnalysisAction20,Output,Options
```

### RunSet Integration
- Supports external RunSet definition files
- Allows specification of analysis actions per run
- Path resolution for PathFile columns (checks project dir, then RunSet dir)

---

## 8. File Handling and Processing

### Supported File Types
- **Input Models**: `.cibd22` (CBECC Input Building Description)
- **Data Models**: `.txt` (BEMBase text), `.bin` (BEMBase binary)
- **Rulesets**: `.txt` (ruleset text), `.bin` (ruleset binary)
- **Weather**: EPW files (EnergyPlus Weather format)
- **Results**: CSV, log files, XML (SDD), CSE files

### Result Summary CSV
The application generates a comprehensive result summary with:
- Analysis completion status
- Energy consumption metrics
- Compliance margins
- Warning and error counts
- Processing statistics

Maximum CSV result length: 3200 characters

---

## 9. Project Structure

### Solution Organization
The CBECC project is organized into multiple configurations:
- **VS19** (Visual Studio 2019)
- **VS22** (Visual Studio 2022) 
- **VS25** (Visual Studio 2025)

Each version maintains separate projects for:
- Commercial buildings (suffix 'c')
- Residential buildings (suffix 'r')
- Version-specific numbering (19, 22, 25)

### Component Projects
1. **OS_Wrap**: Operating system wrapper
2. **BEMProc**: Building energy model processor
3. **BEMCompiler**: BEM data compiler
4. **BEMCmpMgr**: Component manager
5. **BEMProcUI**: UI components (not used in CLI)
6. **CBECC-Com**: Commercial compliance interface
7. **CBECC-Res**: Residential compliance interface
8. **CBECC-CLI**: Command-line interface (this project)

---

## 10. Technical Implementation Details

### Memory Management
- Pre-allocated buffers for error messages (2056 bytes)
- CSV result summaries (3200 bytes)
- MFC dynamic linking for Windows integration

### String Handling
Dual string library approach:
- **QString** (Qt) for cross-platform file operations
- **CString** (MFC) for Windows-specific functionality
- **std::string** for standard C++ operations

### Path Resolution
Sophisticated path handling:
1. Absolute paths used directly
2. Relative paths checked in project directory first
3. Falls back to RunSet file directory
4. Full path validation before processing

### Error Handling
Multi-level error reporting:
1. Function return codes
2. Error message strings (passed by reference)
3. Processing messages for verbose output
4. Log file generation for detailed debugging

---

## 11. Build Configuration

### Compiler Settings
- **Platform Toolset**: v142 (Visual Studio 2019 compiler)
- **C++ Standard**: C++17 (`stdcpp17`)
- **Character Set**: MultiByte (for active configurations)
- **Optimization**: Whole Program Optimization enabled
- **Precompiled Headers**: Enabled (`pch.h`)

### Include Directories
```
../../vendor/boost_1_74_0
../../vendor/Qt_5.15.0/include
```

### Library Directories
```
../../bin/vendor/boost_1_74_0/lib
../../bin/vendor/Qt_5.15.0/lib-x64
../../bin/Debug_VC142x64      (Debug)
../../bin/Release_VC142x64    (Release)
```

### Preprocessor Definitions
- Debug: `_DEBUG;_CONSOLE`
- Release: `NDEBUG;_CONSOLE`
- Specific warnings disabled: `4996`

---

## 12. Key Functions and APIs

### Core BEM Functions
1. **BEMPX_CompileDataModel()**: Compiles BEM text definitions to binary
2. **BEMPX_CompileRuleset()**: Compiles ruleset text to binary format
3. **CMX_PerformAnalysisCB_NonRes()**: Performs nonresidential compliance analysis
4. **CMX_PerformBatchAnalysis_CECNonRes()**: Executes batch analysis runs

### Utility Functions
- **FileExists()**: Validates file existence
- **OKToWriteOrDeleteFile()**: Checks file write permissions
- **GenerateBatchInput()**: Creates batch processing definition files
- **ProcessCommandLineArgs()**: Parses command-line arguments

---

## 13. Integration with Existing Systems

### Compatibility with UI Versions
The CLI shares core libraries with:
- CBECC-Com (Commercial UI application)
- CBECC-Res (Residential UI application)
- BEMCompiler (Data model compiler)

### Data Flow
```
Input File (*.cibd22)
    ↓
BEM Data Model (*.bin)
    ↓
Ruleset (*.bin) + Weather (*.epw)
    ↓
Compliance Analysis Engine
    ↓
Results (CSV, XML, Logs)
```

---

## 14. Recent Development Activity

### Recent Updates (Based on Comments)
- **October 18, 2024**: Initial CLI implementation
- **January 19, 2025**: Compliance analysis function added
- **February 12, 2025**: Batch processing ported to CLI

### Active Development Areas
1. CLI-specific processing functions
2. Batch run generation and management
3. Non-UI access to core analysis functions
4. Climate zone iteration capabilities

---

## 15. Potential Integration Points for EM-Tools

### Data Export Opportunities
1. **CSV Result Summaries**: Already generated, could be parsed
2. **Analysis Logs**: Detailed processing information
3. **Model Reports**: Multiple output formats available

### Processing Hooks
1. **Pre-Analysis**: Custom data validation
2. **Post-Analysis**: Result aggregation and transformation
3. **Batch Processing**: Automated multi-model analysis

### API Access Points
1. Command-line invocation for automation
2. Shared library linking for direct integration
3. File-based data exchange (CSV, XML)

---

## 16. Technical Constraints and Considerations

### Platform Dependencies
- **Windows-specific**: Heavy use of MFC and Windows APIs
- **x64 Architecture**: Primary target (Win32 support appears legacy)
- **Visual Studio Required**: No alternative build system evident

### Library Requirements
- Qt 5.15.0 (specific version dependency)
- Boost 1.74.0 (specific version dependency)
- MFC runtime (dynamic linking required)

### File System Requirements
- Windows path separators (backslash)
- Long path support considerations
- Directory creation permissions needed for output

---

## 17. Recommendations for Further Investigation

### Priority Areas
1. **BEMProc Library Documentation**: Core processing engine details
2. **Ruleset File Format**: Understanding the ruleset structure
3. **Analysis Options**: Complete list of CSV options and their effects
4. **Security Keys**: Purpose of security key parameters in analysis

### Integration Opportunities
1. **Result Parsing**: Build parsers for CSV result summaries
2. **Batch Automation**: Leverage batch processing for large-scale analysis
3. **Data Pipeline**: Create connectors between CBECC and other tools
4. **Report Generation**: Extract and transform compliance reports

### Testing Needs
1. Command-line parameter validation
2. Error handling robustness
3. Large-scale batch processing performance
4. Cross-version compatibility (19/22/25)

---

## 18. Conclusions

### Key Findings
1. **Mature Codebase**: Well-structured with clear separation of concerns
2. **Comprehensive Functionality**: Supports full compliance workflow from CLI
3. **Batch Capable**: Strong support for automated, multi-model processing
4. **Multi-Standard**: Supports various building energy codes
5. **Windows-Centric**: Heavy platform dependencies limit portability

### Strategic Value
The CBECC-CLI represents a valuable foundation for:
- Automated compliance checking workflows
- Integration with broader building performance tools
- Batch processing of large building portfolios
- Programmatic access to California Title 24 compliance

### Next Steps
1. Obtain and review BEMProc library documentation
2. Test CLI with sample building models
3. Develop result parsing utilities
4. Explore integration with existing EM-Tools infrastructure
5. Document API surface for team reference

---

## Appendix: File Inventory

### Analyzed Files
1. **CBECC-CLI.cpp** (69KB) - Main implementation file
2. **CBECC-CLI.h** (512 bytes) - Header file
3. **CBECC-CLI.rc** (5KB) - Resource file
4. **CBECC-CLI.vcxproj** (28KB) - Project file
5. **CBECC-VS19.sln** (30KB) - VS2019 solution
6. **CBECC-VS22.sln** (37KB) - VS2022 solution
7. **CBECC.sln** (31KB) - Legacy solution

### Key Source File Metrics
- **Total Lines in CBECC-CLI.cpp**: ~1,255 lines
- **Main Function Lines**: ~195 lines
- **Batch Generation Function**: ~1,000+ lines
- **Comments**: Well-commented with function explanations

---

*Document Generated: October 21, 2025*
*Analysis of CBECC-CLI from California Energy Commission's Building Energy Code Compliance repository*

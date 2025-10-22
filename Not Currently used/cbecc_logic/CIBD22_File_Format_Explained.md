# CIBD22 File Format Deep Dive

**Date:** October 21, 2025  
**Project:** ECO Tools Suite - CBECC Integration  
**Topic:** Understanding CIBD22 vs CIBD22X File Formats

---

## Executive Summary

**CIBD** = **C**BECC **I**nput **B**uilding **D**escription

The file extensions indicate the **version lineage** and **format type**:

- **`.cibd22`** = CBECC Input Building Description for Title 24 **2022** standard
- **`.cibd22x`** = Same as above, but **XML format** (the 'x' = XML)
- **`.cibd19`** = For Title 24 **2019** standard
- **`.cibd16`** = For Title 24 **2016** standard

**Key Insight:** Both `.cibd22` and `.cibd22x` are used interchangeably in modern CBECC - they're both XML files. The system detects format by content, not extension.

---

## 1. File Format Evolution

### 1.1 Historical Context

```
Title 24 Evolution → File Format Evolution

2016 Standards → CBECC-Com 2016
    ├─ .cibd16 (XML)
    └─ Older binary formats (deprecated)

2019 Standards → CBECC-Com 2019  
    ├─ .cibd19 (XML)
    ├─ .cibd19x (explicit XML marker)
    └─ Backward compatible with .cibd16

2022 Standards → CBECC-Com 2022
    ├─ .cibd22 (XML)
    ├─ .cibd22x (explicit XML marker)
    └─ Backward compatible with .cibd19, .cibd16

2025 Standards → CBECC-Com 2025 (current)
    ├─ .cibd25 (XML)
    ├─ .cibd25x (explicit XML marker)
    └─ Backward compatible with all prior versions
```

### 1.2 Why Two Extensions?

From the code analysis, here's what's happening:

```cpp
// Pseudo-code from BEMProc_FileIO.cpp

bool BEMPX_ReadProjectFile(const char* fileName, ...) {
    
    // Detect file format by extension AND content
    QString sFileExt = GetFileExtension(fileName);
    
    // Check if XML format
    bool isXML = false;
    
    // Method 1: Extension check
    if (sFileExt.compare("xml", Qt::CaseInsensitive) == 0 ||
        sFileExt.endsWith('x', Qt::CaseInsensitive) ||  // .cibd22x
        sFileExt.endsWith('X', Qt::CaseInsensitive))    // .cibd22X
    {
        isXML = true;
    }
    
    // Method 2: Content sniffing (peek at first bytes)
    if (!isXML) {
        QFile file(fileName);
        if (file.open(QIODevice::ReadOnly)) {
            char buffer[5];
            file.read(buffer, 5);
            if (strncmp(buffer, "<?xml", 5) == 0) {
                isXML = true;  // It's XML even without 'x' extension
            }
            file.close();
        }
    }
    
    // Route to appropriate reader
    if (isXML) {
        return ReadXMLFile(fileName, ...);
    } else {
        return ReadBinaryFile(fileName, ...);  // Legacy
    }
}
```

**The Reality:**
- **Both `.cibd22` and `.cibd22x` are XML files**
- The system doesn't strictly enforce extension conventions
- Content detection is the primary method
- Extensions are more for **user/developer clarity** than technical requirement

---

## 2. File Format Structure

### 2.1 XML Format (Both .cibd22 and .cibd22x)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<SDDXML xmlns="http://www.lmnts.lbl.gov/sdd"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:schemaLocation="http://www.lmnts.lbl.gov/sdd CBECC-Com_2022.xsd">
    
    <!-- Ruleset Reference -->
    <RulesetFilename>T24N_2022.bin</RulesetFilename>
    
    <!-- Project Level -->
    <Proj>
        <Name>My Office Building</Name>
        <BldgEngyModelVersion>0.9.0</BldgEngyModelVersion>
        <CreateDate>2024-01-15T10:30:00</CreateDate>
        <ClimateZone>3</ClimateZone>
        <WeatherFile>CZ03.epw</WeatherFile>
        
        <!-- Building -->
        <Bldg>
            <Name>Building 1</Name>
            <TotFlrArea>50000</TotFlrArea>
            <BldgType>Office</BldgType>
            
            <!-- Stories -->
            <Story>
                <Name>Floor 1</Name>
                <Z>0</Z>
                <FlrToFlrHgt>13</FlrToFlrHgt>
                <FlrToCeilingHgt>10</FlrToCeilingHgt>
                
                <!-- Spaces (Thermal Zones) -->
                <Spc>
                    <Name>Core Zone</Name>
                    <SpcFunc>Office - Open</SpcFunc>
                    <FlrArea>10000</FlrArea>
                    <Volume>100000</Volume>
                    
                    <!-- Interior Walls -->
                    <IntWall>
                        <Name>Wall-1</Name>
                        <ConsAssmRef>Interior Wall - Standard</ConsAssmRef>
                        <Area>500</Area>
                    </IntWall>
                    
                    <!-- Exterior Walls -->
                    <ExtWall>
                        <Name>Wall-2</Name>
                        <ConsAssmRef>Exterior Wall - Mass</ConsAssmRef>
                        <Area>1000</Area>
                        <Az>180</Az>
                        <Tilt>90</Tilt>
                        
                        <!-- Windows -->
                        <Win>
                            <Name>Window-1</Name>
                            <FenConsRef>Window - U-0.32 SHGC-0.25</FenConsRef>
                            <Area>200</Area>
                        </Win>
                    </ExtWall>
                    
                </Spc>
            </Story>
            
            <!-- HVAC Systems -->
            <HVACSys>
                <Name>HVAC System 1</Name>
                <Type>PVAVS</Type>  <!-- Packaged VAV with reheat -->
                <ClgSrc>DXCoil</ClgSrc>
                <HtgSrc>HotWater</HtgSrc>
                
                <!-- Zone Systems (Terminal Units) -->
                <ZnSys>
                    <Name>VAV-1</Name>
                    <Type>VAVR</Type>
                    <ZnServedRef>Core Zone</ZnServedRef>
                </ZnSys>
            </HVACSys>
            
            <!-- Service Hot Water -->
            <DHWSys>
                <Name>DHW System 1</Name>
                <Type>CentralDHW</Type>
                
                <WtrHtr>
                    <Name>Water Heater 1</Name>
                    <Type>StorageTank</Type>
                    <EF>0.92</EF>
                    <Vol>100</Vol>
                </WtrHtr>
            </DHWSys>
            
        </Bldg>
    </Proj>
</SDDXML>
```

### 2.2 Key Structural Elements

```
Root: <SDDXML>
│
├─ <RulesetFilename> ........... Which ruleset to use
│
└─ <Proj> ...................... Project container
   │
   ├─ Project metadata
   │  ├─ Name
   │  ├─ ClimateZone
   │  ├─ WeatherFile
   │  └─ Analysis settings
   │
   └─ <Bldg> ................... Building container
      │
      ├─ Building metadata
      │  ├─ Name
      │  ├─ TotFlrArea
      │  └─ BldgType
      │
      ├─ <Story>+ .............. One or more stories
      │  │
      │  └─ <Spc>+ ............. Thermal zones/spaces
      │     │
      │     ├─ <IntWall>* ...... Interior walls
      │     ├─ <ExtWall>* ...... Exterior walls
      │     │  └─ <Win>* ....... Windows
      │     ├─ <UndgrndWall>* .. Below-grade walls
      │     ├─ <Roof>* ......... Roofs
      │     │  └─ <Skylt>* ..... Skylights
      │     ├─ <Flr>* .......... Interior floors
      │     ├─ <FlrOnGrade>* ... Slab floors
      │     ├─ <IntLtgSys>* .... Interior lighting
      │     └─ <ProcLd>* ....... Process loads
      │
      ├─ <HVACSys>+ ............ HVAC systems
      │  │
      │  ├─ System properties
      │  └─ <ZnSys>+ ........... Terminal units
      │
      ├─ <DHWSys>* ............. Service hot water
      │  │
      │  └─ <WtrHtr>+ .......... Water heaters
      │
      ├─ <PVArray>* ............ Photovoltaic arrays
      │
      └─ <BatterySystem>* ...... Battery storage
```

---

## 3. File I/O in BEMProc

### 3.1 Reading Process

```cpp
// High-level read workflow

int BEMPX_ReadProjectFile(const char* fileName, ...) {
    
    // 1. Determine file type
    QString fileExt = GetFileExtension(fileName);
    
    // 2. Read ruleset filename from file
    QString rulesetFile;
    bool foundRuleset = false;
    
    if (IsXMLFormat(fileName)) {
        // XML: Read <RulesetFilename> element
        ReadXMLFile(
            fileName,
            BEMFM_INPUT,
            0,  // version
            0,  // BEMProc index
            rulesetFile,  // OUTPUT: ruleset filename
            TRUE,  // Return ruleset name only
            ...
        );
        foundRuleset = !rulesetFile.isEmpty();
    }
    
    // 3. Load ruleset if found
    if (foundRuleset) {
        QString rulesetPath = ResolveRulesetPath(
            rulesetFile,
            GetDirectoryPath(fileName)
        );
        
        if (!BEMPX_LoadRuleset(rulesetPath)) {
            return -2;  // Ruleset load failed
        }
    }
    
    // 4. Now read the actual model data
    int objCount = 0, propCount = 0;
    int failureCount = 0;
    QStringList failures;
    
    if (IsXMLFormat(fileName)) {
        ReadXMLFile(
            fileName,
            BEMFM_INPUT,
            0,  // version
            0,  // BEMProc index
            rulesetFile,  // (already have this)
            FALSE,  // Now reading full model, not just ruleset
            MAX_FAILURES,
            &failureCount,
            bSupressMessages,
            NULL,  // obj index failures
            &failures,  // failure descriptions
            bLogDurations,
            TRUE,  // Store data
            &objCount, &propCount,  // Count created objects
            pStraightMap,  // Backward compatibility mappings
            pCompMap,
            pPropMap,
            NULL  // Class prefix filter
        );
    }
    
    // 5. Post-process
    BEMPX_DefaultProperties();  // Apply defaults
    BEMPX_ValidateModel();      // Run checks
    
    return 0;  // Success
}
```

### 3.2 Key Reading Features

```cpp
// From ReadXMLFile() implementation

void ReadXMLFile(...) {
    
    QXmlStreamReader xml(&file);
    
    // Navigate to data
    while (!xml.atEnd()) {
        xml.readNext();
        
        if (xml.isStartElement()) {
            QString elemName = xml.name().toString();
            
            // Special handling for RulesetFilename
            if (elemName == "RulesetFilename") {
                if (bReturnRulesetFilename) {
                    // Just return this and exit
                    ssRulesetFilename = xml.readElementText();
                    return;
                }
                continue;
            }
            
            // Map XML element name to BEMClass
            int classIdx = BEMPX_GetDBComponentID(
                elemName.toLocal8Bit().constData()
            );
            
            if (classIdx < 1) {
                // Check backward compatibility mappings
                classIdx = FindComponentMapping(
                    pCompMap,
                    elemName,
                    fileVersion
                );
            }
            
            if (classIdx > 0) {
                // Create or retrieve object
                BEMObject* obj = CreateObject(
                    classIdx,
                    xml.attributes(),
                    iFileMode
                );
                
                // Read properties from attributes
                ReadObjectAttributes(
                    xml,
                    obj,
                    pStraightMap,  // Property mappings
                    pPropMap
                );
                
                // Process child elements recursively
                ReadChildElements(xml, obj, ...);
            }
        }
    }
}
```

### 3.3 Writing Process

```cpp
// High-level write workflow

BOOL BEMPX_WriteProjectFile(
    const char* fileName,
    BOOL bIsInputMode,
    int iFileType,
    bool bWriteAllProperties,
    ...
) {
    // Always write as XML (modern approach)
    
    // 1. Open file
    QFile file(fileName);
    if (!file.open(QIODevice::WriteOnly | QIODevice::Text)) {
        return FALSE;
    }
    
    // 2. Create XML writer
    QXmlStreamWriter xml(&file);
    xml.setAutoFormatting(true);  // Pretty print
    xml.setAutoFormattingIndent(2);
    
    // 3. Write XML declaration
    xml.writeStartDocument();
    
    // 4. Write root element with namespace
    xml.writeStartElement("SDDXML");
    xml.writeAttribute("xmlns", "http://www.lmnts.lbl.gov/sdd");
    xml.writeAttribute("xmlns:xsi", 
                      "http://www.w3.org/2001/XMLSchema-instance");
    
    // 5. Write ruleset reference
    QString rulesetFile = BEMPX_GetRulesetFilename();
    if (!rulesetFile.isEmpty()) {
        xml.writeTextElement("RulesetFilename", rulesetFile);
    }
    
    // 6. Write all BEMObjects
    WriteAllObjects(xml, bIsInputMode, bWriteAllProperties);
    
    // 7. Close elements
    xml.writeEndElement();  // </SDDXML>
    xml.writeEndDocument();
    
    file.close();
    return TRUE;
}

void WriteAllObjects(
    QXmlStreamWriter& xml,
    bool bIsInputMode,
    bool bWriteAllProperties
) {
    // Iterate through all BEMClasses
    for (int classIdx = 1; classIdx <= numClasses; classIdx++) {
        
        BEMClass* cls = BEMPX_GetClass(classIdx);
        if (!cls) continue;
        
        // Iterate through all objects of this class
        for (int objIdx = 0; objIdx < cls->ObjectCount(); objIdx++) {
            
            BEMObject* obj = cls->GetObject(BEMO_User, objIdx);
            if (!obj) continue;
            
            // Write object
            WriteObject(xml, obj, bIsInputMode, bWriteAllProperties);
        }
    }
}

void WriteObject(
    QXmlStreamWriter& xml,
    BEMObject* obj,
    bool bIsInputMode,
    bool bWriteAllProperties
) {
    BEMClass* cls = obj->getClass();
    
    // Start element with class name
    xml.writeStartElement(cls->getShortName());
    
    // Write properties as attributes or child elements
    for (int propIdx = 0; propIdx < obj->getPropertiesSize(); propIdx++) {
        
        BEMProperty* prop = obj->getProperty(propIdx);
        BEMPropertyType* propType = prop->getType();
        
        // Determine if we should write this property
        bool shouldWrite = false;
        
        if (bWriteAllProperties) {
            shouldWrite = true;
        } else if (bIsInputMode) {
            // Only write user-defined properties in input mode
            shouldWrite = (prop->getDataStatus() == BEMS_UserDefined);
        } else {
            // Write all defined properties in detail mode
            shouldWrite = (prop->getDataStatus() != BEMS_Undefined);
        }
        
        if (shouldWrite && prop->IsDataValid()) {
            WriteProperty(xml, prop, propType);
        }
    }
    
    // Close element
    xml.writeEndElement();
}

void WriteProperty(
    QXmlStreamWriter& xml,
    BEMProperty* prop,
    BEMPropertyType* propType
) {
    QString propName = propType->getShortName();
    QString value;
    
    // Convert property value to string
    switch (propType->getDataType()) {
        case BEMP_Int:
            value = QString::number(prop->getInt());
            break;
        
        case BEMP_Flt:
            value = QString::number(prop->getDouble(), 'g', 10);
            break;
        
        case BEMP_Str:
            value = prop->getString();
            break;
        
        case BEMP_Obj:
            // Object reference - write object name
            BEMObject* refObj = prop->getObj();
            if (refObj) {
                value = refObj->getName();
            }
            break;
        
        case BEMP_Sym:
            // Symbolic value - write symbol string
            value = prop->getSymbolString();
            break;
    }
    
    // Write as attribute (most common)
    xml.writeAttribute(propName, value);
    
    // Alternative: Write as child element
    // xml.writeTextElement(propName, value);
}
```

---

## 4. File Extension Best Practices

### 4.1 What Should Python Use?

**Recommendation: Use `.cibd22x` for new files**

Reasons:
1. **Explicit format marker** - The 'x' clearly indicates XML
2. **Follows modern convention** - Most recent CBECC versions prefer this
3. **Self-documenting** - Anyone seeing the file knows it's XML
4. **Future-proof** - If binary formats return, distinction is clear

```python
# em_tools/translators/cbecc_translator.py

class CBECCTranslator:
    
    def export_to_file(
        self,
        emjson: EMJSONModel,
        output_path: Path,
        use_explicit_xml_extension: bool = True
    ) -> Path:
        """Export EMJSON as CBECC XML file"""
        
        # Ensure proper extension
        if use_explicit_xml_extension:
            # Use .cibd22x to be explicit
            if not str(output_path).endswith('.cibd22x'):
                output_path = output_path.with_suffix('.cibd22x')
        else:
            # Use .cibd22 (also valid)
            if not str(output_path).endswith('.cibd22'):
                output_path = output_path.with_suffix('.cibd22')
        
        # Generate XML
        xml_tree = self.translate(emjson)
        
        # Write to file
        xml_str = ET.tostring(
            xml_tree,
            pretty_print=True,
            xml_declaration=True,
            encoding='UTF-8'
        )
        
        with open(output_path, 'wb') as f:
            f.write(xml_str)
        
        return output_path
```

### 4.2 Reading Strategy

```python
class CBECCReader:
    
    def read_file(self, file_path: Path) -> EMJSONModel:
        """
        Read CBECC file (auto-detect format)
        
        Accepts:
        - .cibd22
        - .cibd22x
        - .cibd19, .cibd19x
        - .xml
        """
        
        # Try to read as XML
        try:
            tree = ET.parse(str(file_path))
            root = tree.getroot()
            
            # Verify it's SDDXML
            if root.tag.endswith('SDDXML'):
                return self._read_xml(root)
            else:
                raise ValueError(
                    f"Unknown root element: {root.tag}"
                )
        
        except ET.ParseError as e:
            raise ValueError(
                f"File is not valid XML: {e}"
            )
```

---

## 5. Version Detection & Migration

### 5.1 Detecting File Version

```python
def detect_file_version(file_path: Path) -> str:
    """
    Detect which Title 24 version the file targets
    
    Returns: "2016", "2019", "2022", "2025", etc.
    """
    
    # Method 1: Extension
    ext = file_path.suffix.lower()
    if 'cibd25' in ext:
        return "2025"
    elif 'cibd22' in ext:
        return "2022"
    elif 'cibd19' in ext:
        return "2019"
    elif 'cibd16' in ext:
        return "2016"
    
    # Method 2: Read ruleset reference from file
    tree = ET.parse(str(file_path))
    root = tree.getroot()
    
    ruleset_elem = root.find('.//RulesetFilename')
    if ruleset_elem is not None:
        ruleset = ruleset_elem.text
        
        if 'T24N_2025' in ruleset or 'T24R_2025' in ruleset:
            return "2025"
        elif 'T24N_2022' in ruleset or 'T24R_2022' in ruleset:
            return "2022"
        elif 'T24N_2019' in ruleset or 'T24R_2019' in ruleset:
            return "2019"
        elif 'T24N_2016' in ruleset or 'T24R_2016' in ruleset:
            return "2016"
    
    # Method 3: Schema namespace
    namespace = root.get('{http://www.w3.org/2001/XMLSchema-instance}schemaLocation')
    if namespace:
        if '2025' in namespace:
            return "2025"
        elif '2022' in namespace:
            return "2022"
        elif '2019' in namespace:
            return "2019"
        elif '2016' in namespace:
            return "2016"
    
    # Default to latest
    return "2025"
```

### 5.2 Handling Version Differences

```python
class CBECCVersionAdapter:
    """
    Handle differences between CBECC versions
    
    Implements property/component mappings similar to
    BEMStraightMap, BEMCompMap, BEMPropMap in C++
    """
    
    def __init__(self):
        self.property_mappings = self._load_property_mappings()
        self.component_mappings = self._load_component_mappings()
    
    def _load_property_mappings(self) -> Dict:
        """
        Property name changes between versions
        
        Equivalent to BEMStraightMap in C++
        """
        return {
            # Format: (old_name, version) -> new_name
            ('Proj:BldgLoc', '2016'): 'Proj:ClimateZone',
            ('Spc:ElevEscalSchRef', '2019'): 'Spc:ElevSchRef',
            ('IntLtgSys:AllowBoardWd', '2019'): 'IntLtgSys:AllowLen',
            # ... hundreds more
        }
    
    def _load_component_mappings(self) -> Dict:
        """
        Component type changes between versions
        
        Equivalent to BEMCompMap in C++
        """
        return {
            # Format: (old_type, version) -> new_type
            ('HVACSys', '2016'): 'AirSys',
            ('ThermalZone', '2019'): 'Spc',
            # ... more
        }
    
    def migrate_to_current(
        self,
        xml_tree: ET.Element,
        from_version: str
    ) -> ET.Element:
        """
        Migrate old file to current version format
        
        Returns: Updated XML tree
        """
        
        # Walk tree and apply mappings
        for elem in xml_tree.iter():
            
            # Check component mappings
            old_tag = elem.tag
            mapping_key = (old_tag, from_version)
            
            if mapping_key in self.component_mappings:
                new_tag = self.component_mappings[mapping_key]
                elem.tag = new_tag
            
            # Check property mappings
            for attr_name, attr_value in list(elem.attrib.items()):
                prop_key = (f"{elem.tag}:{attr_name}", from_version)
                
                if prop_key in self.property_mappings:
                    new_prop_name = self.property_mappings[prop_key]
                    
                    # Remove old attribute
                    del elem.attrib[attr_name]
                    
                    # Add new attribute
                    elem.set(new_prop_name.split(':')[1], attr_value)
        
        # Update ruleset reference
        ruleset_elem = xml_tree.find('.//RulesetFilename')
        if ruleset_elem is not None:
            # Update to current version ruleset
            ruleset_elem.text = ruleset_elem.text.replace(
                from_version, '2025'
            )
        
        return xml_tree
```

---

## 6. Python Integration Summary

### 6.1 File Naming Convention

```python
from enum import Enum
from pathlib import Path

class CBECCFileExtension(Enum):
    """Standard CBECC file extensions"""
    
    # XML format (recommended)
    CIBD25X = ".cibd25x"  # Title 24 2025
    CIBD22X = ".cibd22x"  # Title 24 2022
    CIBD19X = ".cibd19x"  # Title 24 2019
    
    # XML format (alternative)
    CIBD25 = ".cibd25"
    CIBD22 = ".cibd22"
    CIBD19 = ".cibd19"
    
    # Generic
    XML = ".xml"

# Usage
def get_output_filename(
    base_name: str,
    version: str = "2022",
    explicit_xml: bool = True
) -> Path:
    """Generate appropriate CBECC filename"""
    
    if explicit_xml:
        ext = f".cibd{version[-2:]}x"
    else:
        ext = f".cibd{version[-2:]}"
    
    return Path(base_name).with_suffix(ext)

# Examples:
# get_output_filename("MyBuilding", "2022", True)  → MyBuilding.cibd22x
# get_output_filename("MyBuilding", "2022", False) → MyBuilding.cibd22
# get_output_filename("MyBuilding", "2025", True)  → MyBuilding.cibd25x
```

### 6.2 Complete I/O Example

```python
# em_tools/translators/cbecc_io.py

class CBECCIO:
    """
    Complete CBECC file I/O handling
    
    Features:
    - Auto-detect format
    - Version migration
    - Validation
    - Error handling
    """
    
    def __init__(self, target_version: str = "2022"):
        self.target_version = target_version
        self.translator = CBECCTranslatorV2(...)
        self.reader = CBECCReader(...)
        self.adapter = CBECCVersionAdapter()
    
    def read_any_version(
        self,
        file_path: Path
    ) -> Tuple[EMJSONModel, str]:
        """
        Read CBECC file of any version
        
        Returns: (emjson_model, original_version)
        """
        
        # Detect version
        file_version = detect_file_version(file_path)
        
        # Parse XML
        tree = ET.parse(str(file_path))
        root = tree.getroot()
        
        # Migrate if needed
        if file_version != self.target_version:
            root = self.adapter.migrate_to_current(
                root,
                file_version
            )
        
        # Convert to EMJSON
        emjson = self.reader._read_xml(root)
        
        return emjson, file_version
    
    def write_current_version(
        self,
        emjson: EMJSONModel,
        output_path: Path
    ) -> Path:
        """
        Write EMJSON as current version CBECC file
        """
        
        # Ensure proper extension
        if not str(output_path).endswith(f'.cibd{self.target_version[-2:]}x'):
            output_path = output_path.with_suffix(
                f'.cibd{self.target_version[-2:]}x'
            )
        
        # Translate and write
        return self.translator.export_to_file(
            emjson,
            output_path
        )
    
    def validate_file(self, file_path: Path) -> List[str]:
        """
        Validate CBECC file
        
        Returns: List of validation errors/warnings
        """
        
        errors = []
        
        # Check file exists
        if not file_path.exists():
            errors.append(f"File not found: {file_path}")
            return errors
        
        # Check extension
        ext = file_path.suffix.lower()
        valid_extensions = [
            '.cibd22', '.cibd22x',
            '.cibd19', '.cibd19x',
            '.cibd25', '.cibd25x',
            '.xml'
        ]
        
        if ext not in valid_extensions:
            errors.append(
                f"Unexpected extension '{ext}'. "
                f"Valid: {', '.join(valid_extensions)}"
            )
        
        # Try to parse XML
        try:
            tree = ET.parse(str(file_path))
            root = tree.getroot()
            
            # Check root element
            if not root.tag.endswith('SDDXML'):
                errors.append(
                    f"Invalid root element: {root.tag}. "
                    "Expected: SDDXML"
                )
            
            # Check for ruleset reference
            ruleset = root.find('.//RulesetFilename')
            if ruleset is None:
                errors.append(
                    "Missing RulesetFilename element"
                )
            
            # Check for at least one building
            bldg = root.find('.//Bldg')
            if bldg is None:
                errors.append(
                    "No building (Bldg element) found"
                )
        
        except ET.ParseError as e:
            errors.append(f"XML parse error: {e}")
        
        return errors
```

---

## 7. Key Takeaways for Python Development

### ✅ Critical Points

1. **Both `.cibd22` and `.cibd22x` are XML** - Don't write separate parsers
   
2. **Use `.cibd22x` for new files** - Be explicit about XML format

3. **Content detection matters** - Extension is a hint, not gospel

4. **Version numbers map to Title 24 years**:
   - `.cibd25x` = 2025 standards
   - `.cibd22x` = 2022 standards
   - `.cibd19x` = 2019 standards

5. **Backward compatibility is built-in** - CBECC handles old files automatically

6. **Python should:**
   - Generate `.cibd22x` or `.cibd25x` files
   - Read any version (`.cibd16`, `.cibd19`, `.cibd22`, `.cibd25`)
   - Validate XML structure
   - Not worry too much about extension as long as it's XML

### 📝 Recommended Approach

```python
# Simple, practical approach:

# WRITING (EMJSON → CBECC):
# - Always output as .cibd22x (or .cibd25x for latest)
# - Use proper XML with UTF-8 encoding
# - Include RulesetFilename element
# - Pretty-print for human readability

# READING (CBECC → EMJSON):
# - Accept any .cibd* or .xml extension
# - Parse as XML
# - Validate root element is SDDXML
# - Handle version differences gracefully
# - Provide warnings for deprecated properties
```

---

*Document created: October 21, 2025*  
*Clarifies: CIBD22 vs CIBD22X file format relationship*  
*Purpose: Guide Python integration development*

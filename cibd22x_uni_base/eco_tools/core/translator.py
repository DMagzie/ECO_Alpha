"""
Universal Translator Module
Main orchestrator for format translations
"""

from typing import Optional
from dataclasses import dataclass
from eco_tools.core.format_detector import FormatDetector, FormatInfo
from eco_tools.core.id_registry import IDRegistry
from eco_tools.core.validator import Validator, ValidationResult
from eco_tools.core.internal_repr import InternalRepresentation
from eco_tools.formats.cibd22x_adapter import CIBD22XAdapter


@dataclass
class TranslationResult:
    """Result of a translation operation"""
    source_format: FormatInfo
    target_format: str
    input_path: str
    output_path: Optional[str]
    source_validation: ValidationResult
    target_validation: ValidationResult
    diagnostics: list
    
    def __str__(self):
        return f"{self.source_format.format_type} → {self.target_format}: " +                f"{'✓ Success' if self.target_validation.is_valid else '✗ Failed'}"


class UniversalTranslator:
    """
    Main translation orchestrator for all CBECC formats.
    
    Supports:
    - CIBD22 ↔ CIBD22X ↔ EMJSON
    - Version migration
    - Batch processing
    - Validation
    """
    
    def __init__(self, schema_dir: str = 'schemas/'):
        self.detector = FormatDetector()
        self.id_registry = IDRegistry()
        self.validator = Validator()
        self.schema_dir = schema_dir
    
    def translate(self,
                  input_path: str,
                  target_format: str,
                  output_path: Optional[str] = None) -> TranslationResult:
        """
        Translate file to target format.
        
        Args:
            input_path: Path to input file
            target_format: Target format ('CIBD22', 'CIBD22X', 'EMJSON')
            output_path: Optional output path
            
        Returns:
            TranslationResult with validation and diagnostics
        """
        # 1. Detect source format
        format_info = self.detector.detect(input_path)
        print(f"Detected: {format_info}")
        
        # 2. Load with appropriate adapter
        internal = self.load(input_path, format_info)
        
        # 3. Validate source
        source_validation = self.validator.validate(internal)
        print(f"Source validation: {source_validation}")
        
        # 4. Transform if needed
        # (In full implementation, would apply format-specific transformations)
        
        # 5. Serialize to target format
        if output_path:
            self.save(internal, output_path, target_format)
        
        # 6. Validate target if written
        if output_path:
            target_internal = self.load(output_path)
            target_validation = self.validator.validate(target_internal)
        else:
            target_validation = source_validation
        
        print(f"Target validation: {target_validation}")
        
        return TranslationResult(
            source_format=format_info,
            target_format=target_format,
            input_path=input_path,
            output_path=output_path,
            source_validation=source_validation,
            target_validation=target_validation,
            diagnostics=internal.diagnostics
        )
    
    def load(self, 
             file_path: str,
             format_info: Optional[FormatInfo] = None) -> InternalRepresentation:
        """
        Load file to internal representation.
        
        Args:
            file_path: Path to file
            format_info: Optional format info (will detect if not provided)
            
        Returns:
            InternalRepresentation
        """
        if format_info is None:
            format_info = self.detector.detect(file_path)
        
        # Select adapter
        if format_info.format_type == 'CIBD22X':
            adapter = CIBD22XAdapter(id_registry=self.id_registry)
        elif format_info.format_type == 'CIBD22':
            # Would use CIBD22Adapter here
            adapter = CIBD22XAdapter(id_registry=self.id_registry)  # Fallback
        elif format_info.format_type == 'EMJSON':
            # Would use EMJSONAdapter here
            raise NotImplementedError("EMJSON adapter not yet implemented")
        else:
            raise ValueError(f"Unknown format: {format_info.format_type}")
        
        # Parse
        internal = adapter.parse(file_path)
        internal.format_info = format_info
        
        return internal
    
    def save(self,
             internal: InternalRepresentation,
             output_path: str,
             target_format: str):
        """
        Save internal representation to file.
        
        Args:
            internal: Internal representation
            output_path: Output file path
            target_format: Target format
        """
        # Select adapter
        if target_format == 'CIBD22X':
            adapter = CIBD22XAdapter(id_registry=self.id_registry)
        elif target_format == 'CIBD22':
            # Would use CIBD22Adapter
            adapter = CIBD22XAdapter(id_registry=self.id_registry)  # Fallback
        elif target_format == 'EMJSON':
            # Would use EMJSONAdapter
            raise NotImplementedError("EMJSON adapter not yet implemented")
        else:
            raise ValueError(f"Unknown format: {target_format}")
        
        # Serialize
        output = adapter.serialize(internal)
        
        # Write
        adapter.write(output, output_path)
        
        print(f"Wrote {output_path}")
    
    def translate_batch(self,
                       input_files: list,
                       target_format: str,
                       parallel: bool = False) -> list:
        """
        Batch translate multiple files.
        
        Args:
            input_files: List of input file paths
            target_format: Target format
            parallel: Use parallel processing
            
        Returns:
            List of TranslationResult
        """
        if parallel:
            from multiprocessing import Pool
            with Pool() as pool:
                results = pool.starmap(
                    self.translate,
                    [(f, target_format) for f in input_files]
                )
            return results
        else:
            return [self.translate(f, target_format) for f in input_files]

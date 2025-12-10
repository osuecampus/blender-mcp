"""
Unified GLTF Conversion Pipeline

Single entry point for converting any supported format to optimized GLTF/GLB.
Automatically detects input format and applies appropriate conversion + optimization.

Usage:
    from tools.gltf_pipeline import convert_to_gltf
    
    output, report = convert_to_gltf("model.obj")
    output, report = convert_to_gltf("character.fbx", optimize=True)
    output, report = convert_to_gltf("scene.gltf", output="optimized.glb")
"""

import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

from .obj_converter import OBJConverter, obj_to_gltf
from .fbx_converter import FBXConverter, fbx_to_gltf, FBXImportSettings, GLTFExportSettings
from .optimizer import optimize_gltf, OptimizationSettings, MeshOptimizer, MaterialOptimizer
from .validator import validate_gltf, ValidationReport


# Supported input formats
SUPPORTED_FORMATS = {
    '.obj': 'OBJ (Wavefront)',
    '.fbx': 'FBX (Autodesk)',
    '.gltf': 'GLTF (already canonical)',
    '.glb': 'GLB (already canonical)',
}


@dataclass
class ConversionReport:
    """Complete report of a conversion operation"""
    success: bool = False
    input_path: str = ""
    input_format: str = ""
    output_path: str = ""
    
    # Stats from conversion
    conversion_stats: Dict[str, Any] = field(default_factory=dict)
    
    # Stats from optimization
    optimization_stats: Dict[str, Any] = field(default_factory=dict)
    
    # Validation result
    validation: Optional[ValidationReport] = None
    
    # Issues encountered
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "input_path": self.input_path,
            "input_format": self.input_format,
            "output_path": self.output_path,
            "conversion_stats": self.conversion_stats,
            "optimization_stats": self.optimization_stats,
            "validation": self.validation.to_dict() if self.validation else None,
            "warnings": self.warnings,
            "errors": self.errors,
        }
    
    def summary(self) -> str:
        lines = [
            f"Conversion Report",
            f"================",
            f"Input:  {self.input_path} ({self.input_format})",
            f"Output: {self.output_path}",
            f"Status: {'SUCCESS' if self.success else 'FAILED'}",
        ]
        
        if self.conversion_stats:
            lines.append(f"\nConversion Stats:")
            for key, value in self.conversion_stats.items():
                lines.append(f"  {key}: {value}")
        
        if self.optimization_stats:
            lines.append(f"\nOptimization Stats:")
            for key, value in self.optimization_stats.items():
                lines.append(f"  {key}: {value}")
        
        if self.validation:
            lines.append(f"\nValidation: {'PASSED' if self.validation.valid else 'FAILED'}")
            lines.append(f"  Errors: {self.validation.error_count}, Warnings: {self.validation.warning_count}")
        
        if self.warnings:
            lines.append(f"\nWarnings ({len(self.warnings)}):")
            for w in self.warnings[:10]:  # Limit output
                lines.append(f"  ⚠️ {w}")
            if len(self.warnings) > 10:
                lines.append(f"  ... and {len(self.warnings) - 10} more")
        
        if self.errors:
            lines.append(f"\nErrors ({len(self.errors)}):")
            for e in self.errors:
                lines.append(f"  ❌ {e}")
        
        return "\n".join(lines)


def detect_format(filepath: str) -> Optional[str]:
    """Detect file format from extension"""
    ext = Path(filepath).suffix.lower()
    return ext if ext in SUPPORTED_FORMATS else None


def convert_to_gltf(
    input_path: str,
    output_path: Optional[str] = None,
    binary: bool = True,
    optimize: bool = True,
    validate: bool = True,
    optimization_settings: Optional[OptimizationSettings] = None,
) -> Tuple[str, ConversionReport]:
    """
    Convert any supported format to GLTF/GLB.
    
    This is the main entry point for the conversion pipeline.
    
    Args:
        input_path: Path to input file (OBJ, FBX, GLTF, GLB)
        output_path: Output path (default: same name with .glb/.gltf)
        binary: Output GLB (True) or GLTF (False)
        optimize: Apply optimization pass
        validate: Validate output file
        optimization_settings: Custom optimization settings
        
    Returns:
        (output_path, ConversionReport)
        
    Example:
        >>> output, report = convert_to_gltf("model.obj")
        >>> print(report.summary())
    """
    report = ConversionReport(input_path=input_path)
    
    # Validate input
    if not os.path.exists(input_path):
        report.errors.append(f"Input file not found: {input_path}")
        return "", report
    
    input_path = os.path.abspath(input_path)
    
    # Detect format
    input_format = detect_format(input_path)
    if input_format is None:
        report.errors.append(f"Unsupported format. Supported: {list(SUPPORTED_FORMATS.keys())}")
        return "", report
    
    report.input_format = SUPPORTED_FORMATS[input_format]
    
    # Determine output path
    if output_path is None:
        ext = '.glb' if binary else '.gltf'
        output_path = str(Path(input_path).with_suffix(ext))
    
    report.output_path = os.path.abspath(output_path)
    
    try:
        # Convert based on format
        if input_format == '.obj':
            output, info = obj_to_gltf(input_path, output_path, binary=binary)
            report.conversion_stats = info.get("stats", {})
            report.warnings.extend(info.get("warnings", []))
        
        elif input_format == '.fbx':
            output, info = fbx_to_gltf(input_path, output_path, binary=binary, optimize=False)
            report.conversion_stats = info.get("stats", {})
            report.warnings.extend(info.get("warnings", []))
        
        elif input_format in ('.gltf', '.glb'):
            # Already GLTF, just copy or re-export if optimization needed
            if optimize or input_path != output_path:
                # Will be handled by optimization step
                import shutil
                if not optimize:
                    shutil.copy2(input_path, output_path)
            else:
                output_path = input_path
            report.conversion_stats = {"note": "Input already GLTF format"}
        
        # Optimization pass
        if optimize and input_format not in ('.gltf', '.glb'):
            # Already optimized during FBX conversion
            if input_format != '.fbx':
                pass  # OBJ converter handles basic optimization
        elif optimize and input_format in ('.gltf', '.glb'):
            # Optimize existing GLTF
            if optimization_settings is None:
                optimization_settings = OptimizationSettings()
            
            _, opt_result = optimize_gltf(input_path, output_path, optimization_settings)
            report.optimization_stats = opt_result.get("stats", {})
            report.warnings.extend(opt_result.get("warnings", []))
        
        # Validation
        if validate:
            report.validation = validate_gltf(output_path)
            
            # Add validation issues to report
            for issue in report.validation.issues:
                if issue.severity.value == "error":
                    report.warnings.append(f"[Validation] {issue.message}")
                elif issue.severity.value == "warning":
                    report.warnings.append(f"[Validation] {issue.message}")
        
        report.success = True
        
    except Exception as e:
        report.errors.append(str(e))
        import traceback
        report.errors.append(traceback.format_exc())
    
    return report.output_path if report.success else "", report


def batch_convert(
    input_files: List[str],
    output_dir: Optional[str] = None,
    binary: bool = True,
    optimize: bool = True,
    validate: bool = True,
) -> Dict[str, ConversionReport]:
    """
    Convert multiple files to GLTF.
    
    Args:
        input_files: List of input file paths
        output_dir: Output directory (default: same as input)
        binary: Output GLB (True) or GLTF (False)
        optimize: Apply optimization
        validate: Validate outputs
        
    Returns:
        Dict mapping input paths to ConversionReports
    """
    results = {}
    
    for input_path in input_files:
        # Determine output path
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            ext = '.glb' if binary else '.gltf'
            filename = Path(input_path).stem + ext
            output_path = os.path.join(output_dir, filename)
        else:
            output_path = None
        
        _, report = convert_to_gltf(
            input_path,
            output_path,
            binary=binary,
            optimize=optimize,
            validate=validate,
        )
        
        results[input_path] = report
    
    return results


def get_supported_formats() -> Dict[str, str]:
    """Get dict of supported input formats"""
    return SUPPORTED_FORMATS.copy()


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import argparse
    import json as json_module
    
    parser = argparse.ArgumentParser(
        description="Convert 3D models to GLTF/GLB format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m tools.gltf_pipeline.pipeline model.obj
  python -m tools.gltf_pipeline.pipeline character.fbx -o output.glb
  python -m tools.gltf_pipeline.pipeline *.obj --output-dir converted/
        """
    )
    
    parser.add_argument("input", nargs="+", help="Input file(s)")
    parser.add_argument("-o", "--output", help="Output file (single file) or directory (multiple files)")
    parser.add_argument("--gltf", action="store_true", help="Output GLTF instead of GLB")
    parser.add_argument("--no-optimize", action="store_true", help="Skip optimization")
    parser.add_argument("--no-validate", action="store_true", help="Skip validation")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--formats", action="store_true", help="List supported formats")
    
    args = parser.parse_args()
    
    if args.formats:
        print("Supported input formats:")
        for ext, desc in SUPPORTED_FORMATS.items():
            print(f"  {ext}: {desc}")
        exit(0)
    
    # Single or batch conversion
    if len(args.input) == 1:
        output, report = convert_to_gltf(
            args.input[0],
            args.output,
            binary=not args.gltf,
            optimize=not args.no_optimize,
            validate=not args.no_validate,
        )
        
        if args.json:
            print(json_module.dumps(report.to_dict(), indent=2))
        else:
            print(report.summary())
        
        exit(0 if report.success else 1)
    
    else:
        results = batch_convert(
            args.input,
            args.output,
            binary=not args.gltf,
            optimize=not args.no_optimize,
            validate=not args.no_validate,
        )
        
        success_count = sum(1 for r in results.values() if r.success)
        
        if args.json:
            print(json_module.dumps({k: v.to_dict() for k, v in results.items()}, indent=2))
        else:
            print(f"\nBatch Conversion Complete")
            print(f"========================")
            print(f"Success: {success_count}/{len(results)}")
            
            for input_path, report in results.items():
                status = "✅" if report.success else "❌"
                print(f"  {status} {input_path}")
                if args.verbose and not report.success:
                    for e in report.errors:
                        print(f"      Error: {e}")
        
        exit(0 if success_count == len(results) else 1)

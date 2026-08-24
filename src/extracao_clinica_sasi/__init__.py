#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SASI - Extração Clínica
Sistema de Extração e Compilação de Dados Clínicos para UTI - Dr. Nicolas

Main package initialization.
"""

from .core import (
    extract_from_text,
    validate_data,
    generate_output,
    generate_full_output,
    PatientData,
    VitalSigns,
    LabResults,
    FluidBalance,
    ClinicalDataExtractor,
    ClinicalDataValidator,
    ClinicalOutputGenerator,
)
from .ocr_text import OCRTextExtractor, ClinicalOCROptimizer, extract_text_from_file
from .server import app as flask_app

__version__ = '1.0.0'
__author__ = 'Dr. Nicolas Teixeira'
__description__ = 'Sistema de Extração e Compilação de Dados Clínicos para UTI'

__all__ = [
    'extract_from_text',
    'validate_data',
    'generate_output',
    'generate_full_output',
    'PatientData',
    'VitalSigns',
    'LabResults',
    'FluidBalance',
    'ClinicalDataExtractor',
    'ClinicalDataValidator',
    'ClinicalOutputGenerator',
    'OCRTextExtractor',
    'ClinicalOCROptimizer',
    'extract_text_from_file',
    'flask_app',
    '__version__',
    '__author__',
    '__description__',
]
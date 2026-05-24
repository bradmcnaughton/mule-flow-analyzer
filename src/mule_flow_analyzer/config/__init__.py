"""
Configuration module for Mule Flow Analyzer.

This module contains configuration-related components including default properties
and constants used throughout the package.
"""

from .default_properties import DEFAULT_PROPERTIES
from .constants import OutputFormat, normalize_output_format

__all__ = [
    'DEFAULT_PROPERTIES',
    'OutputFormat',
    'normalize_output_format',
]

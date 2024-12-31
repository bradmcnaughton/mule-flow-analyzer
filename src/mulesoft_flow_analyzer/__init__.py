"""
MuleSoft Flow Analyzer - A tool for analyzing MuleSoft integration projects.

This package provides functionality to analyze MuleSoft projects and generate
sequence diagrams or natural language descriptions of each flow.
"""

from .analyzer.mule_flow_analyzer import MuleFlowAnalyzer, PropertyHierarchy
from .analyzer.sequence_diagram_generator import SequenceDiagramGenerator
from .analyzer.mule_flow_element import MuleFlowElement
from .config.default_properties import DEFAULT_PROPERTIES
from .config.constants import OutputFormat

__version__ = '1.1.0'

__all__ = [
    'MuleFlowAnalyzer',
    'PropertyHierarchy',
    'SequenceDiagramGenerator',
    'MuleFlowElement',
    'DEFAULT_PROPERTIES',
    'OutputFormat',
]

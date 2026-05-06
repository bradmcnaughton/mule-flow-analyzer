"""
Mule Flow Analyzer — a tool for analyzing Mule integration projects.

This package provides functionality to analyze Mule projects and generate
sequence diagrams or natural language descriptions of each flow.
"""

from .analyzer.mule_flow_analyzer import MuleFlowAnalyzer, PropertyHierarchy
from .analyzer.sequence_diagram_generator import SequenceDiagramGenerator
from .analyzer.mermaid_sequence_diagram_generator import MermaidSequenceDiagramGenerator
from .analyzer.mule_flow_element import MuleFlowElement
from .config.default_properties import DEFAULT_PROPERTIES
from .config.constants import OutputFormat
from .exceptions import (
    ConfigurationError,
    DiagramGenerationError,
    DiagramGenerationException,
    MuleFlowException,
    MuleFlowParsingException,
    MuleFlowValidationException,
    PropertyHierarchyError,
    RenderingError,
)

__version__ = '1.0.0'

__all__ = [
    'MuleFlowAnalyzer',
    'PropertyHierarchy',
    'SequenceDiagramGenerator',
    'MermaidSequenceDiagramGenerator',
    'MuleFlowElement',
    'DEFAULT_PROPERTIES',
    'OutputFormat',
    'MuleFlowException',
    'MuleFlowParsingException',
    'MuleFlowValidationException',
    'ConfigurationError',
    'RenderingError',
    'DiagramGenerationException',
    'DiagramGenerationError',
    'PropertyHierarchyError',
]

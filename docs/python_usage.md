# MuleSoft Flow Analyzer - Python Integration Guide

## Overview

The MuleSoft Flow Analyzer is a Python library designed to analyze MuleSoft integration projects and generate sequence diagrams or natural language descriptions of each flow. This guide provides detailed information for Python developers looking to integrate this library into their applications.

## Installation

```bash
pip install https://{GIT_ACCESS_TOKEN}@raw.githubusercontent.com/bradmcnaughton/private-python-packages/main/mulesoft-flow-analyzer/1.1.0/mulesoft_flow_analyzer-1.1.0-py3-none-any.whl
```

## Core Components

The library provides several key components:

1. `MuleFlowAnalyzer`: The main class for analyzing MuleSoft projects
2. `SequenceDiagramGenerator`: Generates sequence diagrams from flow analysis
3. `MuleFlowElement`: Represents individual elements in a MuleSoft flow
4. `PropertyHierarchy`: Manages property file hierarchy for placeholder resolution

## Basic Usage

### Initialization

```python
from mulesoft_flow_analyzer import MuleFlowAnalyzer, PropertyHierarchy, OutputFormat

# Basic initialization
analyzer = MuleFlowAnalyzer()

# Initialize with project path
analyzer = MuleFlowAnalyzer(project_path="/path/to/mule/project")

# Initialize with property files
property_files = PropertyHierarchy({
    0: "properties/prod.yaml",  # Highest priority
    1: "properties/dev.yaml",   # Lower priority
    2: "properties/common.yaml" # Lowest priority
})
analyzer = MuleFlowAnalyzer(
    project_path="/path/to/mule/project",
    property_files=property_files
)

# Initialize with custom configuration
user_config = {
    'analyzer_properties': {
        'output_type': OutputFormat.TEXT,
        'plantuml': {
            'server': 'http://localhost:8087/',
            'format': 'png'
        }
    }
}
analyzer = MuleFlowAnalyzer(user_config=user_config)
```

### Project Analysis

```python
# Analyze all flows in the project
analyzer.analyze_mule_flows()

# Analyze a specific flow
analyzer.analyze_mule_flows(flow_name="my-flow-name")
```

## Configuration Options

The library supports extensive configuration through the `DEFAULT_PROPERTIES` structure. Key configuration areas include:

### Output Format

- `TEXT`: Generates text-based flow descriptions
- `SEQUENCE`: Generates sequence diagrams
- `NATURAL`: Generates natural language descriptions

### Diagram Formatting

- Mule box colors and styling
- Arrow styles and colors
- Actor icons and formatting
- Transaction formatting
- Error handling visualization
- Async processing visualization
- Batch processing visualization

### Property File Processing

- Property file hierarchy management
- Placeholder resolution
- Environment-specific property handling

## Advanced Usage

### Custom Configuration

```python
from mulesoft_flow_analyzer import DEFAULT_PROPERTIES

# Create custom configuration
custom_config = {
    'analyzer_properties': {
        'output_type': OutputFormat.SEQUENCE,
        'plantuml': {
            'server': 'http://localhost:8087/',
            'format': 'png',
            'output_directory': './output/diagrams'
        }
    },
    'diagram_formatting_properties': {
        'mule': {
            'box-color': 'LightBlue-6FBBD3'
        },
        'verbose': {
            'processors': True,
            'logging': False,
            'errors': True,
            'notes': True
        }
    }
}

# Apply configuration
analyzer.set_configuration_properties(custom_config)
```

### Property File Management

```python
# Set property file hierarchy
property_files = PropertyHierarchy({
    0: "properties/prod.yaml",
    1: "properties/dev.yaml"
})
analyzer.set_properties_hierarchy(property_files)

# Get current property hierarchy
current_hierarchy = analyzer.get_properties_hierarchy()
```

### Flow Analysis Results

```python
# Get configuration properties
config = analyzer.get_configuration_properties()

# Analyze specific flow
analyzer.analyze_mule_flows(flow_name="my-flow")

# The results will be:
# - For TEXT output: Printed to console
# - For SEQUENCE output: Saved as PNG files in the configured output directory
```

## Error Handling

The library includes custom exceptions for error handling:

```python
from mulesoft_flow_analyzer.exceptions import MuleFlowException

try:
    analyzer.analyze_mule_flows()
except MuleFlowException as e:
    print(f"Error analyzing flows: {str(e)}")
```

## Best Practices

1. **Property File Management**

   - Use a clear hierarchy for property files
   - Keep environment-specific properties separate
   - Document property file priorities

2. **Configuration**

   - Start with default configuration
   - Override only necessary settings
   - Use environment variables for sensitive settings

3. **Output Management**

   - Configure appropriate output directories
   - Handle file permissions appropriately
   - Consider cleanup of generated files

4. **Error Handling**
   - Implement proper exception handling
   - Log errors appropriately
   - Validate configurations before use

## Dependencies

- Python 3.x
- PlantUML server (for sequence diagram generation)
- Required Python packages:
  - xmltodict
  - yaml
  - plantweb

## Troubleshooting

1. **Property Resolution Issues**

   - Verify property file hierarchy
   - Check file permissions
   - Validate property file formats

2. **Diagram Generation Problems**

   - Verify PlantUML server connectivity
   - Check output directory permissions
   - Validate configuration settings

3. **Flow Analysis Errors**
   - Verify MuleSoft project structure
   - Check XML file validity
   - Validate flow references

## Example Implementation

```python
from mulesoft_flow_analyzer import MuleFlowAnalyzer, PropertyHierarchy, OutputFormat
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

def analyze_mule_project(project_path: str, flow_name: str = None):
    try:
        # Initialize analyzer
        analyzer = MuleFlowAnalyzer(
            project_path=project_path,
            property_files=PropertyHierarchy({
                0: "properties/prod.yaml",
                1: "properties/common.yaml"
            })
        )

        # Set custom configuration
        analyzer.set_configuration_properties({
            'analyzer_properties': {
                'output_type': OutputFormat.SEQUENCE,
                'plantuml': {
                    'server': 'http://localhost:8087/',
                    'format': 'png',
                    'output_directory': './output/diagrams'
                }
            }
        })

        # Analyze flows
        analyzer.analyze_mule_flows(flow_name)

    except Exception as e:
        logging.error(f"Error analyzing MuleSoft project: {str(e)}")
        raise

if __name__ == "__main__":
    analyze_mule_project("/path/to/mule/project", "my-flow")
```

## Additional Resources

- [Configuration Documentation](docs/configuration.md)
- [CLI Implementation](https://github.com/bradmcnaughton/mulesoft-flow-analyzer-cli)
- [PlantUML Documentation](https://plantuml.com/)

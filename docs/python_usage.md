# Mule Flow Analyzer — Python integration guide

## Overview

**Mule Flow Analyzer** is a Python library designed to analyze Mule integration projects and generate sequence diagrams or natural language descriptions of each flow. This guide provides detailed information for Python developers looking to integrate this library into their applications.

## Installation

```bash
pip install mule-flow-analyzer
```

Pin a version if needed:

```bash
pip install mule-flow-analyzer==1.0.0
```

Package page: https://pypi.org/project/mule-flow-analyzer/

### Log file path (for your app or CLI)

The default configuration metadata includes `analyzer_properties.logging.file` (`mfa-logs/mule_flow_analyzer.log` relative to the process current working directory). The library does not configure Python’s `logging` module for you; this value is for **your** code or a CLI to read and attach a `FileHandler` if desired. Override it by merging `user_config` or external YAML into the analyzer configuration (see [configuration.md](configuration.md)).

## Core Components

The library provides several key components:

1. `MuleFlowAnalyzer`: The main class for analyzing Mule projects
2. `SequenceDiagramGenerator`: Generates PlantUML sequence diagrams from flow analysis
3. `MermaidSequenceDiagramGenerator`: Generates Mermaid sequence diagram syntax from flow analysis
4. `NaturalLanguageDescriptionGenerator`: Generates structured English flow descriptions from flow analysis
5. `MuleFlowElement`: Represents individual elements in a Mule flow
6. `PropertyHierarchy`: Manages property file hierarchy for placeholder resolution

## Basic Usage

### Initialization

```python
from mule_flow_analyzer import MuleFlowAnalyzer, PropertyHierarchy, OutputFormat

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
        'diagram_engine': 'plantuml',
        'plantuml': {
            'mode': 'server',
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

| Format | Output | Description |
|--------|--------|-------------|
| `TEXT` | Printed to **console** | Indented structural tree (`tag [name]`) for debugging |
| `SEQUENCE` | **Files** in `plantuml` or `mermaid` output directory | Sequence diagrams (PlantUML or Mermaid) |
| `NATURAL` | **Files** in `natural.output_directory` | Deterministic structured English flow descriptions (template-based prose, not LLM-generated) |

`SEQUENCE` supports `analyzer_properties.diagram_engine`:

- `plantuml` (default): writes PlantUML source and renders through server, jar, or CLI depending on `analyzer_properties.plantuml.mode`.
- `mermaid` (experimental): writes Mermaid `.mmd` source and optionally renders through Mermaid CLI depending on `analyzer_properties.mermaid.mode`.

PlantUML is the recommended sequence diagram output. Mermaid support is experimental and may not represent every Mule flow construct or formatting feature as accurately as PlantUML.

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
from mule_flow_analyzer import DEFAULT_PROPERTIES

# Create custom configuration
custom_config = {
    'analyzer_properties': {
        'output_type': OutputFormat.SEQUENCE,
        'diagram_engine': 'plantuml',
        'plantuml': {
            'mode': 'server',
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

### Mermaid Output

Mermaid support is experimental. Prefer PlantUML for the most complete sequence diagram output.

```python
from mule_flow_analyzer import MuleFlowAnalyzer, OutputFormat

analyzer = MuleFlowAnalyzer(
    project_path="/path/to/mule/project",
    user_config={
        'analyzer_properties': {
            'output_type': OutputFormat.SEQUENCE,
            'diagram_engine': 'mermaid',
            'mermaid': {
                'mode': 'file',
                'output_directory': './output/mermaid',
            },
        }
    }
)
analyzer.analyze_mule_flows(flow_name="my-flow")
```

Use `mode: 'cli'` with `cli_command: 'mmdc'` and `format: 'svg'` or `png` if you want the library to render with Mermaid CLI. Source `.mmd` files are always written.

### NATURAL Output

`NATURAL` writes one structured English description file per flow. Output is **deterministic and template-based** — the library does not call an LLM. For polished documentation, pipe the generated file to your own LLM or editor workflow.

```python
from mule_flow_analyzer import MuleFlowAnalyzer, OutputFormat

analyzer = MuleFlowAnalyzer(
    project_path="/path/to/mule/project",
    user_config={
        'analyzer_properties': {
            'output_type': OutputFormat.NATURAL,
            'natural': {
                'output_directory': './output/natural',
                'file_extension': 'txt',
            },
        }
    }
)
analyzer.analyze_mule_flows(flow_name="my-flow")
```

Respects the same `diagram_formatting_properties.verbose` flags as sequence diagrams (`processors`, `logging`, `errors`, `notes`).

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
# - For TEXT output: Printed to console (structural tree)
# - For NATURAL output: Saved as .txt (or configured extension) in natural.output_directory
# - For SEQUENCE + PlantUML: Saved as PlantUML source and rendered files in the configured output directory
# - For SEQUENCE + Mermaid: Saved as .mmd source, optionally rendered by Mermaid CLI
```

## Error Handling

Exceptions live in `mule_flow_analyzer.exceptions`. `MuleFlowException` is the base for several types; diagram configuration and rendering use `ConfigurationError` and `RenderingError` (subclasses of `DiagramGenerationException`, which subclasses `MuleFlowException`).

```python
from mule_flow_analyzer.exceptions import (
    MuleFlowException,
    ConfigurationError,
    RenderingError,
)

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
- PlantUML rendering backend (for PlantUML sequence diagram rendering):
  - `mode=server`: reachable PlantUML HTTP server (local Docker-hosted or hosted)
  - `mode=jar`: local Java + `plantuml.jar`
  - `mode=cli`: local `plantuml` executable
- Mermaid CLI is optional for Mermaid rendering:
  - `mode=file`: no Mermaid dependency; use the generated `.mmd` files directly
  - `mode=cli`: install `@mermaid-js/mermaid-cli` and make `mmdc` available on PATH
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

   - For `mode=server`, verify PlantUML server connectivity
   - For `mode=jar`, verify Java and `jar_path`
   - For `mode=cli`, verify `plantuml` command is on PATH
   - For Mermaid `mode=cli`, verify `mmdc` is on PATH
   - Check output directory permissions
   - Validate configuration settings

3. **Flow Analysis Errors**
   - Verify Mule project structure
   - Check XML file validity
   - Validate flow references

## Example Implementation

```python
from mule_flow_analyzer import MuleFlowAnalyzer, PropertyHierarchy, OutputFormat
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
                'diagram_engine': 'plantuml',
                'plantuml': {
                    'mode': 'server',
                    'server': 'http://localhost:8087/',
                    'format': 'png',
                    'output_directory': './output/diagrams'
                }
            }
        })

        # Analyze flows
        analyzer.analyze_mule_flows(flow_name)

    except Exception as e:
        logging.error(f"Error analyzing Mule project: {str(e)}")
        raise

if __name__ == "__main__":
    analyze_mule_project("/path/to/mule/project", "my-flow")
```

## Additional Resources

- [Configuration Documentation](docs/configuration.md)
- [CLI Implementation](https://github.com/bradmcnaughton/mule-flow-analyzer-cli)
- [PlantUML Documentation](https://plantuml.com/)

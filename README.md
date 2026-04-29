# Mule Flow Analyzer

A library for analyzing Mule integration projects to generate sequence diagrams or natural language descriptions of each flow.

Before analysis, placeholders in code will attempt to be replaced using values from the property files in the project directory. If there are multiple properties files, you can supply a hierarchy to follow and any omitted properties will not be referenced. This can be helpful if multiple environment property files are in the project.

Depending on your output format, text files and/or diagrams will be generated with file names based on the flow name (with special characters replaced with underscores).

## Installation

Install from [PyPI](https://pypi.org/project/mule-flow-analyzer/):

```bash
pip install mule-flow-analyzer
```

To install a specific version:

```bash
pip install mule-flow-analyzer==1.0.0
```

For development, clone the repository and install in editable mode with test dependencies:

```bash
pip install -e ".[dev]"
```

Maintainers: see [Releasing to PyPI](docs/RELEASING.md).

## IDE agent skill (VS Code / GitHub Copilot)

This repo ships an [Agent Skill](https://code.visualstudio.com/docs/copilot/customization/agent-skills) for analyzing flows from inside a Mule workspace using Copilot or compatible agents.

**Where it lives here:** [`.cursor/skills/mule-flow-analyzer/`](.cursor/skills/mule-flow-analyzer/) (`SKILL.md` plus [`scripts/run_analyzer.py`](.cursor/skills/mule-flow-analyzer/scripts/run_analyzer.py)).

**Where to use it:** Copy the whole `mule-flow-analyzer` folder into **your Mule application repository** (the project that contains `src/main/mule/`). Do not rely on this library clone for analyzing your apps unless you open that app as the workspace. Suggested paths after copying:

- `.github/skills/mule-flow-analyzer/` (works well with GitHub Copilot in VS Code), or
- `.cursor/skills/mule-flow-analyzer/`, or
- any folder allowed by your `chat.skillsLocations` setting.

The `name` field in `SKILL.md` must match the parent directory name (`mule-flow-analyzer`). After copying, install the package in a venv (`pip install mule-flow-analyzer`) and run the helper from the Mule app root; see the script’s `--help` for flags.

## Diagram Generation

Sequence diagram generation supports two syntax engines:

- `plantuml` (default): writes PlantUML source and can render PNG/SVG through a server, local JAR, or CLI.
- `mermaid`: writes Mermaid `.mmd` source and can optionally render through Mermaid CLI.

Select the engine with `analyzer_properties.diagram_engine`. Existing configurations continue to use PlantUML by default.

### PlantUML

PlantUML image generation supports three rendering approaches:

- `server`: HTTP PlantUML server URL (local Docker-hosted or hosted service)
- `jar`: local `java -jar plantuml.jar` execution (offline, no Docker)
- `cli`: local `plantuml` command execution (offline)

If no mode is explicitly set, the library defaults to `server` mode for backward compatibility.

### Running the PlantUML server locally with Docker

No Mule application source is required to be sent to a public server, only the generated UML. If you don't want to send the UML to a public server, you can run the PlantUML server locally.

Pull the PlantUML server image:

```bash
docker pull plantuml/plantuml-server
```

Run the PlantUML server. (In this example, the server will be available on port 8087)

```bash
docker run -d -p 8087:8080 plantuml/plantuml-server:jetty
```

Use `server` mode with `http://localhost:8087/`:

```yaml
analyzer_properties:
  plantuml:
    mode: "server"
    server: "http://localhost:8087/"
    format: "png"
    output_directory: "./output/plantuml"
```

### Running with local PlantUML JAR (no Docker, offline)

Requirements:

- Java installed and on `PATH`
- `plantuml.jar` downloaded locally (for example `./tools/plantuml.jar`)

Use `jar` mode:

```yaml
analyzer_properties:
  plantuml:
    mode: "jar"
    java_command: "java"
    jar_path: "./tools/plantuml.jar"
    format: "png"
    output_directory: "./output/plantuml"
```

### Running with local PlantUML CLI (offline)

If `plantuml` is installed as a command:

```yaml
analyzer_properties:
  plantuml:
    mode: "cli"
    cli_command: "plantuml"
    format: "png"
    output_directory: "./output/plantuml"
```

### Quick validation commands

Check local server:

```bash
curl -I http://localhost:8087/
```

Check Java:

```bash
java -version
```

Check PlantUML CLI:

```bash
plantuml -version
```

Refer to [Overriding Configuration](#overriding-configuration) for full configuration details.

### Mermaid

Mermaid output is useful when you want syntax that can be rendered by GitHub, GitLab, documentation tools, editor extensions, or Mermaid CLI.

By default, Mermaid mode writes source only:

```yaml
analyzer_properties:
  diagram_engine: "mermaid"
  mermaid:
    mode: "file"
    output_directory: "./output/mermaid"
    source_extension: "mmd"
```

To render with Mermaid CLI, install `@mermaid-js/mermaid-cli` and use `cli` mode:

```bash
npm install -g @mermaid-js/mermaid-cli
mmdc --version
```

```yaml
analyzer_properties:
  diagram_engine: "mermaid"
  mermaid:
    mode: "cli"
    cli_command: "mmdc"
    format: "svg"
    output_directory: "./output/mermaid"
```

Mermaid support intentionally degrades PlantUML-only features. Custom PlantUML actor icons, `skinparam`, scale settings, colored arrows, colored notes/groups, and the generated PlantUML legend do not have direct Mermaid equivalents.

## Overriding Configuration

For detailed configuration options, see [Configuration Documentation](docs/configuration.md).

## Instructions for LLMs

LLMs can be shown the [python usage instructions](docs/python_usage.md) to help them generate code.

## Troubleshooting

If you encounter an error, check the log file for more information. The default path in configuration metadata is `mfa-logs/mule_flow_analyzer.log` (relative to the process working directory where Python is run). Override it under `analyzer_properties.logging.file` in your merged configuration or YAML.

If the log file is not found, check the default properties file for the correct path.

The log level can be set to DEBUG to get more information in the configuration file.

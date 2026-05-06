---
name: mule-flow-analyzer
description: >-
  Uses the PyPI package mule-flow-analyzer to analyze Mule integration flows in the
  open workspace, generate PlantUML or Mermaid sequence diagrams or text descriptions, and tune
  analyzer configuration. Use when the user asks to document flows, generate sequence
  diagrams or UML, explain what a flow does, analyze src/main/mule XML, or run flow
  analysis with PlantUML, Mermaid, or placeholder properties.
argument-hint: "[flow name] [--output-type TEXT|SEQUENCE|NATURAL] [--diagram-engine plantuml|mermaid] [--plantuml-server URL]"
---

# Mule Flow Analyzer

Analyze the **current workspace** as a Mule application root: it must contain `src/main/mule/`. Use [mule-flow-analyzer](https://pypi.org/project/mule-flow-analyzer/) (`import mule_flow_analyzer`).

## Environment

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install mule-flow-analyzer
```

## Tools the agent should use

| Goal                                    | Tool / action                                                                                                                                      |
| --------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| Run analysis without writing new Python | **Terminal:** run [scripts/run_analyzer.py](./scripts/run_analyzer.py) from the **Mule app workspace root** with `-p`, `-f`, `-o`, `-s`, `--diagram-engine` as needed. |
| Install or fix imports                  | **Terminal:** `pip install mule-flow-analyzer` (or `pip show mule-flow-analyzer`).                                                                 |
| Inspect flows / XML                     | **Read/search** files under `src/main/mule/` and `src/main/resources/`.                                                                            |
| Build or adjust config in code          | **Edit** a small script or notebook that imports `MuleFlowAnalyzer` and passes `user_config` (see below).                                          |

Use the **workspace root of the Mule app** as `project_path` unless the user specifies another folder. Confirm `src/main/mule` exists under that path.

## Interpret user intent and set configuration

### 1. Clarify the task (internally or with a short question)

- **Whole app vs one flow:** Does the user want every flow or a named flow?
- **Output:** Diagrams (PlantUML PNG/SVG or Mermaid `.mmd`/SVG/PNG), printed structure (TEXT), or natural language (NATURAL)?
- **Diagram engine:** If SEQUENCE diagrams are requested, choose `plantuml` (default and recommended). Use `mermaid` only when the user explicitly asks for Mermaid output; Mermaid support is experimental.
- **PlantUML:** If PlantUML images are requested, choose rendering mode: `server` (HTTP PlantUML server, default), `jar` (local `java -jar plantuml.jar`), or `cli` (local `plantuml` command). If `server`, default is `http://localhost:8087/`.
- **Mermaid:** If Mermaid is requested, default to `mode: "file"` and write `.mmd` source. Use `mode: "cli"` only when rendered images are requested and `mmdc` is available.
- **Properties:** Should placeholders be resolved from `src/main/resources`? If yes, ask which property files or env (or use auto-discovery by omitting `property_files`).

### 1a. Required prompting behavior for image generation

When the user request is ambiguous, ask follow-up questions before running:

1. Determine whether the user wants diagram **images**:
   - If not explicitly yes/no, ask: "Do you want rendered diagram images (PNG/SVG), or text/natural output only?"
2. If user wants images, determine renderer approach:
   - If user has already provided server URL or asked for jar/cli, proceed to validation.
   - If not clear, ask: "Should I use a PlantUML server URL or local jar/cli rendering?"
3. If user wants images, ensure output directory is explicit:
   - If not provided, ask for `output_directory` path.
   - Mermaid `file` mode creates source files, not images; do not treat it as image rendering.

Do not assume image rendering mode when the user has not clearly requested images.

### 1b. Validation behavior before rendering images

If user requested images and selected a renderer, validate availability first:

- `server` mode:
  - Support both server approaches:
    - Hosted URL (example: `https://www.plantuml.com/plantuml/`)
    - Locally hosted Docker/Podman URL (example: `http://localhost:8087/`)
  - Validate URL reachable (for local default test `http://localhost:8087/`).
  - Example checks: `curl -I <server-url>` or equivalent HTTP check.
- `jar` mode:
  - Validate Java exists: `java -version` (or configured `java_command`).
  - Validate jar exists at configured `jar_path`.
- `cli` mode:
  - Validate CLI exists: `<cli_command> -version`.
- Mermaid `cli` mode:
  - Validate CLI exists: `mmdc --version` or configured `<cli_command> --version`.

If validation fails, explain exactly what is missing and offer automatic setup steps.

### 1c. Automatic setup guidance/workflow (when user asks or when validation fails)

The agent should offer to run these setup commands for the user.

Docker server setup:

```bash
docker pull plantuml/plantuml-server
docker run -d -p 8087:8080 --name plantuml-server plantuml/plantuml-server:jetty
```

Podman server setup:

```bash
podman pull docker.io/plantuml/plantuml-server
podman run -d -p 8087:8080 --name plantuml-server docker.io/plantuml/plantuml-server:jetty
```

Jar setup (example):

```bash
mkdir -p tools
# user provides/approves source URL for plantuml.jar download location
# then save jar as ./tools/plantuml.jar
java -version
```

After setup, re-run validation and continue rendering.

### 1d. Post-run image verification (required when output is images)

After generating PNG/SVG diagrams, always verify output files were created successfully.

1. **Use terminal filesystem checks first (required)**:
   - `ls` on the output directory
   - direct path checks via shell (`test -f ...` / platform equivalent)
2. Treat search/indexing tools (like Glob) as secondary only:
   - If Glob/search shows no results, do **not** assume generation failed.
   - Binary files may not be indexed immediately in some IDEs.
3. Confirm existence using direct path access:
   - `ReadFile` on expected file paths to confirm file presence/metadata even for binary outputs
4. Only after terminal/path verification fails should the agent regenerate or begin troubleshooting renderer issues.
5. Report the confirmed output directory and at least one verified image filename back to the user.

### 2. Map intent to `user_config`

Merge overrides into `user_config` (the library merges with its defaults). Common keys:

| User says                           | Set in `user_config`                                                                            |
| ----------------------------------- | ----------------------------------------------------------------------------------------------- |
| Text / list flows / print structure | `analyzer_properties.output_type` → `OutputFormat.TEXT`                                         |
| Sequence diagram / UML / PlantUML via server | `OutputFormat.SEQUENCE`, `diagram_engine: "plantuml"`, `plantuml.mode: "server"`, `plantuml.server`, `format`, `output_directory` |
| Sequence diagram / UML / PlantUML via jar | `OutputFormat.SEQUENCE`, `diagram_engine: "plantuml"`, `plantuml.mode: "jar"`, `plantuml.java_command`, `plantuml.jar_path`, `format`, `output_directory` |
| Sequence diagram / UML / PlantUML via cli | `OutputFormat.SEQUENCE`, `diagram_engine: "plantuml"`, `plantuml.mode: "cli"`, `plantuml.cli_command`, `format`, `output_directory` |
| Mermaid source diagram (experimental) | `OutputFormat.SEQUENCE`, `diagram_engine: "mermaid"`, `mermaid.mode: "file"`, `mermaid.output_directory` |
| Mermaid rendered diagram (experimental) | `OutputFormat.SEQUENCE`, `diagram_engine: "mermaid"`, `mermaid.mode: "cli"`, `mermaid.cli_command`, `format`, `output_directory` |
| Natural language description        | `OutputFormat.NATURAL`                                                                          |
| Use local PlantUML on 8087          | `plantuml.server`: `http://localhost:8087/`                                                     |
| Put diagrams in a folder            | `plantuml.output_directory` or `mermaid.output_directory` (relative to cwd or absolute)          |
| Log file location                   | `analyzer_properties.logging.file` (metadata for your logging setup)                            |

Example:

```python
from mule_flow_analyzer import MuleFlowAnalyzer, PropertyHierarchy, OutputFormat

user_config = {
    "analyzer_properties": {
        "output_type": OutputFormat.SEQUENCE,
        "diagram_engine": "plantuml",
        "plantuml": {
            "mode": "server",
            "server": "http://localhost:8087/",
            "format": "png",
            "output_directory": "./docs/generated/uml",
        },
    },
}

analyzer = MuleFlowAnalyzer(
    project_path="<absolute path to Mule app root>",
    property_files=PropertyHierarchy({0: "properties/dev.yaml"}) if using_explicit_hierarchy else None,
    user_config=user_config,
)
analyzer.analyze_mule_flows(flow_name="optionalFlowNameOrNone")
```

Jar example:

```python
user_config = {
    "analyzer_properties": {
        "output_type": OutputFormat.SEQUENCE,
        "diagram_engine": "plantuml",
        "plantuml": {
            "mode": "jar",
            "java_command": "java",
            "jar_path": "./tools/plantuml.jar",
            "format": "png",
            "output_directory": "./docs/generated/uml",
        },
    },
}
```

Mermaid example (experimental; PlantUML is recommended):

```python
user_config = {
    "analyzer_properties": {
        "output_type": OutputFormat.SEQUENCE,
        "diagram_engine": "mermaid",
        "mermaid": {
            "mode": "file",
            "output_directory": "./docs/generated/mermaid",
        },
    },
}
```

Use `PropertyHierarchy` only when the user specifies an order of property files; otherwise let the analyzer discover files under `src/main/resources`.

### 3. Run

- Prefer [scripts/run_analyzer.py](./scripts/run_analyzer.py) for a quick run from the app root.
- On failure, read stderr, check `project_path`, renderer validation (server/jar/cli), and that `mule-flow-analyzer` is installed in the active interpreter.

```bash
python scripts/run_analyzer.py --help
python scripts/run_analyzer.py -p . --flow my-flow-name -o SEQUENCE -s http://localhost:8087/
python scripts/run_analyzer.py -p . --flow my-flow-name -o SEQUENCE --diagram-engine mermaid --output-dir ./docs/generated/mermaid
```

(Use the path to `scripts/run_analyzer.py` relative to where this skill folder sits in the workspace.)

## Limits and notes

- **SEQUENCE** output defaults to PlantUML and requires a configured PlantUML renderer (`server`, `jar`, or `cli`) for images.
- Mermaid support is experimental. Prefer PlantUML for the most complete Mule sequence diagram output.
- Mermaid `file` mode writes `.mmd` source without extra dependencies; Mermaid `cli` mode requires `mmdc`.
- Mermaid does not support PlantUML actor icons, `skinparam`, colored arrows/groups/notes, or the generated PlantUML legend.
- In `server` mode, only generated UML/diagrams leave the machine if you point `server` at a remote URL.
- The library does not configure Python `logging` automatically; `logging.file` in config is metadata for your app or CLI.
- Flow analysis is file-based; it does not drive Anypoint Studio.

## Reference

- Package: https://pypi.org/project/mule-flow-analyzer/
- Full API and configuration patterns: see the library repository’s `docs/` on GitHub (e.g. `python_usage.md`, `configuration.md`).

#!/usr/bin/env python3
"""
Example helper for the mule-flow-analyzer skill.

Run from your Mule application root (the folder that contains src/main/mule),
ideally with a venv where `mule-flow-analyzer` is installed:

  pip install mule-flow-analyzer
  python scripts/run_analyzer.py
  python scripts/run_analyzer.py --flow myFlowName --output-type SEQUENCE
  python scripts/run_analyzer.py --flow myFlowName --diagram-engine mermaid
"""

from __future__ import annotations

import argparse
import os
import sys

try:
    from mule_flow_analyzer import MuleFlowAnalyzer, OutputFormat
except ImportError:
    print(
        "Error: mule_flow_analyzer is not installed.\n"
        "  pip install mule-flow-analyzer",
        file=sys.stderr,
    )
    sys.exit(1)


def parse_output_type(value: str) -> OutputFormat:
    key = value.strip().upper()
    if key == "TEXT":
        return OutputFormat.TEXT
    if key == "SEQUENCE":
        return OutputFormat.SEQUENCE
    if key == "NATURAL":
        return OutputFormat.NATURAL
    raise argparse.ArgumentTypeError(f"Unknown output type: {value!r} (use TEXT, SEQUENCE, or NATURAL)")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyze Mule flows using mule-flow-analyzer (example script for Agent Skills)."
    )
    parser.add_argument(
        "-p",
        "--project",
        default=".",
        help="Path to Mule app root (directory containing src/main/mule). Default: current directory.",
    )
    parser.add_argument(
        "-f",
        "--flow",
        default=None,
        help="Analyze only this flow name (optional).",
    )
    parser.add_argument(
        "-o",
        "--output-type",
        type=parse_output_type,
        default=OutputFormat.SEQUENCE,
        help="TEXT, SEQUENCE (default), or NATURAL.",
    )
    parser.add_argument(
        "-s",
        "--plantuml-server",
        default="http://localhost:8087/",
        help="PlantUML server base URL (SEQUENCE output). Default: http://localhost:8087/",
    )
    parser.add_argument(
        "--diagram-engine",
        choices=["plantuml", "mermaid"],
        default="plantuml",
        help="Sequence diagram syntax engine. Default: plantuml.",
    )
    parser.add_argument(
        "--mermaid-mode",
        choices=["file", "cli"],
        default="file",
        help="Mermaid output mode: write .mmd only or render with mmdc. Default: file.",
    )
    parser.add_argument(
        "--mermaid-cli",
        default="mmdc",
        help="Mermaid CLI command for --mermaid-mode cli. Default: mmdc.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Override diagram output directory (default depends on diagram engine).",
    )
    args = parser.parse_args()

    project = os.path.abspath(args.project)
    user_config = {
        "analyzer_properties": {
            "output_type": args.output_type,
            "diagram_engine": args.diagram_engine,
            "plantuml": {
                "server": args.plantuml_server,
                "format": "png",
            },
            "mermaid": {
                "mode": args.mermaid_mode,
                "cli_command": args.mermaid_cli,
            },
            "natural": {},
        }
    }
    if args.output_dir:
        output_type = args.output_type
        if output_type == OutputFormat.NATURAL:
            user_config["analyzer_properties"]["natural"]["output_directory"] = args.output_dir
        else:
            user_config["analyzer_properties"][args.diagram_engine]["output_directory"] = args.output_dir

    analyzer = MuleFlowAnalyzer(project_path=project, property_files=None, user_config=user_config)
    analyzer.analyze_mule_flows(flow_name=args.flow)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

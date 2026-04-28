#!/usr/bin/env python3
"""
Example helper for the mule-flow-analyzer skill.

Run from your Mule application root (the folder that contains src/main/mule),
ideally with a venv where `mule-flow-analyzer` is installed:

  pip install mule-flow-analyzer
  python scripts/run_analyzer.py
  python scripts/run_analyzer.py --flow myFlowName --output-type SEQUENCE
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
        "--output-dir",
        default=None,
        help="Override diagram output directory (default: ./output/plantuml under project).",
    )
    args = parser.parse_args()

    project = os.path.abspath(args.project)
    user_config = {
        "analyzer_properties": {
            "output_type": args.output_type,
            "plantuml": {
                "server": args.plantuml_server,
                "format": "png",
            },
        }
    }
    if args.output_dir:
        user_config["analyzer_properties"]["plantuml"]["output_directory"] = args.output_dir

    analyzer = MuleFlowAnalyzer(project_path=project, property_files=None, user_config=user_config)
    analyzer.analyze_mule_flows(flow_name=args.flow)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

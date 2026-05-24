import os
from enum import Enum

# Application constants
DEFAULT_PROJECT_PATH = os.getcwd()
PROPERTY_FILE_SELECTION_PROMPT = "Enter the numbers of the property files to use (comma-separated, e.g., 1,5,3): "
PROPERTY_HIERARCHY_CONFIRMATION = "Please Confirm Property File Hierarchy. (For Example, Prod First then Dev then Global):" 

# Enum for the Output Format
OutputFormat = Enum('OutputFormat', ['TEXT', 'SEQUENCE', 'NATURAL'])


def normalize_output_format(value):
    """Coerce string or enum values to OutputFormat."""
    if isinstance(value, OutputFormat):
        return value
    if isinstance(value, str):
        key = value.strip().upper()
        for member in OutputFormat:
            if member.name == key:
                return member
    return value
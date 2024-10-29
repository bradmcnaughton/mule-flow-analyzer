from enum import Enum
import os
import xmltodict
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, NewType
import yaml
import re
from typing import List, Optional, Dict
from xml.sax.saxutils import escape, unescape

# Type for the Property Files Hierarchy
PropertyHierarchy = NewType('PropertyHierarchy', Dict[int, str])

# Enum for the Output Format
OutputFormat = Enum('OutputFormat', ['TEXT', 'SEQUENCE'])

# List of Tags that will always be processors regardless of the tag's prefix
ALWAYS_PROCESSOR_TAGS = ['scheduling-strategy', 'fixed-frequency', 'cron', 'redelivery-policy']

# List of Tags that should avoid being stored as processes, usually because they get put into a control flow element that shares a common prefix.
# Note - don't include namespace which may lead to issues if any processors of one namespace use the same tag as another namespace's element
NEVER_PROCESSOR_TAGS = ['transform', 'process-records', 'step', 'aggregator', 'on-complete']

class MuleFlowElement:
        
    def __init__(self, 
                 tag: str, 
                 attributes: Dict[str, str] = None, 
                 children: List['MuleFlowElement'] = None, 
                 processes: List['MuleFlowElement'] = None, 
                 content: str = "",
                 notes: str = "", 
                 standalone: bool = True, 
                 error_handler_ref: Optional[str] = None,
                 error_handler_element: Optional[List['MuleFlowElement']] = None):
        self.tag = tag
        self.attributes = attributes or {}
        
        self.children = children or []
        self.processes = processes or []
        self.content = content
        print(f"Processing {self.tag}")

        self.notes = notes
        self.standalone = standalone
        self.error_handler_ref = error_handler_ref
        self.error_handler_element = error_handler_element

    def __str__(self):
        # A Case Statement to handle stringifying the tag based on the key attributes of the element
        # Defaults to name if no other identifier is found
        # Extend as needed
        if self.tag == 'set-variable':
            identifier = self.attributes.get('variableName') or ''
        elif self.tag in ['on-error-propagate', 'on-error-continue']:
            identifier = self.attributes.get('when') or self.attributes.get('type') or '' 
        else:
            identifier = self.attributes.get('name') or self.attributes.get('documentation:name') or ''
        return f"{self.tag} [{identifier}]" if identifier else self.tag

    def add_child(self, child: 'MuleFlowElement'):
        self.children.append(child)

    def set_note(self, note: str):
        self.notes = note

    def set_error_handler_ref(self, ref: str):
        self.error_handler_ref = ref

    """
    Get all flows in the current element
    If flow_name is provided, return only the flow with that name
    """
    def get_flows(self, flow_name: str = None) -> List['MuleFlowElement']:
        flows = []
        for child in self.children:
            if child.tag in ['flow']:
                if flow_name is None or child.attributes.get('name') == flow_name:
                    flows.append(child)
        return flows

class MuleFlowAnalyzer:
    def __init__(self, project_path: str, property_files: PropertyHierarchy = None):
        self.project_path = project_path
        self.project_files = {}
        self.properties_hierarchy = PropertyHierarchy({})
        self.discovered_properties = None

        # Debugging Flag - will be replaced with actual input flag later
        self.debug_xml = True
        self.debug_options = {
            "file": False,
            "tag": False,
            "attributes": False,
            "content": False
        }

        # Output Type Flag - will be replaced with actual input flag later
        self.output_format = OutputFormat.SEQUENCE

        # Tags to skip when printing the flow structure
        self.skip_tags = ["flow-ref", "logger", "tracing:set-logging-variable"]

        self._validate_project_path()
        self._discover_project_files()

        # If property_files is provided, validate using set_properties_hierarchy
        # Otherwise, discover the properties files and use all in order
        if property_files:
            self.set_properties_hierarchy(property_files)
        else:
            self._populate_properties_hierarchy()

    def _validate_project_path(self):
        path = Path(self.project_path).resolve()
        
        if not path.exists():
            raise ValueError(f"Project path does not exist: {path}")
        
        mule_dir = path / "src" / "main" / "mule"
        if not mule_dir.is_dir():
            raise ValueError(f"Invalid project structure. Missing src/main/mule directory: {mule_dir}")
        
        xml_files = list(mule_dir.glob("**/*.xml"))
        if not xml_files:
            raise ValueError(f"No XML files found in {mule_dir}")
        
        mule_files = [f for f in xml_files if self._is_mule_file(f)]
        if not mule_files:
            raise ValueError(f"No Mule configuration files found in {mule_dir}")

    def _is_mule_file(self, file_path: Path) -> bool:
        try:
            with file_path.open('r') as f:
                content = xmltodict.parse(f.read())
                return 'mule' in content
        except Exception:
            return False

    def _discover_project_files(self):
        mule_dir = Path(self.project_path) / "src" / "main" / "mule"
        for xml_file in mule_dir.glob("**/*.xml"):
            if self._is_mule_file(xml_file):
                relative_path = xml_file.relative_to(self.project_path)
                with xml_file.open('r') as f:
                    self.project_files[str(relative_path)] = f.read()
                pass


    # Recursive Helper Function to convert XML Text to a MuleFlowElement
    def xml_to_mule_flow_element(self, xml_string):
        def create_mule_flow_element(element: ET.Element) -> MuleFlowElement | None:
            def process_tag_or_attribute(name):
                parts = name.split('}')
                if len(parts) > 1:
                    namespace = parts[0].split('/')[-1]
                    tag = parts[-1]
                    # In line with Studio markup, ignore core namespace in tag names
                    if namespace != 'core':
                        return f"{namespace}:{tag}"
                    else:
                        if parts[0].split('/')[-2] == 'ee':
                            return f"ee:{tag}"
                        else:
                            return tag
                return name

            tag = process_tag_or_attribute(element.tag)
            attributes = {process_tag_or_attribute(k): v for k, v in element.attrib.items()}

            # If the element has no attributes, content, and no children of their own, skip it
            if not element.attrib and (not element.text or element.text.strip() == ''):
                # No content and no children = Skip
                if len(element) == 0:
                    return None

            
            children = []
            processes = []

            for child in element:
                if len(child) > 0 or not child.get('attributes', None) or len(child.get('text', '').strip()) > 0:
                    new_child = create_mule_flow_element(child)
                    if new_child is not None:

                        # if tag is always to be a processor, add as process instead of child
                        if new_child.tag in ALWAYS_PROCESSOR_TAGS:
                            processes.append(new_child)
                        elif ':' in new_child.tag:
                            # if tag prefix (before ":") matches, add as process instead of child
                            # With some exceptions of known flow elements
                            if ':' in new_child.tag and new_child.tag.split(':')[1] not in NEVER_PROCESSOR_TAGS and new_child.tag.split(':')[0] == tag.split(':')[0]:
                                processes.append(new_child)
                            else:
                                children.append(new_child)
                        else:
                            children.append(new_child)

            # Check if the element has an error-handler
            error_handler_ref = None
            error_handler_element = None
            for child in children:
                if child.tag == 'error-handler':
                    if child.attributes.get('ref', None):
                        error_handler_ref = child.attributes.get('ref')
                    elif len(child.children) > 0:
                        error_handler_ref = "Inline Error Handler"
                        error_handler_element = child
                    children.remove(child)
                    break
            
            if element.text and element.text.strip():
                content = element.text.strip()
            else:
                content = None

            return MuleFlowElement(
                tag=tag,
                attributes=attributes,
                children=children,
                processes=processes,
                content=content,
                error_handler_ref=error_handler_ref,
                error_handler_element=error_handler_element
            )

        if xml_string is not None:
            tree = ET.fromstring(xml_string)
            
            if tree is not None:
                return create_mule_flow_element(tree)
            else:
                raise ValueError("No 'mule' element found in the XML.")

    def _populate_properties_hierarchy(self):
        resources_dir = Path(self.project_path) / "src" / "main" / "resources"

        # Ensure properties_hierarchy is initialized
        if self.properties_hierarchy is None:
            self.properties_hierarchy = PropertyHierarchy({})

        for file_pattern in ["**/*.properties", "**/*.yaml"]:
            for prop_file in resources_dir.glob(file_pattern):
                relative_path = prop_file.relative_to(resources_dir)
                if str(relative_path) not in self.properties_hierarchy.values():
                    next_index = len(self.properties_hierarchy)
                    self.properties_hierarchy[next_index] = str(relative_path)

    def get_properties_hierarchy(self) -> PropertyHierarchy:
        return self.properties_hierarchy

    def set_properties_hierarchy(self, property_files: PropertyHierarchy):
        resources_dir = Path(self.project_path) / "src" / "main" / "resources"
        
        for index, file_path in property_files.items():
            full_path = resources_dir / file_path
            if not full_path.is_file():
                raise ValueError(f"Property file not found: {full_path}")
            if not os.access(full_path, os.R_OK):
                raise ValueError(f"Property file is not readable: {full_path}")
        
        self.properties_hierarchy = property_files

    def _discover_properties_keys(self):
        self.discovered_properties = {}
        self.properties_keys = set()  # Initialize properties_keys as a set
        resources_dir = Path(self.project_path) / "src" / "main" / "resources"

        for index, file_path in self.properties_hierarchy.items():
            full_path = resources_dir / file_path
            self.discovered_properties[str(full_path)] = {}

            if file_path.endswith('.properties'):
                with open(full_path, 'r') as file:
                    for line in file:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            key, value = line.split('=', 1)
                            self.discovered_properties[str(full_path)][key.strip()] = value.strip()
                            self.properties_keys.add(key.strip())

            elif file_path.endswith('.yaml'):
                with open(full_path, 'r') as file:
                    yaml_data = yaml.safe_load(file)
                    flat_dict = self._flatten_dict(yaml_data)
                    self.discovered_properties[str(full_path)] = flat_dict
                    self.properties_keys.update(flat_dict.keys())

    def _flatten_dict(self, d, parent_key='', sep='.'):
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    def _prepare_analysis_xml(self, flow_name: str = None):
        # Process the supplied properties files and get all keys
        self._discover_properties_keys()

        # 1. Replace all property keys in the XML files with the values from the properties files
        for xml_file, xml_content in self.project_files.items():
            # Process the XML structure in its raw form
            # Replace all property keys in the XML with the values from the properties files
            if flow_name is None or flow_name in xml_content:
                self.project_files[xml_file] = self._process_xml_structure_replace_placeholders(xml_content)
            else:
                # Remove the XML file from the project_files if it doesn't match the flow_name
                self.project_files[xml_file] = None
            pass

    def _prepare_analysis_to_mule_flow_elements(self):
        # 2. Convert the XML structure to a MuleFlowElement
        for xml_file, xml_content in self.project_files.items():
            self.project_files[xml_file] = self.xml_to_mule_flow_element(xml_content)

        # 3. Find all Flow Refs and insert the actual flow content
        self._process_flow_refs()


    def print_flow_structures(self, xml_file: str, flow_name: str = None):
        """
        Print the structure of flows in the given XML file.

        This function processes and prints the structure of all flows found in the specified XML file.
        If a flow name is provided, it will only print the structure of that specific flow.

        Args:
            xml_file (str): The path to the XML file containing the flows.
            flow_name (str, optional): The name of a specific flow to print. If None, all flows are printed.

        Returns:
            None
        """
        mule_flow_element = self.project_files[xml_file]
        flows = mule_flow_element.get_flows(flow_name) # If flow_name is None, returns all flows

        # Process all flows in the file
        if len(flows) > 0:
            print(f"Processing {xml_file}")
            for flow in flows:
                # Initial Depth of 1
                depth = 0

                current_flow_name = flow.attributes.get('name') or 'Unnamed Flow'
                print(f"Flow: {current_flow_name}")
                
                # Print Element Structure (Regardless of output format)
                self._print_element_structure(flow, depth)
                
                print()  # Add a blank line after each flow for readability
            print()  # Add an extra blank line after processing all flows and sub-flows in this file

    def _print_element_structure(self, element:MuleFlowElement, depth:int):
        indent = "  " * depth

        if element.tag not in self.skip_tags:                   
            print(f"{indent}{element}")
            depth += 1
        for child in element.children:
            self._print_element_structure(child, depth)

    def _process_flow_refs(self):
        flow_cache = {}

        def find_flow(name):
            if name in flow_cache:
                return flow_cache[name]

            for mule_element in self.project_files.values():
                # This only finds flows and sub-flows at the root level (e.g. mule tag)
                for mule_child_element in mule_element.children:
                    if mule_child_element.tag in ['flow', 'sub-flow']:
                        if mule_child_element.attributes.get('name') == name:
                            flow_cache[name] = mule_child_element
                            return mule_child_element
            return None

        def replace_flow_refs(element:MuleFlowElement):
            if element.tag == 'flow-ref':
                flow_ref_name = element.attributes.get('name')
                referenced_flow = find_flow(flow_ref_name)
                if referenced_flow:
                    # Ensure the element has a "children" property
                    if len(element.children) == 0:
                        element.children = []
                    # Append the referenced flow with the actual flow content
                    # Ordering doesn't matter as flow-refs have no children
                    element.add_child(referenced_flow)
                else:
                    raise ValueError(f"Flow Ref not found in project: {flow_ref_name}")
            else:
                if len(element.children) > 0:
                    for child in element.children:
                        replace_flow_refs(child)
            
            return element

        # Process all files in self.project_files
        for xml_file, mule_flow_element in self.project_files.items():
            self.project_files[xml_file] = replace_flow_refs(mule_flow_element)

    def _contains_placeholder(self, text):
        return ('${' in text and '}' in text) or ('Mule::p(' in text) or ('p(' in text and ("'" in text or '"' in text))

    def _process_xml_structure_replace_placeholders(self, xml_string):
        def replace_placeholders(text):
            def replace_placeholder_value(placeholder, wrapper=None):
                for _, prop_dict in sorted(self.discovered_properties.items()):
                    if placeholder in prop_dict:
                        return prop_dict[placeholder]
                # Return original if no replacement found, using the appropriate wrapper
                if wrapper == 'Mule::p':
                    return f"Mule::p({placeholder})"
                elif wrapper == 'p':
                    return f"p('{placeholder}')"
                else:
                    return f"${{{placeholder}}}"
                       
            # Handle ${...} placeholders
            text = re.sub(r'\$\{([^}]+)\}', lambda m: replace_placeholder_value(m.group(1)), text)
            
            # Handle Mule::p(...) placeholders
            text = re.sub(r'Mule::p\(([^)]+)\)', lambda m: replace_placeholder_value(m.group(1).strip("'\""), 'Mule::p'), text)
            
            # Handle p('...') or p("...") placeholders
            text = re.sub(r"p\((['\"])([^)]+)\1\)", lambda m: replace_placeholder_value(m.group(2), 'p'), text)
            
            return text

        def process_tag(match):
            full_tag = match.group(0)
            tag_name = match.group(1)
            attributes = match.group(2)
            #print(f"OLD TAG: {full_tag}")
            
            if attributes:
                # Process attributes
                attributes = re.sub(r'(\w+)=(["\'])(.*?)\2', 
                                    lambda m: f'{m.group(1)}={m.group(2)}{replace_placeholders(m.group(3))}{m.group(2)}',
                                    attributes)
            
            # Reconstruct the tag with processed attributes
            #print(f"NEW TAG: <{tag_name}{attributes}>")
            return f"<{tag_name}{attributes}>"

        # Replace placeholders in tag attributes
        xml_string = re.sub(r'<(\w+)([^>]*)>', process_tag, xml_string)
        
        # Replace placeholders in text content
        xml_string = re.sub(r'>([^<]+)<', lambda m: f'>{replace_placeholders(m.group(1))}<', xml_string)
        
        return xml_string

    def analyze_mule_flows(self, flow_name: str = None):
        self._prepare_analysis_xml(flow_name)

        if flow_name is not None:
            # Remove any None values from project_files
            self.project_files = {k: v for k, v in self.project_files.items() if v is not None}

        self._prepare_analysis_to_mule_flow_elements()

        # Print the flow and sub-flow structures
        for xml_file, xml_content in self.project_files.items():
            if self.output_format == OutputFormat.TEXT:
                # Print flow and sub-flow structures
                self.print_flow_structures(xml_file)
            elif self.output_format == OutputFormat.SEQUENCE:
                self.generate_sequence_diagram(xml_file, flow_name)

    def generate_sequence_diagram(self, xml_file: str, flow_name: str = None):
        
        mule_flow_element = self.project_files[xml_file]
        flows = mule_flow_element.get_flows(flow_name) # If flow_name is None, returns all flows
        
        from src.sequence_diagram_generator import SequenceDiagramGenerator
        mule_sequence_diagram_generator = SequenceDiagramGenerator()

        for flow in flows:
            diagram_syntax = mule_sequence_diagram_generator.generate_sequence_diagram_syntax(flow)
            image_file = mule_sequence_diagram_generator.render_image(diagram_syntax, flow.attributes.get('name'))
            legend_file = mule_sequence_diagram_generator.render_legend(mule_sequence_diagram_generator.arrow_legend, flow.attributes.get('name'))
            print(f"Generated {image_file}")



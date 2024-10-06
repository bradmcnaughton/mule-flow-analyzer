import os
import xmltodict
from pathlib import Path
from typing import Dict, NewType
import yaml
import re

# Type for the Property Files Hierarchy
PropertyHierarchy = NewType('PropertyHierarchy', Dict[int, str])

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
        self.output_format = "SEQUENCE" # alternative "TEXT"

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
                    self.project_files[str(relative_path)] = xmltodict.parse(f.read())

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

    def _prepare_analysis(self):
        # Process the supplied properties files and get all keys
        self._discover_properties_keys()

        # Remove Unneeded Elements from the XML
        unneeded_elements = ["logger", "error-handler"]
        for xml_file, xml_content in self.project_files.items():
            self.project_files[xml_file] = self._remove_unneeded_elements(xml_content, unneeded_elements)

        # Replace all property keys in the XML files with the values from the properties files
        for xml_file, xml_content in self.project_files.items():
            # Process the root element of the XML structure
            self._process_xml_structure_replace_placeholders(xml_content)

        # Find all Flow Refs and replace them with the actual flow content
        self._process_flow_refs()


    def _print_flow_structures(self, xml_file, xml_content):
        mule_element = xml_content.get('mule', {})
        flows = mule_element.get('flow', [])

        # Ensure flows and sub_flows are lists
        flows = [flows] if isinstance(flows, dict) else (flows or [])

        # Process all flows
        if len(flows) > 0:
            syntax_list = []
            for flow in flows:
                if self.output_format == "TEXT":
                    print(f"Processing {xml_file}")
                flow_name = flow.get('@name', 'Unnamed Flow')
                if self.output_format == "TEXT":
                    print(f"Flow: {flow_name}")
                self._print_element_structure(flow, 1, syntax_list)
                if self.output_format == "TEXT":
                    print()  # Add a blank line after each flow

            if self.output_format == "SEQUENCE":
                # Generate the syntax for the sequence diagram
                seq_diagram_syntax_list = self.generate_sequence_diagram_syntax(syntax_list, flow_name)
                # Print the syntax for the sequence diagram
                #for line in seq_diagram_syntax_list:
                for line in syntax_list:
                    print(line)
                    # Add a blank line after each line of the sequence diagram
                    print()

            if self.output_format == "TEXT":
                print()  # Add an extra blank line after processing all flows and sub-flows in this file

    def _print_element_structure(self, element, depth, syntax_list):
        if isinstance(element, dict):
            for tag, content in element.items():
                if tag.startswith('@'):  # Skip attributes
                    continue
                
                indent = "  " * depth
                doc_name = element.get('@doc:name', '')
                doc_name_str = f" [{doc_name}]" if doc_name else ''
                                
                if self.output_format == "TEXT":
                    print(f"{indent}{tag}{doc_name_str}")
                elif self.output_format == "SEQUENCE":
                    syntax_list.append(f"{indent}{tag}{doc_name_str}")
                if isinstance(content, (dict, list)):
                    self._print_element_structure(content, depth + 1, syntax_list)
        elif isinstance(element, list):
            for item in element:
                self._print_element_structure(item, depth, syntax_list)


    def _remove_unneeded_elements(self, xml_content, unneeded_elements):
        def remove_elements(element):
            if isinstance(element, dict):
                for tag in list(element.keys()):
                    if tag in unneeded_elements:
                        del element[tag]
                    elif isinstance(element[tag], (dict, list)):
                        remove_elements(element[tag])
            elif isinstance(element, list):
                for item in element:
                    if isinstance(item, dict):
                        # Remove unneeded elements from the dict
                        for tag in unneeded_elements:
                            if tag in item:
                                del item[tag]
                        # Recursively process remaining elements
                        remove_elements(item)

        # Create a deep copy of the xml_content to avoid modifying the original
        import copy
        xml_content_copy = copy.deepcopy(xml_content)
        remove_elements(xml_content_copy)
        return xml_content_copy

    def _process_flow_refs(self):
        flow_cache = {}

        def find_flow(name):
            if name in flow_cache:
                return flow_cache[name]

            for content in self.project_files.values():
                flows = content.get('mule', {}).get('flow', [])
                sub_flows = content.get('mule', {}).get('sub-flow', [])
                
                for flow in (flows if isinstance(flows, list) else [flows]) + (sub_flows if isinstance(sub_flows, list) else [sub_flows]):
                    if flow.get('@name') == name:
                        flow_cache[name] = flow
                        return flow
            return None

        def replace_flow_refs(element):
            if isinstance(element, dict):
                for tag, content in list(element.items()):  # Use list() to avoid runtime error when modifying dict
                    if tag == 'flow-ref':
                        if isinstance(content, list):
                            new_content = []
                            for flow_ref in content:
                                ref_name = flow_ref.get('@name')
                                if ref_name:
                                    referenced_flow = find_flow(ref_name)
                                    if referenced_flow:
                                        replace_flow_refs(referenced_flow)
                                        new_content.append(referenced_flow)
                                    else:
                                        new_content.append(flow_ref)
                                else:
                                    new_content.append(flow_ref)
                            element[tag] = new_content
                        else:
                            ref_name = content.get('@name')
                            if ref_name:
                                referenced_flow = find_flow(ref_name)
                                if referenced_flow:
                                    replace_flow_refs(referenced_flow)
                                    element[tag] = referenced_flow
                    elif isinstance(content, (dict, list)):
                        replace_flow_refs(content)
            elif isinstance(element, list):
                for item in element:
                    replace_flow_refs(item)

        # Process all files in self.project_files
        for xml_file, xml_content in self.project_files.items():
            replace_flow_refs(xml_content)
            self.project_files[xml_file] = xml_content

    def _contains_placeholder(self, text):
        return ('${' in text and '}' in text) or ('Mule::p(' in text) or ('p(' in text and ("'" in text or '"' in text))

    def _resolve_placeholder(self, text):
        def replace_placeholder(placeholder, wrapper=None):
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

        # Handle ${...} placeholders, including those wrapped in quotes
        text = re.sub(r'(?:\'|\")?\$\{([^}]+)\}(?:\'|\")?', lambda m: replace_placeholder(m.group(1)), text)

        # Handle Mule::p(...) placeholders
        text = re.sub(r'Mule::p\(([^)]+)\)', lambda m: replace_placeholder(m.group(1).strip("'\""), 'Mule::p'), text)

        # Handle p('...') or p("...") placeholders
        text = re.sub(r"p\((['\"])([^)]+)\1\)", lambda m: replace_placeholder(m.group(2), 'p'), text)

        return text

    def _process_xml_structure_replace_placeholders(self, element, indent=0):
        indent_str = "  " * indent
        
        if isinstance(element, dict):
            for tag, content in element.items():
                if isinstance(content, dict):
                    if self.debug_xml and self.debug_options["tag"]:
                        print(f"{indent_str}Tag: {tag}")
                    if '@attributes' in content:
                        for attr_key, attr_value in content['@attributes'].items():
                            if isinstance(attr_value, str) and self._contains_placeholder(attr_value):
                                content['@attributes'][attr_key] = self._resolve_placeholder(attr_value)
                    if '#text' in content:
                        if isinstance(content['#text'], str) and self._contains_placeholder(content['#text']):
                            content['#text'] = self._resolve_placeholder(content['#text'])
                    self._process_xml_structure_replace_placeholders(content, indent + 1)
                elif isinstance(content, list):
                    for item in content:
                        if self.debug_xml and self.debug_options["tag"]:
                            print(f"{indent_str}Tag: {tag} (repeated)")
                        self._process_xml_structure_replace_placeholders(item, indent + 1)
                else:
                    if isinstance(content, str) and self._contains_placeholder(content):
                        element[tag] = self._resolve_placeholder(content)
                    if self.debug_xml and self.debug_options["content"]:
                        print(f"{indent_str}Tag: {tag}, Content: {element[tag]}")
        elif isinstance(element, list):
            for item in element:
                self._process_xml_structure_replace_placeholders(item, indent)
        


    """
    E.G.
    VM->Mule Application: VM Listener Trigger
    Mule Application->Email Service: Send Email
    Email Service->Email Service: Set To Addresses
    Email Service->Email Service: Set Reply-To Addresses
    Email Service->Email Service: Set Email Body
    Email Service-->Mule Application: Email Sent
    Mule Application-->VM: Response


    
    """

    def generate_sequence_diagram_syntax(self, flow_lines, flow_name:str=None):
        seq_diagram_syntax_list = []

        current_actor = "Mule Application"  # Default actor for top-level operations
        previous_actor = None
        actor_stack = []  # To track nested actors based on indentation levels
        indent_level = 0

        if flow_name:
            seq_diagram_syntax_list.append(f"title {flow_name}")

        for line in flow_lines:
            stripped_line = line.strip()

            # Calculate the indentation level to understand the nesting
            new_indent_level = (len(line) - len(stripped_line)) // 2

            # If the new indent level is greater than the current, it's a nested flow
            if new_indent_level > indent_level:
                actor_stack.append(current_actor)
                current_actor = stripped_line
                seq_diagram_syntax_list.append(f"{current_actor}->Mule Application: {flow_name}")


            # Handle 'Flow' (reset actors stack for a new flow)
            if line.startswith("Flow:"):
                flow_name = line.split(":")[1].strip()
                seq_diagram_syntax_list.append(f"Client->Mule Application: {flow_name}")

            # Handle 'vm:listener' and 'flow-ref' as flow steps
            elif line.startswith("vm:listener"):
                seq_diagram_syntax_list.append("VM->Mule Application: VM Listener Trigger")

            elif line.startswith("flow-ref"):
                seq_diagram_syntax_list.append(f"Mule Application->Mule Application: {line}")

            # Handle database interactions
            elif line.startswith("db:"):
                db_action = line.split(":")[1].strip()
                if db_action == "stored-procedure":
                    seq_diagram_syntax_list.append(f"Mule Application->Database: Call stored procedure ({line.split()[1]})")
                elif db_action == "select":
                    seq_diagram_syntax_list.append(f"Mule Application->Database: Select from database ({line})")

            # Handle HTTP requests (like POST or GET)
            elif line.startswith("http:request"):
                seq_diagram_syntax_list.append("Mule Application->HTTP API: POST /completions (Set headers and body)")

            # Handle email sending actions
            elif line.startswith("email:send"):
                seq_diagram_syntax_list.append("Mule Application->Email Service: Send Email")
            elif line.startswith("email:to-addresses"):
                seq_diagram_syntax_list.append("Email Service->Email Service: Set To Addresses")
            elif line.startswith("email:reply-to-addresses"):
                seq_diagram_syntax_list.append("Email Service->Email Service: Set Reply-To Addresses")
            elif line.startswith("email:body"):
                seq_diagram_syntax_list.append("Email Service->Email Service: Set Email Body")

            # Handle payload setting or variable setting in MuleSoft
            elif line.startswith("set-variable"):
                seq_diagram_syntax_list.append(f"Mule Application->Mule Application: {line}")
            elif line.startswith("ee:transform"):
                seq_diagram_syntax_list.append(f"Mule Application->Mule Application: {line}")
            elif line.startswith("set-payload"):
                seq_diagram_syntax_list.append("Mule Application->Mule Application: Set Payload")

            # Handle async operations
            elif line.startswith("async"):
                seq_diagram_syntax_list.append("Mule Application->Mule Application: Async Operation")

            # Handle VM publish (e.g., publish to email queue)
            elif line.startswith("vm:publish"):
                seq_diagram_syntax_list.append("Mule Application->Email Queue: Publish to Email Queue")

            # Handle conditional logic (e.g., "when" and "otherwise")
            elif line.startswith("when"):
                condition = line.split("[")[1].split("]")[0].strip()
                seq_diagram_syntax_list.append(f"alt {condition}")
            elif line.startswith("otherwise"):
                seq_diagram_syntax_list.append("else")

            # Handle end of alternate paths (end of conditions)
            elif line.startswith("end"):
                seq_diagram_syntax_list.append("end")

        # Return the final syntax list
        return seq_diagram_syntax_list


    def analyze_mule_flows(self):
        self._prepare_analysis()

        # Print the flow and sub-flow structures
        for xml_file, xml_content in self.project_files.items():
            # Print flow and sub-flow structures
            self._print_flow_structures(xml_file, xml_content)
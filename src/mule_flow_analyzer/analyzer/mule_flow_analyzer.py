from enum import Enum
import os
import xmltodict
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, NewType, Optional
import yaml
import re
import copy
import logging
from ..config.default_properties import DEFAULT_PROPERTIES
from ..config.constants import OutputFormat, normalize_output_format
from .mule_flow_element import MuleFlowElement
from .sequence_diagram_generator import SequenceDiagramGenerator
from .mermaid_sequence_diagram_generator import MermaidSequenceDiagramGenerator
from .natural_language_description_generator import NaturalLanguageDescriptionGenerator

logger = logging.getLogger(__name__)

# Type for the Property Files Hierarchy
PropertyHierarchy = NewType('PropertyHierarchy', Dict[int, str])

try:
    ALWAYS_PROCESSOR_TAGS = DEFAULT_PROPERTIES.get('analyzer_properties', {}).get('tag_rules', {}).get('always_processors', [])
except Exception:
    ALWAYS_PROCESSOR_TAGS = []

try:
    NEVER_PROCESSOR_TAGS = DEFAULT_PROPERTIES.get('analyzer_properties', {}).get('tag_rules', {}).get('never_processors', [])
except Exception:
    NEVER_PROCESSOR_TAGS = []

class MuleFlowAnalyzer:
    
    def __init__(self, project_path: str = None, property_files: PropertyHierarchy = None, user_config: dict = None):
        """
        Initialize a MuleFlowAnalyzer instance for analyzing Mule projects.

        This constructor sets up the analyzer with project configuration, property files,
        and user-defined settings. It can handle both complete project initialization
        and deferred initialization where paths and properties are set later.

        Args:
            project_path (str, optional): Path to the root of the Mule project.
                                        If provided, initializes project files and properties.
            property_files (PropertyHierarchy, optional): Dictionary mapping priority (int) to
                                                        property file paths (str) relative to
                                                        src/main/resources/.
            user_config (dict, optional): Custom configuration to override default properties.
                                        Will be merged with DEFAULT_PROPERTIES.

        Attributes:
            project_path (str): Root path of the Mule project
            project_files (dict): Dictionary of discovered Mule configuration files
            properties_hierarchy (PropertyHierarchy): Ordered hierarchy of property files
            configuration_properties (dict): Merged default and user configuration
            output_format (OutputFormat): Format for analysis output (sequence/text)
            debug_xml (bool): Flag for XML debugging
            debug_options (dict): Debugging configuration options

        Note:
            - If project_path is provided, validates project structure and discovers files
            - Property files are processed in order of their hierarchy index
            - Default properties can be found in DEFAULT_PROPERTIES

        Example:
            >>> analyzer = MuleFlowAnalyzer(
            ...     project_path="path/to/project",
            ...     property_files={0: "properties/dev.yaml", 1: "properties/common.properties"},
            ...     user_config={"analyzer_properties": {"output_type": "TEXT"}}
            ... )
        """
        self.project_path = project_path
        self.project_files = {}
        self.properties_hierarchy = PropertyHierarchy({})
        self.discovered_properties = None

        # Debugging Flags - will be replaced with actual input flag later
        # TODO: Allow these to be set in config file
        self.debug_xml = True
        self.debug_options = {
            "file": False,
            "tag": False,
            "attributes": False,
            "content": False
        }

        # Merge user config with default properties       
        if user_config:
            self.configuration_properties = self._recursive_merge(DEFAULT_PROPERTIES, user_config)
        else:
            self.configuration_properties = copy.deepcopy(DEFAULT_PROPERTIES)

        # Output Type Flag - will be replaced with actual input flag later
        self.output_format = normalize_output_format(
            self.configuration_properties.get('analyzer_properties', {}).get('output_type', OutputFormat.SEQUENCE)
        )

        # Tags to skip when printing the flow structure
        self.skip_tags = ["flow-ref", "logger", "tracing:set-logging-variable"]

        # Validate and discover project files if project_path is provided
        if project_path is not None:
            self._validate_project_path()
            self._discover_project_files()

            # If property_files is provided, validate using set_properties_hierarchy
            # Otherwise, discover the properties files and use all in order
            if property_files:
                self.set_properties_hierarchy(property_files)
            else:
                self._populate_properties_hierarchy()

    def set_project_path(self, project_path: str):
        """
        Set or update the Mule project path and initialize project resources.

        This method allows for deferred or updated project path initialization. It validates
        the project structure, discovers Mule configuration files, and processes property files.

        Args:
            project_path (str): Path to the root of the Mule project directory.
                              Must contain a valid src/main/mule structure.

        Raises:
            ValueError: If the project path is invalid or missing required structure.

        Note:
            - Automatically discovers and processes property files if no hierarchy is set
            - Re-validates property hierarchy if one was previously set
            - Updates internal project files cache

        Example:
            >>> analyzer = MuleFlowAnalyzer()
            >>> analyzer.set_project_path("/path/to/mule/project")
        """
        self.project_path = project_path
        
        logger.info(f"Setting project path to: {self.project_path}")
        
        self._validate_project_path()
        self._discover_project_files()

        if self.properties_hierarchy:
            self.set_properties_hierarchy(self.properties_hierarchy)
        else:
            self._populate_properties_hierarchy()

    def set_properties_hierarchy(self, property_files: PropertyHierarchy):
        """
        Set or update the hierarchy of property files for placeholder resolution.

        This method establishes the order in which property files are processed when
        resolving property placeholders in Mule configuration files. Files are processed
        in order of their integer key in the hierarchy.

        Args:
            property_files (PropertyHierarchy): Dictionary mapping priority (int) to
                                              property file paths (str) relative to
                                              src/main/resources/.

        Raises:
            ValueError: If any property file in the hierarchy doesn't exist or isn't readable
                       when project_path is set.

        Note:
            - Lower integer keys have higher priority in property resolution
            - Property files can be either .properties or .yaml format
            - All paths should be relative to src/main/resources
            - If project_path is not set, only stores the hierarchy without validation
        """
        # Store the hierarchy regardless of project_path
        self.properties_hierarchy = property_files
        logger.info(f"Setting properties hierarchy to: {self.properties_hierarchy}")

        # Skip validation if project_path is not set
        if self.project_path is None:
            logger.debug("Project path not set, skipping property file validation")
            return

        # Now that we know project_path is set, proceed with validation
        resources_dir = Path(self.project_path) / "src" / "main" / "resources"
        
        # Validate all property files exist and are readable
        for index, file_path in property_files.items():
            full_path = resources_dir / file_path
            if not full_path.is_file():
                raise ValueError(f"Property file not found: {full_path}")
            if not os.access(full_path, os.R_OK):
                raise ValueError(f"Property file is not readable: {full_path}")
        
        # Trigger property discovery if project path is set
        self._discover_properties_keys()

    def _recursive_merge(self, defaults, overrides):
        """
        Recursively merge two dictionaries.
        Values from `overrides` take precedence.
        """
        
        if not isinstance(overrides, dict):
            return overrides  # Base case: non-dict value, use overrides
        
        merged = copy.deepcopy(defaults)
        for key, value in overrides.items():
            if key in merged and isinstance(merged[key], dict):
                merged[key] = self._recursive_merge(merged[key], value)
            else:
                merged[key] = value
        return merged   

    def _validate_project_path(self):
        path = Path(self.project_path).resolve()
        
        if not path.exists():
            raise ValueError(f"Project path does not exist: {path}")
        
        mule_dir = path / "src" / "main" / "mule"
        if not mule_dir.is_dir():
            raise ValueError(f"Invalid Mule project structure. Missing src/main/mule directory at: {path}. Ensure the utility is run from the root of the Mule project, or with the -p flag pointing to the root of a Mule project.")
        
        xml_files = list(mule_dir.glob("**/*.xml"))
        if not xml_files:
            raise ValueError(f"No XML files found in {mule_dir}")
        
        mule_files = [f for f in xml_files if self._is_mule_file(f)]
        if not mule_files:
            raise ValueError(f"Zero Mule configuration files (XML file with a 'mule' element) were found in {mule_dir}")

    def _is_mule_file(self, file_path: Path) -> bool:
        try:
            with file_path.open('r', encoding='utf-8') as f:
                content = xmltodict.parse(f.read())
                return 'mule' in content
        except (IOError, UnicodeDecodeError) as e:
            logger.warning(f"Could not read file {file_path}: {str(e)}")
            return False
        except Exception as e:
            logger.warning(f"Error processing file {file_path}: {str(e)}")
            return False

    def _discover_project_files(self):
        try:
            mule_dir = Path(self.project_path) / "src" / "main" / "mule"
            for xml_file in mule_dir.glob("**/*.xml"):
                try:
                    if self._is_mule_file(xml_file):
                        relative_path = xml_file.relative_to(self.project_path)
                        normalized_relative_path = self._normalize_project_file_key(relative_path)
                        with xml_file.open('r', encoding='utf-8') as f:
                            self.project_files[normalized_relative_path] = f.read()
                except Exception as e:
                    logger.error(f"Error processing XML file {xml_file}: {str(e)}")
        except Exception as e:
            logger.error(f"Error discovering project files: {str(e)}")
            raise

    def _normalize_project_file_key(self, file_path: str) -> str:
        """
        Normalize project file keys to POSIX-style separators for cross-platform consistency.
        """
        return str(file_path).replace("\\", "/")

    # Recursive Helper Function to convert XML Text to a MuleFlowElement
    def xml_to_mule_flow_element(self, xml_string):
        def create_mule_flow_element(element: ET.Element) -> Optional[MuleFlowElement]:
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
                text_stripped = (child.text or '').strip()
                if len(child) > 0 or bool(child.attrib) or text_stripped:
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

            # Check if the element has an error-handler (only the first is lifted out; rest stay)
            error_handler_ref = None
            error_handler_element = None
            pruned_children = []
            first_error_handler_only = True
            for child in children:
                if child.tag == 'error-handler' and first_error_handler_only:
                    first_error_handler_only = False
                    if child.attributes.get('ref', None):
                        error_handler_ref = child.attributes.get('ref')
                    elif len(child.children) > 0:
                        error_handler_ref = "Inline Error Handler"
                        error_handler_element = child
                    continue
                pruned_children.append(child)
            children = pruned_children
            
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

    def _populate_properties_hierarchy(self, property_files: PropertyHierarchy = None):
        """
        Populate the properties hierarchy with either provided files or by discovering them.

        Args:
            property_files (PropertyHierarchy, optional): If provided, use these property files.
                                                        If None, discover all property files.
        """
        if property_files is not None:
            # Use the provided property files
            self.properties_hierarchy = property_files
            return

        # Auto-discover property files if none provided
        resources_dir = Path(self.project_path) / "src" / "main" / "resources"

        # Ensure properties_hierarchy is initialized
        if self.properties_hierarchy is None:
            self.properties_hierarchy = PropertyHierarchy({})

        for file_pattern in ["**/*.properties", "**/*.yaml", "**/*.yml"]:
            for prop_file in resources_dir.glob(file_pattern):
                relative_path = prop_file.relative_to(resources_dir)
                if str(relative_path) not in self.properties_hierarchy.values():
                    next_index = len(self.properties_hierarchy)
                    self.properties_hierarchy[next_index] = str(relative_path)

    def get_properties_hierarchy(self) -> PropertyHierarchy:
        return self.properties_hierarchy

    def _discover_properties_keys(self):
        try:
            self.discovered_properties = {}
            self.properties_keys = set()
            resources_dir = Path(self.project_path) / "src" / "main" / "resources"

            for index, file_path in self.properties_hierarchy.items():
                try:
                    full_path = resources_dir / file_path
                    self.discovered_properties[str(full_path)] = {}

                    file_suffix = Path(file_path).suffix.lower()

                    if file_suffix == '.properties':
                        with open(full_path, 'r', encoding='utf-8') as file:
                            for line in file:
                                try:
                                    line = line.strip()
                                    if line and not line.startswith('#'):
                                        key, value = line.split('=', 1)
                                        self.discovered_properties[str(full_path)][key.strip()] = value.strip()
                                        self.properties_keys.add(key.strip())
                                except ValueError as e:
                                    logger.warning(f"Invalid property line in {file_path}: {line.strip()}")
                                    continue

                    elif file_suffix in ['.yaml', '.yml']:
                        try:
                            with open(full_path, 'r', encoding='utf-8') as file:
                                yaml_data = yaml.safe_load(file)
                                flat_dict = self._flatten_dict(yaml_data)
                                self.discovered_properties[str(full_path)] = flat_dict
                                self.properties_keys.update(flat_dict.keys())
                        except yaml.YAMLError as e:
                            logger.error(f"Error parsing YAML file {file_path}: {str(e)}")
                            raise
                except Exception as e:
                    logger.error(f"Error processing property file {file_path}: {str(e)}")
                    raise
        except Exception as e:
            logger.error(f"Error discovering properties: {str(e)}")
            raise

    def _flatten_dict(self, d, parent_key='', sep='.'):
        """
        Recursively flatten a nested dictionary into a single-level dictionary with dot-notation keys.

        This method is particularly useful for processing YAML configuration files where nested
        structures need to be converted to a flat key-value format similar to .properties files.

        Args:
            d (dict): The dictionary to flatten
            parent_key (str, optional): The parent key to prepend to child keys. Defaults to empty string.
            sep (str, optional): The separator to use between nested keys. Defaults to '.'

        Returns:
            dict: A flattened dictionary where nested keys are joined with the separator

        Example:
            >>> nested = {'a': {'b': 1, 'c': {'d': 2}}, 'e': 3}
            >>> analyzer._flatten_dict(nested)
            {'a.b': 1, 'a.c.d': 2, 'e': 3}

        Note:
            - Keys in the flattened dictionary maintain their hierarchy through dot notation
            - This is commonly used to convert YAML property files to a format compatible with
              Mule-style property placeholder resolution
        """
        if d is None or not isinstance(d, dict):
            return {}
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    def _prepare_analysis_xml(self, flow_name: str = None):
        """
        Prepare XML files for analysis by processing property placeholders and filtering content.

        This method performs two main tasks:
        1. Discovers and processes all property files in the project
        2. Replaces property placeholders in XML files with their actual values
        3. Optionally filters XML content to only include files containing a specific flow

        Args:
            flow_name (str, optional): If provided, only XML files containing this flow name
                                     will be processed. If None, all XML files are processed.

        Note:
            - Property placeholders can be in formats: ${property}, Mule::p(property), or p('property')
            - The method updates self.project_files in place, setting non-matching files to None
            - Property files are processed in order according to self.properties_hierarchy

        Example:
            >>> analyzer = MuleFlowAnalyzer("path/to/project")
            >>> analyzer._prepare_analysis_xml("my-flow")  # Process only files with "my-flow"
            >>> analyzer._prepare_analysis_xml()  # Process all XML files
        """
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
        normalized_xml_file = self._normalize_project_file_key(xml_file)
        mule_flow_element = self.project_files[normalized_xml_file]
        flows = mule_flow_element.get_flows(flow_name) # If flow_name is None, returns all flows. Else, returns ALL FLOWS in the xml file that has a flow with the name matching the flow_name

        # Process all flows in the file
        if len(flows) > 0:
            logger.debug(f"Processing {xml_file}")
            for flow in flows:
                # Initial Depth of 1
                depth = 0

                current_flow_name = flow.attributes.get('name') or 'Unnamed Flow'
                print('--------------------------------')
                print(f"Flow: {current_flow_name}")
                print('--------------------------------')
                
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
                try:
                    for mule_child_element in mule_element.children:
                        if mule_child_element.tag in ['flow', 'sub-flow']:
                            if mule_child_element.attributes.get('name') == name:
                                flow_cache[name] = mule_child_element
                                return mule_child_element
                except AttributeError as e:
                    logger.warning(f"Invalid mule element structure while searching for flow {name}: {str(e)}")
                    continue
            return None

        def replace_flow_refs(element: MuleFlowElement):
            try:
                if element.tag == 'flow-ref':
                    flow_ref_name = element.attributes.get('name')
                    if not flow_ref_name:
                        logger.warning("Flow-ref found without name attribute")
                        return element
                    
                    referenced_flow = find_flow(flow_ref_name)
                    if referenced_flow:
                        if len(element.children) == 0:
                            element.children = []
                        element.add_child(referenced_flow)
                    else:
                        logger.error(f"Flow Ref not found in project: {flow_ref_name}")
                        raise ValueError(f"Flow Ref not found in project: {flow_ref_name}")
                else:
                    if len(element.children) > 0:
                        for child in element.children:
                            replace_flow_refs(child)
                
                return element
            except Exception as e:
                logger.error(f"Error processing flow reference: {str(e)}")
                raise

        try:
            for xml_file, mule_flow_element in self.project_files.items():
                try:
                    self.project_files[xml_file] = replace_flow_refs(mule_flow_element)
                except Exception as e:
                    logger.error(f"Error processing flow refs in {xml_file}: {str(e)}")
                    raise
        except Exception as e:
            logger.error(f"Error in flow reference processing: {str(e)}")
            raise

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
            
            if attributes:
                # Process attributes
                attributes = re.sub(r'(\w+)=(["\'])(.*?)\2', 
                                    lambda m: f'{m.group(1)}={m.group(2)}{replace_placeholders(m.group(3))}{m.group(2)}',
                                    attributes)
            
            # Reconstruct the tag with processed attributes
            return f"<{tag_name}{attributes}>"

        # Replace placeholders in tag attributes
        xml_string = re.sub(r'<(\w+)([^>]*)>', process_tag, xml_string)
        
        # Replace placeholders in text content
        xml_string = re.sub(r'>([^<]+)<', lambda m: f'>{replace_placeholders(m.group(1))}<', xml_string)
        
        return xml_string

    def analyze_mule_flows(self, flow_name: str = None):
        self._prepare_analysis_xml(flow_name)

        if flow_name is not None:
            logger.info(f"Analyzing specific flow only: {flow_name}")
            # Remove any None values from project_files
            self.project_files = {k: v for k, v in self.project_files.items() if v is not None}

        self._prepare_analysis_to_mule_flow_elements()

        # Print the flow and sub-flow structures
        for xml_file, xml_content in self.project_files.items():
            if self.output_format == OutputFormat.TEXT:
                # Print flow and sub-flow structures
                self.print_flow_structures(xml_file, flow_name)
            elif self.output_format == OutputFormat.SEQUENCE:
                self.generate_sequence_diagram(xml_file, flow_name)
            elif self.output_format == OutputFormat.NATURAL:
                self.generate_natural_description(xml_file, flow_name)

    def _get_sequence_diagram_generator(self):
        diagram_engine = self.configuration_properties.get('analyzer_properties', {}).get('diagram_engine', 'plantuml')
        diagram_engine = str(diagram_engine).strip().lower()

        if diagram_engine == 'plantuml':
            return SequenceDiagramGenerator(self.configuration_properties)
        if diagram_engine == 'mermaid':
            return MermaidSequenceDiagramGenerator(self.configuration_properties)

        raise ValueError(
            f"Unsupported diagram engine '{diagram_engine}'. Supported engines are: plantuml, mermaid."
        )

    def generate_sequence_diagram(self, xml_file: str, flow_name: str = None):
        """
        Generate sequence diagrams for Mule flows in the specified XML file.

        This method processes Mule flows and creates sequence diagrams to visualize the flow of data
        and interactions between components. The diagrams are saved as image files.

        Args:
            xml_file (str): The path to the XML file containing the Mule flows, relative to the project root.
                           This should be a key from the project_files dictionary.
            flow_name (str, optional): The name of a specific flow to generate a diagram for.
                                     If None, generates diagrams for all flows in the file.

        Returns:
            None: The method generates and saves diagram files but does not return any values.

        Note:
            The generated diagram files will be saved in a location determined by the
            SequenceDiagramGenerator configuration.
        """
        
        normalized_xml_file = self._normalize_project_file_key(xml_file)
        mule_flow_element = self.project_files[normalized_xml_file]
        flows = mule_flow_element.get_flows(flow_name) # If flow_name is None, returns all flows
        
        mule_sequence_diagram_generator = self._get_sequence_diagram_generator()

        for flow in flows:
            logger.info(f"Processing sequence for flow: {flow.attributes.get('name')}")
            diagram_syntax = mule_sequence_diagram_generator.generate_sequence_diagram_syntax(flow)
            
            logger.info(f"Rendering diagram for flow: {flow.attributes.get('name')}")
            image_file = mule_sequence_diagram_generator.render_image(diagram_syntax, flow.attributes.get('name'))
            
            if image_file is not None:
                logger.info(f"Generated diagram: {image_file}")

    def generate_natural_description(self, xml_file: str, flow_name: str = None):
        """
        Generate structured English descriptions for Mule flows in the specified XML file.

        Args:
            xml_file (str): The path to the XML file containing the Mule flows, relative to the project root.
            flow_name (str, optional): The name of a specific flow to describe. If None, describes all flows in the file.
        """
        normalized_xml_file = self._normalize_project_file_key(xml_file)
        mule_flow_element = self.project_files[normalized_xml_file]
        flows = mule_flow_element.get_flows(flow_name)

        description_generator = NaturalLanguageDescriptionGenerator(self.configuration_properties)

        for flow in flows:
            current_flow_name = flow.attributes.get('name')
            logger.info(f"Processing natural language description for flow: {current_flow_name}")
            description_lines = description_generator.generate_description(flow)
            output_file = description_generator.write_output(description_lines, current_flow_name)
            logger.info(f"Generated natural language description: {output_file}")

    def get_configuration_properties(self) -> dict:
        """
        Get the current configuration properties.

        Returns:
            dict: The current configuration properties
        """
        return self.configuration_properties

    def set_configuration_properties(self, config: dict) -> None:
        """
        Set new configuration properties, merging with existing defaults.

        Args:
            config (dict): New configuration properties to merge with defaults

        Returns:
            None
        """
        self.configuration_properties = self._recursive_merge(DEFAULT_PROPERTIES, config)
        # Update output format since it depends on configuration properties
        self.output_format = normalize_output_format(
            self.configuration_properties.get('analyzer_properties', {}).get('output_type', OutputFormat.SEQUENCE)
        )

    
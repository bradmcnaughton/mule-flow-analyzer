import argparse
import os
import yaml
import logging
from src.mule_flow_analyzer import MuleFlowAnalyzer, PropertyHierarchy
from src.constants import OutputFormat
from default_properties import DEFAULT_PROPERTIES
from src.constants import DEFAULT_PROJECT_PATH, PROPERTY_FILE_SELECTION_PROMPT, PROPERTY_HIERARCHY_CONFIRMATION
from src.exceptions import PropertyHierarchyError
from __init__ import __version__

# Get logging configuration from default properties
log_config = DEFAULT_PROPERTIES['analyzer_properties']['logging']
log_level = getattr(logging, log_config['level'].upper())
log_file = log_config['file']
log_format = log_config['format']

# Create output directory for logs if it doesn't exist
os.makedirs(os.path.dirname(log_file), exist_ok=True)

# Configure logging with settings from default_properties
logging.basicConfig(
    level=log_level,
    format=log_format,
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()  # This will maintain console output
    ]
)

# Suppress PlantUML Missing ~/.plantwebrc file warning which is INFO for some reason
logging.getLogger('plantweb.defaults').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

def load_user_config(file_path: str) -> dict:
    """
    Load and parse a YAML configuration file.
    
    Args:
        file_path: Path to the YAML configuration file
        
    Returns:
        dict: Parsed configuration dictionary
        
    Raises:
        FileNotFoundError: If the configuration file doesn't exist
        yaml.YAMLError: If the YAML file is invalid
    """
 
    try:
        with open(file_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.error(f"Config file not found: {file_path}")
        raise
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML config file: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error loading config file: {str(e)}")
        raise

def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments for the Mule Flow Analyzer.
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(description="Mule Flow Analyzer")
    parser.add_argument("-p", "--project-path", default=DEFAULT_PROJECT_PATH,
                        help="Path to the root directory of the Mule Project for analysis (default: current directory)")
    
    # TODO: Support external properties files
    parser.add_argument("-props", "--properties-hierarchy", 
                        help="A comma-separated list of property file names relative to the src/main/resources directory")
    parser.add_argument("-f", "--flow-name", default=None,
                        help="The name of the flow (name attribute of the flow tag) to generate a diagram for")
    parser.add_argument("-c", "--config-path", default=None,
                        help="The path to a config.yaml file the analyzer will use for diagram generation and internal settings")   
    parser.add_argument("-o", "--output-path", default=None,
                        help="The path to an output directory for the generated diagrams. Always overrides the output path in a default or custom config.yaml file")
    parser.add_argument("-s", "--plantuml-server", default=None, dest="plantuml_server",
                        help="The URL of the PlantUML server to use for diagram generation. Always overrides the server in a default or custom config.yaml file")
    parser.add_argument("--plant-format", default="png", dest="plant_format",
                        help="The format of the PlantUML diagrams to generate (png or svg). Always overrides the format in a default or custom config.yaml file")
    parser.add_argument("--output-text", action='store_true',
                        help="If set, the output will be in text format.")
    parser.add_argument('-v', '--version', action='version', version=f'Mule Flow Analyzer v{__version__}')

    args = parser.parse_args()
    # Track which arguments were explicitly provided
    args.explicit_args = {action.dest for action in parser._actions if action.dest in vars(args) and getattr(args, action.dest) != action.default}
    
    return args

def select_property_hierarchy(properties_hierarchy: PropertyHierarchy) -> PropertyHierarchy:
    """
    Select a subset of property files from the given hierarchy.
    
    Args:
        properties_hierarchy: The PropertyHierarchy object to select from
        
    Returns:
        PropertyHierarchy: A new PropertyHierarchy object with selected properties
    """
    print(PROPERTY_HIERARCHY_CONFIRMATION)
    for prop_file in properties_hierarchy:
        print(f"{prop_file}: {properties_hierarchy[prop_file]}")
                            
    selection = input(PROPERTY_FILE_SELECTION_PROMPT)
    
    try:
        selected_indices = [int(idx.strip()) for idx in selection.split(',')]
        if any(idx >= len(properties_hierarchy) for idx in selected_indices):
            raise ValueError("Selected index out of range")
        return PropertyHierarchy({i: properties_hierarchy[idx] for i, idx in enumerate(selected_indices)})
    except ValueError as e:
        logger.error("Invalid input: Please enter comma-separated numbers only")
        raise PropertyHierarchyError(str(e))

def main() -> int:
    """
    Main function for the Mule Flow Analyzer.
    
    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    try:
        
        logger.info(f"Started Mule Flow Analyzer v{__version__}")
        
        args = parse_arguments()

        project_path = os.path.join(os.getcwd(), args.project_path) if not os.path.isabs(args.project_path) else args.project_path
        
        # Validate project path exists
        if not os.path.exists(project_path):
            raise FileNotFoundError(f"Project path does not exist: {project_path}")

        properties_hierarchy = None
        flow_name = args.flow_name
        
        # User Config gets pre-populated with configuration values that will later be merged into the default properties
        # The rest of the default properties are loaded and merged in the Sequence Diagram Generator
        user_config = {}

        # Load user config if provided
        if args.config_path:
            try:
                user_config = load_user_config(args.config_path)
            except Exception as e:
                logger.error(f"Failed to load config file: {str(e)}")
                raise

        # If custom output path, create (or update) the user_config with the new output path
        if args.output_path:
            if 'analyzer_properties' not in user_config:
                user_config['analyzer_properties'] = {}
            if 'plantuml' not in user_config['analyzer_properties']:
                user_config['analyzer_properties']['plantuml'] = {}
            user_config['analyzer_properties']['plantuml']['output_directory'] = args.output_path

        # If custom output type, update the user_config with the new output type
        if args.output_text:
            if 'analyzer_properties' not in user_config:
                user_config['analyzer_properties'] = {}
            user_config['analyzer_properties']['output_type'] = OutputFormat.TEXT

        # If custom plantuml server, update the user_config with the new server
        if args.plantuml_server:
            if 'analyzer_properties' not in user_config:
                user_config['analyzer_properties'] = {}
            if 'plantuml' not in user_config['analyzer_properties']:
                user_config['analyzer_properties']['plantuml'] = {}
            user_config['analyzer_properties']['plantuml']['server'] = args.plantuml_server

        # If custom plantuml format, update the user_config with the new format
        if args.plant_format:
            if 'analyzer_properties' not in user_config:
                user_config['analyzer_properties'] = {}
            if 'plantuml' not in user_config['analyzer_properties']:
                user_config['analyzer_properties']['plantuml'] = {}
            user_config['analyzer_properties']['plantuml']['format'] = args.plant_format

        # Debug logging to see argument values
        logger.debug(f"plantuml_server: {args.plantuml_server}")
        logger.debug(f"plant_format: {args.plant_format}")
        
        # Warning if output_text is true but plant options are also explicitly passed
        if args.output_text and ('plantuml_server' in args.explicit_args or 'plant_format' in args.explicit_args):
            logger.warning("Output type is set to TEXT but PlantUML options are also passed. PlantUML options will be ignored.")

        if args.properties_hierarchy:
            try:
                prop_files = args.properties_hierarchy.split(',')
                properties_hierarchy = PropertyHierarchy({i: filename.strip() for i, filename in enumerate(prop_files)})
            except Exception as e:
                logger.error(f"Failed to process properties hierarchy: {str(e)}")
                raise

        try:
            analyzer = MuleFlowAnalyzer(project_path, properties_hierarchy, user_config)

            if not properties_hierarchy:
                properties_hierarchy = analyzer.get_properties_hierarchy()
                if properties_hierarchy:
                    logger.debug("Property files discovered in hierarchy")
                    properties_hierarchy = select_property_hierarchy(properties_hierarchy)
                    analyzer = MuleFlowAnalyzer(project_path, properties_hierarchy)
                else:
                    logger.warning("No property files discovered")

            analyzer.analyze_mule_flows(flow_name)

        except Exception as e:
            logger.error(f"Error during analysis: {str(e)}")
            raise

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        print(f"Error: {str(e)}")
        return 1  # Return error code
    
    return 0  # Return success code

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)

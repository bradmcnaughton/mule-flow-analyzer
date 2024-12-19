import argparse
import os
import yaml
import logging
from src.mule_flow_analyzer import MuleFlowAnalyzer, PropertyHierarchy
from default_properties import DEFAULT_PROPERTIES
from src.constants import DEFAULT_PROJECT_PATH, PROPERTY_FILE_SELECTION_PROMPT, PROPERTY_HIERARCHY_CONFIRMATION
from src.exceptions import PropertyHierarchyError

# Get logging configuration from default properties
log_config = DEFAULT_PROPERTIES['analyzer_properties']['logging']
log_level = getattr(logging, log_config['level'].upper())
log_file = log_config['file']

# Create output directory for logs if it doesn't exist
os.makedirs(os.path.dirname(log_file), exist_ok=True)

# Configure logging with settings from default_properties
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
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
                        help="Path to the Mule Project for analysis (default: current directory)")
    parser.add_argument("-props", "--properties-hierarchy", 
                        help="A comma-separated list of property file names relative to the src/main/resources directory")
    parser.add_argument("-f", "--flow-name", default=None,
                        help="The name of the flow to generate a diagram for")
    parser.add_argument("-c", "--config-path", default=None,
                        help="The path to a config.yaml file to use for diagram generation")   
    parser.add_argument("-o", "--output-path", default=None,
                        help="The path to the output directory for the generated diagrams. Overwrites the default output path in the config.yaml file")
    parser.add_argument("-s", "--plantuml-server", default=None,
                        help="The URL of the PlantUML server to use for diagram generation. Overwrites the default server in the config.yaml file")
    parser.add_argument("--plant-format", default="png",
                        help="The format of the PlantUML diagrams to generate (png or svg). Overwrites the default format in the config.yaml file")

    return parser.parse_args()

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
        args = parse_arguments()

        project_path = os.path.join(os.getcwd(), args.project_path) if not os.path.isabs(args.project_path) else args.project_path
        
        # Validate project path exists
        if not os.path.exists(project_path):
            raise FileNotFoundError(f"Project path does not exist: {project_path}")

        properties_hierarchy = None
        flow_name = args.flow_name
        
        # User Config gets pre-populated with configuration values that will later be merged into the default properties
        # The rest of the default properties are loaded and merged in the Sequence Diagram Generator
        user_config = None

        # Load user config if provided
        if args.config_path:
            try:
                user_config = load_user_config(args.config_path)
            except Exception as e:
                logger.error(f"Failed to load config file: {str(e)}")
                raise

        # If custom output path, create (or update) the user_config with the new output path
        if args.output_path:
            if user_config is None:
                user_config = {}
            if 'analyzer_properties' not in user_config:
                user_config['analyzer_properties'] = {}
            if 'plantuml' not in user_config['analyzer_properties']:
                user_config['analyzer_properties']['plantuml'] = {}
            user_config['analyzer_properties']['plantuml']['output_directory'] = args.output_path

        # If custom plantuml server, update the user_config with the new server
        if args.plantuml_server:
            if user_config is None:
                user_config = {}
            if 'analyzer_properties' not in user_config:
                user_config['analyzer_properties'] = {}
            if 'plantuml' not in user_config['analyzer_properties']:
                user_config['analyzer_properties']['plantuml'] = {}
            user_config['analyzer_properties']['plantuml']['server'] = args.plantuml_server

        # If custom plantuml format, update the user_config with the new format
        if args.plant_format:
            if user_config is None:
                user_config = {}
            if 'analyzer_properties' not in user_config:
                user_config['analyzer_properties'] = {}
            if 'plantuml' not in user_config['analyzer_properties']:
                user_config['analyzer_properties']['plantuml'] = {}
            user_config['analyzer_properties']['plantuml']['format'] = args.plant_format

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

import argparse
import os
import yaml
import logging
from src.mule_flow_analyzer import MuleFlowAnalyzer, PropertyHierarchy
from default_properties import DEFAULT_PROPERTIES

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
logger = logging.getLogger(__name__)

def load_user_config(file_path):
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

def main():
    try:
        parser = argparse.ArgumentParser(description="Mule Flow Analyzer")
        parser.add_argument("-p", "--project-path", default=os.getcwd(),
                            help="Path to the Mule Project for analysis (default: current directory)")
        parser.add_argument("-props", "--properties-hierarchy", 
                            help="A comma-separated list of property file names relative to the src/main/resources directory")
        parser.add_argument("-f", "--flow-name", default=None,
                            help="The name of the flow to generate a diagram for")
        parser.add_argument("-c", "--config-path", default=None,
                            help="The path to a config.yaml file to use for diagram generation")

        args = parser.parse_args()

        project_path = os.path.join(os.getcwd(), args.project_path) if not os.path.isabs(args.project_path) else args.project_path
        
        # Validate project path exists
        if not os.path.exists(project_path):
            raise FileNotFoundError(f"Project path does not exist: {project_path}")

        properties_hierarchy = None
        flow_name = args.flow_name
        user_config = None
        
        if args.config_path:
            try:
                user_config = load_user_config(args.config_path)
            except Exception as e:
                logger.error(f"Failed to load config file: {str(e)}")
                raise

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
                    print("Please Confirm Property File Hierarchy. (For Example, Prod First then Dev then Global):")
                    for prop_file in properties_hierarchy:
                        print(f"{prop_file}: {properties_hierarchy[prop_file]}")
                                        
                    selection = input("Enter the numbers of the property files to use (comma-separated, e.g., 1,5,3): ")
                    
                    try:
                        selected_indices = [int(idx.strip()) for idx in selection.split(',')]
                    except ValueError:
                        logger.error("Invalid input: Please enter comma-separated numbers only")
                        raise
                    
                    if any(idx >= len(properties_hierarchy) for idx in selected_indices):
                        raise ValueError("Selected index out of range")
                    
                    properties_hierarchy = PropertyHierarchy({i: properties_hierarchy[idx] for i, idx in enumerate(selected_indices)})
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

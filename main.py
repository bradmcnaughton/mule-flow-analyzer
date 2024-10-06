import argparse
import os
from src.mule_flow_analyzer import MuleFlowAnalyzer, PropertyHierarchy

def main():
    parser = argparse.ArgumentParser(description="Mule Flow Analyzer")
    parser.add_argument("-p", "--project-path", default=os.getcwd(),
                        help="Path to the Mule Project for analysis (default: current directory)")
    parser.add_argument("-props", "--properties-hierarchy", 
                        help="A comma-separated list of property file names relative to the src/main/resources directory")

    args = parser.parse_args()

    project_path = args.project_path
    properties_hierarchy = None

    if args.properties_hierarchy:
        prop_files = args.properties_hierarchy.split(',')
        properties_hierarchy = PropertyHierarchy({i: filename.strip() for i, filename in enumerate(prop_files)})

    try:
        analyzer = MuleFlowAnalyzer(project_path, properties_hierarchy)

        if not properties_hierarchy:
            # Display discovered property files and prompt user for selection
            properties_hierarchy = analyzer.get_properties_hierarchy()
            if properties_hierarchy:
                print("Please Confirm Property File Hierarchy. (For Example, Prod First then Dev then Global):")
                for prop_file in properties_hierarchy:
                    print(f"{prop_file}: {properties_hierarchy[prop_file]}")
                                        
                selection = input("Enter the numbers of the property files to use (comma-separated, e.g., 1,5,3): ")
                selected_indices = [int(idx.strip()) for idx in selection.split(',')]
                
                properties_hierarchy = PropertyHierarchy({i: properties_hierarchy[idx] for i, idx in enumerate(selected_indices) if idx < len(properties_hierarchy)})
                
                # Re-initialize the analyzer with the selected properties
                analyzer = MuleFlowAnalyzer(project_path, properties_hierarchy)
            else:
                print("No property files discovered.")
        else:
            # Properties hierarchy was provided, but not implemented yet
            pass  # Not Implemented

        # Further analysis or operations can be added here
        analyzer.analyze_mule_flows()
        pass

    except Exception as e:
        print(f"Error: {str(e)}")
        return

if __name__ == "__main__":
    main()

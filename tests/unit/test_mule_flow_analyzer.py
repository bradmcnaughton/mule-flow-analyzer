import unittest
from pathlib import Path
import os
from src.mulesoft_flow_analyzer.analyzer.mule_flow_analyzer import MuleFlowAnalyzer, PropertyHierarchy
from src.mulesoft_flow_analyzer.config.constants import OutputFormat
from src.mulesoft_flow_analyzer.config.default_properties import DEFAULT_PROPERTIES

class TestMuleFlowAnalyzer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures that can be reused for all tests"""
        cls.test_project_path = Path('tests/mule/analyzer-tests')
        cls.test_property_files = PropertyHierarchy({0: 'properties/dummy.yaml'})

    def setUp(self):
        """Set up test fixtures before each test"""
        self.analyzer = MuleFlowAnalyzer()

    def test_initialization_with_no_parameters(self):
        """Test initialization with no parameters"""
        analyzer = MuleFlowAnalyzer()
        self.assertIsNone(analyzer.project_path)
        self.assertEqual(analyzer.project_files, {})
        self.assertEqual(analyzer.properties_hierarchy, PropertyHierarchy({}))
        self.assertEqual(analyzer.configuration_properties, DEFAULT_PROPERTIES)
        self.assertEqual(analyzer.output_format, OutputFormat.SEQUENCE)

    def test_initialization_with_project_path(self):
        """Test initialization with project path"""
        analyzer = MuleFlowAnalyzer(project_path=self.test_project_path)
        self.assertEqual(analyzer.project_path, self.test_project_path)
        self.assertGreater(len(analyzer.project_files), 0)  # Should have discovered some files
        self.assertGreater(len(analyzer.properties_hierarchy), 0)  # Should have discovered some property files

    def test_initialization_with_property_files(self):
        """Test initialization with project path and property files"""
        analyzer = MuleFlowAnalyzer(
            project_path=self.test_project_path,
            property_files=self.test_property_files
        )
        self.assertEqual(analyzer.properties_hierarchy, self.test_property_files)
        self.assertTrue(os.path.exists(self.test_project_path / 'src/main/resources' / self.test_property_files[0]))

    def test_initialization_with_user_config(self):
        """Test initialization with user configuration"""
        user_config = {
            'analyzer_properties': {
                'output_type': OutputFormat.TEXT
            }
        }
        analyzer = MuleFlowAnalyzer(user_config=user_config)
        self.assertEqual(analyzer.output_format, OutputFormat.TEXT)
        # Verify other default properties are preserved
        self.assertEqual(
            analyzer.configuration_properties['analyzer_properties']['plantuml'],
            DEFAULT_PROPERTIES['analyzer_properties']['plantuml']
        )

    def test_set_project_path(self):
        """Test setting project path after initialization"""
        self.analyzer.set_project_path(self.test_project_path)
        self.assertEqual(self.analyzer.project_path, self.test_project_path)
        self.assertGreater(len(self.analyzer.project_files), 0)
        self.assertGreater(len(self.analyzer.properties_hierarchy), 0)

    def test_set_project_path_invalid(self):
        """Test setting invalid project path"""
        with self.assertRaises(ValueError):
            self.analyzer.set_project_path("nonexistent/path")

    def test_set_properties_hierarchy(self):
        """Test setting properties hierarchy after initialization"""
        self.analyzer.set_project_path(self.test_project_path)
        self.analyzer.set_properties_hierarchy(self.test_property_files)
        self.assertEqual(self.analyzer.properties_hierarchy, self.test_property_files)

    def test_set_properties_hierarchy_without_project_path(self):
        """Test setting properties hierarchy without project path"""
        # Test that we can set the hierarchy without a project path
        self.analyzer.set_properties_hierarchy(self.test_property_files)
        self.assertEqual(self.analyzer.properties_hierarchy, self.test_property_files)
        self.assertIsNone(self.analyzer.discovered_properties)  # Should not process properties without project path

        # Now set the project path and verify properties are processed
        self.analyzer.set_project_path(self.test_project_path)
        self.assertIsNotNone(self.analyzer.discovered_properties)  # Properties should be processed now

    def test_property_resolution_order(self):
        """Test that properties are resolved in the correct order"""
        # Initialize with test project and property files
        analyzer = MuleFlowAnalyzer(
            project_path=self.test_project_path,
            property_files=self.test_property_files
        )
        # Force property discovery
        analyzer._discover_properties_keys()
        
        # Verify properties from dummy.yaml are loaded
        self.assertIn(str(self.test_project_path / 'src/main/resources/properties/dummy.yaml'), 
                     analyzer.discovered_properties)

    def test_configuration_merge(self):
        """Test that user configuration properly merges with defaults"""
        user_config = {
            'analyzer_properties': {
                'output_type': OutputFormat.TEXT,
                'plantuml': {
                    'format': 'svg'
                }
            }
        }
        analyzer = MuleFlowAnalyzer(user_config=user_config)
        
        # Check that user config overwrites defaults
        self.assertEqual(analyzer.configuration_properties['analyzer_properties']['output_type'], 
                        OutputFormat.TEXT)
        self.assertEqual(analyzer.configuration_properties['analyzer_properties']['plantuml']['format'], 
                        'svg')
        
        # Check that unspecified properties remain at default values
        self.assertEqual(analyzer.configuration_properties['analyzer_properties']['plantuml']['server'], 
                        DEFAULT_PROPERTIES['analyzer_properties']['plantuml']['server'])

if __name__ == '__main__':
    unittest.main()

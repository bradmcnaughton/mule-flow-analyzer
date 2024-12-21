import pytest
import os
import shutil
import tempfile
from unittest.mock import patch, MagicMock, call
import yaml
import logging
from main import main, load_user_config, parse_arguments
from src.exceptions import PropertyHierarchyError

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def valid_mule_project():
    """Return path to the valid Mule project in tests."""
    return os.path.join('tests', 'mule', 'analyzer-tests')

@pytest.fixture
def mock_analyzer():
    """Mock MuleFlowAnalyzer for testing."""
    with patch('main.MuleFlowAnalyzer') as mock:
        analyzer_instance = MagicMock()
        mock.return_value = analyzer_instance
        yield mock

@pytest.fixture
def mock_logging():
    """Mock logging configuration."""
    with patch('main.logging.basicConfig') as mock_log_config:
        with patch('main.os.makedirs') as mock_makedirs:
            with patch('main.logging.getLogger') as mock_logger:
                mock_logger_instance = MagicMock()
                mock_logger.return_value = mock_logger_instance
                yield mock_logger_instance

def test_valid_project_path(valid_mule_project, mock_analyzer, mock_logging):
    """Test analyzing a valid Mule project path."""
    # Mock the property hierarchy check to return False
    analyzer_instance = mock_analyzer.return_value
    analyzer_instance.get_properties_hierarchy.return_value = None
    
    with patch('main.os.path.exists', return_value=True):
        with patch('sys.argv', ['main.py', '-p', valid_mule_project, '-props', 'properties/dummy.yaml']):
            # Get the absolute path as main.py will do
            expected_path = os.path.join(os.getcwd(), valid_mule_project)
            expected_props = {0: 'properties/dummy.yaml'}
            
            assert main() == 0
            
            # Verify the analyzer was created with correct arguments
            mock_analyzer.assert_called_once_with(
                expected_path,
                expected_props,
                {'analyzer_properties': {'plantuml': {'format': 'png'}}}
            )
            # Verify analyze_mule_flows was called once with None
            analyzer_instance.analyze_mule_flows.assert_called_once_with(None)

def test_invalid_project_path(temp_dir):
    """Test analyzing an invalid project path."""
    invalid_path = os.path.join(temp_dir, 'nonexistent')
    with patch('sys.argv', ['main.py', '-p', invalid_path, '-props', 'properties/dummy.yaml']):
        assert main() == 1

def test_valid_flow_name(valid_mule_project, mock_analyzer):
    """Test analyzing a specific flow by name."""
    with patch('sys.argv', ['main.py', '-p', valid_mule_project, '-f', 'batch-job-flow', '-props', 'properties/dummy.yaml']):
        assert main() == 0
        mock_analyzer.return_value.analyze_mule_flows.assert_called_once_with('batch-job-flow')

def test_valid_config_file(temp_dir):
    """Test loading a valid config file."""
    config_file = os.path.join(temp_dir, 'config.yaml')
    config_data = {
        'analyzer_properties': {
            'plantuml': {
                'server': 'http://test-server:8080',
                'format': 'png',
                'output_directory': './test-output'
            }
        }
    }
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f)
    
    loaded_config = load_user_config(config_file)
    assert loaded_config == config_data

def test_invalid_config_file(temp_dir):
    """Test loading an invalid config file."""
    config_file = os.path.join(temp_dir, 'invalid_config.yaml')
    with open(config_file, 'w') as f:
        f.write('invalid: yaml: content:')
    
    with pytest.raises(yaml.YAMLError):
        load_user_config(config_file)

def test_nonexistent_config_file(temp_dir):
    """Test loading a nonexistent config file."""
    config_file = os.path.join(temp_dir, 'nonexistent.yaml')
    with pytest.raises(FileNotFoundError):
        load_user_config(config_file)

def test_custom_output_path(valid_mule_project, mock_analyzer, temp_dir):
    """Test specifying a custom output path."""
    output_path = os.path.join(temp_dir, 'diagrams')
    with patch('sys.argv', ['main.py', '-p', valid_mule_project, '-o', output_path, '-props', 'properties/dummy.yaml']):
        assert main() == 0
        mock_analyzer.assert_called_once()
        # Verify the output path was passed in the config
        config = mock_analyzer.call_args[0][2]
        assert config['analyzer_properties']['plantuml']['output_directory'] == output_path

def test_custom_plantuml_server(valid_mule_project, mock_analyzer):
    """Test specifying a custom PlantUML server."""
    server_url = 'http://custom-server:8080'
    with patch('sys.argv', ['main.py', '-p', valid_mule_project, '-s', server_url, '-props', 'properties/dummy.yaml']):
        assert main() == 0
        mock_analyzer.assert_called_once()
        # Verify the server URL was passed in the config
        config = mock_analyzer.call_args[0][2]
        assert config['analyzer_properties']['plantuml']['server'] == server_url

def test_properties_hierarchy(valid_mule_project, mock_analyzer):
    """Test specifying a properties hierarchy."""
    props = 'dev.properties,prod.properties'
    with patch('sys.argv', ['main.py', '-p', valid_mule_project, '-props', props]):
        assert main() == 0
        mock_analyzer.assert_called_once()
        # Verify properties hierarchy was passed
        assert mock_analyzer.call_args[0][1] is not None

def test_parse_arguments_defaults():
    """Test default values for command line arguments."""
    with patch('sys.argv', ['main.py']):
        args = parse_arguments()
        assert args.project_path == os.getcwd()  # Default project path
        assert args.flow_name is None
        assert args.config_path is None
        assert args.output_path is None
        assert args.plantuml_server is None
        assert args.plant_format == 'png'

def test_invalid_mule_project_structure(temp_dir):
    """Test analyzing a directory that's not a valid Mule project."""
    # Create a directory without proper Mule project structure
    os.makedirs(os.path.join(temp_dir, 'src', 'main'), exist_ok=True)
    with patch('sys.argv', ['main.py', '-p', temp_dir, '-props', 'properties/dummy.yaml']):
        assert main() == 1

def test_version_argument():
    """Test version argument parsing."""
    with pytest.raises(SystemExit) as exc_info:
        with patch('sys.argv', ['main.py', '-v']):
            parse_arguments()
    assert exc_info.value.code == 0

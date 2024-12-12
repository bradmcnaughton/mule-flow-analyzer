import unittest
from pathlib import Path
import os
import shutil
from src.sequence_diagram_generator import SequenceDiagramGenerator, ConfigurationError
from src.mule_flow_analyzer import MuleFlowAnalyzer
from default_properties import DEFAULT_PROPERTIES

class TestSequenceDiagramGenerator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures that can be reused for all tests"""
        cls.test_files_dir = Path('tests/mule/analyzer-tests/src/main/mule')
        cls.output_dir = Path('tests/output/plantuml')
        cls.log_dir = Path('tests/output/logs')
        
        # Overwrite Defautl Properties with some testing specific properties
        test_properties = DEFAULT_PROPERTIES
        test_properties['analyzer_properties']['plantuml']['output_directory'] = cls.output_dir
        test_properties['analyzer_properties']['logging']['file'] = cls.log_dir / 'test_mule_flow_analyzer.log'

        cls.analyzer_properties = test_properties


        
    def setUp(self):
        """Set up test fixtures before each test"""
        # Initialize analyzer with properties file
        self.analyzer = MuleFlowAnalyzer(
            project_path=self.test_files_dir.parent.parent.parent,  # Root of test project
            property_files=None,
            user_config=None
        )
        
        # Initialize generator with test settings
        self.generator = SequenceDiagramGenerator(
            configuration_properties=self.analyzer_properties
        )
        
        # Create clean output directory
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)
        os.makedirs(self.output_dir)

    def tearDown(self):
        """Clean up after each test"""
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)

    def test_initialization_with_empty_config(self):
        """Test that initializing with empty config raises ConfigurationError"""
        with self.assertRaises(ConfigurationError):
            SequenceDiagramGenerator(configuration_properties={})

    def test_initialization_with_missing_keys(self):
        """Test that initializing with missing required keys raises ConfigurationError"""
        incomplete_config = {
            'diagram_formatting_properties': {}
            # Missing 'analyzer_properties'
        }
        with self.assertRaises(ConfigurationError):
            SequenceDiagramGenerator(configuration_properties=incomplete_config)

    def test_remove_expression_brackets(self):
        """Test removal of Dataweave expression brackets"""
        test_cases = [
            ('#[payload]', 'payload'),
            ('regular string', 'regular string'),
            ('#[vars.someVar]', 'vars.someVar'),
            ('', ''),
            ('#[]', ''),
            ('#[test', '#[test'),
            ('test]', 'test]')
        ]
        
        for input_str, expected in test_cases:
            with self.subTest(input_str=input_str):
                result = self.generator.remove_expression_brackets(input_str)
                self.assertEqual(result, expected)

    def test_clean_uml_note(self):
        """Test cleaning of UML notes"""
        test_cases = [
            ('Simple note', 'Simple note'),
            ('Note with "quotes"', 'Note with \\"quotes\\"'),
            ('Multi\nline\nnote', 'Multi\\nline\\nnote'),
            ('Note with "quotes" and\nline breaks', 'Note with \\"quotes\\" and\\nline breaks')
        ]
        
        for input_str, expected in test_cases:
            with self.subTest(input_str=input_str):
                result = self.generator.clean_uml_note(input_str)
                self.assertEqual(result, expected)

    def test_clean_uml_syntax(self):
        """Test cleaning of UML syntax"""
        test_cases = [
            ('Simple text', '"Simple text"'),
            ('Text with [bracket]', '"Text with\\n[bracket]"'),
            ('', ''),
            ('Text with "quotes"', '"Text with quotes"'),
            ('Multiple [brackets] in [text]', '"Multiple\\n[brackets] in\\n[text]"')
        ]
        
        for input_str, expected in test_cases:
            with self.subTest(input_str=input_str):
                result = self.generator.clean_uml_syntax(input_str)
                self.assertEqual(result, expected)

    def test_clean_uml_alias(self):
        """Test cleaning of UML aliases"""
        test_cases = [
            ('simple:alias', 'simplealias'),
            ('complex-alias-with-hyphens', 'complexaliaswithhyphens'),
            ('alias with spaces', 'aliaswithspaces'),
            ('alias:with:colons', 'aliaswithcolons'),
            ('alias"with"quotes', 'aliaswithquotes'),
            ('', '')
        ]
        
        for input_str, expected in test_cases:
            with self.subTest(input_str=input_str):
                result = self.generator.clean_uml_alias(input_str)
                self.assertEqual(result, expected)

    def test_clean_config_ref(self):
        """Test cleaning of config references"""
        test_cases = [
            ('CONFIG_TEST_DB', 'TEST'),
            ('HTTP_API_CONFIGURATION', 'API'),
            ('SALESFORCE_SYSTEM_A', 'SYSTEM A'),
            ('DATABASE_CUSTOMER_DB', 'CUSTOMER'),
            ('simple_name', 'simple name'),
            ('', '')
        ]
        
        for input_str, expected in test_cases:
            with self.subTest(input_str=input_str):
                result = self.generator.clean_config_ref(input_str)
                self.assertEqual(result, expected)

    def test_add_arrow_to_legend(self):
        """Test adding arrows to the legend"""
        # Test adding a high priority arrow
        self.generator.add_arrow_to_legend('->', 'Flow')
        self.assertEqual(self.generator.arrow_legend['->'].priority, 0)
        self.assertEqual(self.generator.arrow_legend['->'].label, 'Flow')

        # Test adding a normal priority arrow
        self.generator.add_arrow_to_legend('-->', 'Regular')
        self.assertEqual(self.generator.arrow_legend['-->'].priority, 2)
        self.assertEqual(self.generator.arrow_legend['-->'].label, 'Regular')

        # Test adding duplicate arrow (should not change priority)
        self.generator.add_arrow_to_legend('->', 'Flow Again')
        self.assertEqual(len(self.generator.arrow_legend), 2)
        self.assertEqual(self.generator.arrow_legend['->'].priority, 0)

    def _common_analyze_flow_and_get_content(self, flow_name: str, flow_source_file: str) -> list[str]:
        """Helper method to analyze a flow and get its UML content.
        
        Args:
            flow_name: Name of the flow to analyze
            flow_source_file: Path to the source file containing the flow
            
        Returns:
            - List of UML content lines
        """
        # Get the flow from the source files
        self.analyzer.analyze_mule_flows(flow_name=flow_name)

        # Generate the sequence diagram syntax for the flow from the source files
        self.analyzer.generate_sequence_diagram(flow_source_file)

        # Get output file path and verify it exists
        output_file_path = self.output_dir / (self.generator.clean_flow_name(flow_name) + ".txt")
        self.assertTrue(os.path.exists(output_file_path))

        # Read the content of the generated UML file
        with open(output_file_path, 'r') as file:
            uml_file_content = file.read()

        uml_content = uml_file_content.splitlines()

        # Assert that the title is present
        self.assertIn(f'title {flow_name}', uml_content)

        return uml_content

    def test_analyzer_nested_flows(self):
        """Test analyzer nested flows"""
        flow_name = "analyzer-test-nested-flowrefs"
        flow_source_file = "src\\main\\mule\\analyzer-tests-nested-subflows.xml"

        uml_content = self._common_analyze_flow_and_get_content(flow_name, flow_source_file)

        # Find indices of box start and end
        # TODO: Move to a general formatting test case
        box_start_idx = uml_content.index('box #LightBlue-6FBBD3')
        box_end_idx = uml_content.index('end box')
        
        # Check all Mule component participant lines are between box start and end
        for participant_idx in ['participant "http:basic-security-filter\\n[Basic security filter]"', 'participant "tracing:set-logging-variable\\n[loggingVar]"', 'participant "ee:transform\\n[Set Variable: myMainVar1]"']:
            self.assertTrue(box_start_idx < uml_content.index(participant_idx) < box_end_idx,
                          f"Participant at line {participant_idx} should be between box lines {box_start_idx} and {box_end_idx}")

        # Assert that the HTTP and LocalFileServer actors are present
        self.assertIn(f'participant "<size:30>{self.analyzer_properties['diagram_formatting_properties']['actors']['http']}\\nHTTP" as HTTP', uml_content)
        self.assertIn(f'participant "<size:30>{self.analyzer_properties['diagram_formatting_properties']['actors']['file']}\\nLocalFileServer SFTP" as LocalFileServer', uml_content)       

        # Assert that the arrows are present
        self.assertIn(' -> "http:basic-security-filter\\n[Basic security filter]" : ', uml_content)
        self.assertIn('"http:basic-security-filter\\n[Basic security filter]" -> "HTTP" : HTTP Request (Basic security filter)', uml_content)
        self.assertIn('"HTTP" --> "http:basic-security-filter\\n[Basic security filter]" : ', uml_content)
        self.assertIn('"ee:transform\\n[Set Variable: myMainVar1]" -> "ee:transform\\n[Set Variable: myMainVar1]" : message.set attributes', uml_content)
        
        # Assert that the subflows have a group
        self.assertIn('group sub-flow set-mySubflowVar-subflow', uml_content)
        self.assertIn('group sub-flow set-mySubflowVar2-subflow', uml_content)
        self.assertIn('group sub-flow read-file-subflow', uml_content)

        # Assert that there are 3 'end' statements
        self.assertEqual(uml_content.count('end'), 3)

    def test_analyzer_anypoint_mq_queues(self):
        """Test analyzer anypoint mq queues"""
        flow_name = "anypoint-mq-queues"
        flow_source_file = "src\\main\\mule\\jms-transaction.xml"

        uml_content = self._common_analyze_flow_and_get_content(flow_name, flow_source_file)

        # Assert that the queues are present
        self.assertIn('queue "Queue\\nmy-test-subscription"', uml_content)
        self.assertIn('queue "Queue\\nmy-test-queue"', uml_content)
        self.assertIn('queue "Queue\\nmy-destination"', uml_content)

        # Assert that the anypoint-mq:subscriber component is present
        self.assertIn('participant "anypoint-mq:subscriber\\n[Subscriber]"', uml_content)

        # Assert that the arrows are present
        self.assertIn('"Queue\\nmy-test-subscription" -> "anypoint-mq:subscriber\\n[Subscriber]" : Message (my-test-subscription)', uml_content)
        self.assertIn('"anypoint-mq:subscriber\\n[Subscriber]" -> "anypoint-mq:consume\\n[Consume]" : ', uml_content)
        self.assertIn('"anypoint-mq:consume\\n[Consume]" -> "Queue\\nmy-test-queue" : Message (my-test-queue)', uml_content)
        self.assertIn('"Queue\\nmy-test-queue" --> "anypoint-mq:consume\\n[Consume]" : ', uml_content)
        self.assertIn('"anypoint-mq:consume\\n[Consume]" -> "anypoint-mq:publish\\n[Publish]" : ', uml_content)
        self.assertIn('"anypoint-mq:publish\\n[Publish]" -> "Queue\\nmy-destination" : Message (my-destination)', uml_content)
        self.assertIn('"Queue\\nmy-destination" --> "anypoint-mq:publish\\n[Publish]" : ', uml_content)

    def test_analyzer_ibm_mq_queues(self):
        """Test analyzer IBM MQ queues"""
        flow_name = "ibm-mq-queues"
        flow_source_file = "src\\main\\mule\\jms-transaction.xml"

        uml_content = self._common_analyze_flow_and_get_content(flow_name, flow_source_file)

        # Assert that the queue is present
        self.assertIn('queue "Queue\\nmy-ibm-queue"', uml_content)
        self.assertIn('queue "Queue\\nibm-destination-2"', uml_content)

        # Assert that the IBM MQ components are present
        self.assertIn('participant "ibm-mq:listener\\n[On New Message]"', uml_content)
        self.assertIn('participant "ibm-mq:ack\\n[Ack]"', uml_content)
        self.assertIn('participant "ibm-mq:publish-consume\\n[Publish consume]"', uml_content)

        # Assert that the arrows are present
        self.assertIn('"Queue\\nmy-ibm-queue" -> "ibm-mq:listener\\n[On New Message]" : Message (my-ibm-queue)', uml_content)
        self.assertIn('"ibm-mq:listener\\n[On New Message]" -> "ibm-mq:ack\\n[Ack]" : ', uml_content)
        self.assertIn('"ibm-mq:ack\\n[Ack]" -> "ibm-mq:publish-consume\\n[Publish consume]" : ', uml_content)
        self.assertIn('"ibm-mq:publish-consume\\n[Publish consume]" -> "Queue\\nibm-destination-2" : Message (ibm-destination-2)', uml_content)
        self.assertIn('"Queue\\nibm-destination-2" --> "ibm-mq:publish-consume\\n[Publish consume]" : ', uml_content)

    def test_analyzer_vm_queues(self):
        """Test analyzer VM queues"""
        flow_name = "vm-queues-queues"
        flow_source_file = "src\\main\\mule\\jms-transaction.xml"

        uml_content = self._common_analyze_flow_and_get_content(flow_name, flow_source_file)

        # Assert that the queues are present
        self.assertIn('queue "Queue\\nmy-vm-queue"', uml_content)
        self.assertIn('queue "Queue\\nsome-vm-queue"', uml_content)
        self.assertIn('queue "Queue\\nsome-vm-queue2"', uml_content)

        # Assert that the VM components are present
        self.assertIn('participant "vm:listener\\n[Listener]"', uml_content)
        self.assertIn('participant "vm:publish-consume\\n[Publish consume]"', uml_content)
        self.assertIn('participant "vm:consume\\n[Consume]"', uml_content)
        self.assertIn('participant "vm:publish\\n[Publish]"', uml_content)

        # Assert that the arrows are present
        self.assertIn('"Queue\\nmy-vm-queue" -> "vm:listener\\n[Listener]" : Message (my-vm-queue)', uml_content)
        self.assertIn('"vm:listener\\n[Listener]" -> "vm:publish-consume\\n[Publish consume]" : ', uml_content)
        self.assertIn('"vm:publish-consume\\n[Publish consume]" -> "Queue\\nsome-vm-queue" : Message (some-vm-queue)', uml_content)
        self.assertIn('"Queue\\nsome-vm-queue" --> "vm:publish-consume\\n[Publish consume]" : ', uml_content)
        self.assertIn('"vm:publish-consume\\n[Publish consume]" -> "vm:consume\\n[Consume]" : ', uml_content)
        self.assertIn('"vm:consume\\n[Consume]" -> "Queue\\nsome-vm-queue2" : Message (some-vm-queue2)', uml_content)
        self.assertIn('"Queue\\nsome-vm-queue2" --> "vm:consume\\n[Consume]" : ', uml_content)
        self.assertIn('"vm:consume\\n[Consume]" -> "vm:publish\\n[Publish]" : ', uml_content)
        self.assertIn('"vm:publish\\n[Publish]" -> "Queue\\nsome-vm-queue" : Message (some-vm-queue2)', uml_content)
        self.assertIn('"Queue\\nsome-vm-queue" --> "vm:publish\\n[Publish]" : ', uml_content)

    def test_analyzer_jms_transaction_flow(self):
        """Test analyzer JMS transaction flow"""
        flow_name = "jms-transactionFlow"
        flow_source_file = "src\\main\\mule\\jms-transaction.xml"

        uml_content = self._common_analyze_flow_and_get_content(flow_name, flow_source_file)

        # Assert that the queue is present
        self.assertIn('queue "Queue\\nmy-queue-name"', uml_content)

        # Assert that the databases are present
        self.assertIn('database "Database\\nA"', uml_content)
        self.assertIn('database "Database\\nB"', uml_content)

        # Assert that the components are present
        self.assertIn('participant "jms:listener\\n[my-queue-name]"', uml_content)
        self.assertIn('participant "ee:transform\\n[Set Var 1]"', uml_content)
        self.assertIn('participant "db:insert\\n[Insert var1 into db1]"', uml_content)
        self.assertIn('participant "ee:transform\\n[Set Var 2]"', uml_content)
        self.assertIn('participant "db:insert\\n[Insert var2 into db2]"', uml_content)
        self.assertIn('participant "logger\\n[All Done]"', uml_content)

        # Assert transaction notes are present
        self.assertIn('note right of "jms:listener\\n[my-queue-name]" #pink : XA Transaction Starting', uml_content)
        self.assertIn('note right of "logger\\n[All Done]"  #pink: XA Transaction End', uml_content)

        # Assert that the arrows and messages are present
        self.assertIn('"Queue\\nmy-queue-name" -> "jms:listener\\n[my-queue-name]" : Message (my-queue-name)', uml_content)
        self.assertIn('"ee:transform\\n[Set Var 1]" -[#pink]> "ee:transform\\n[Set Var 1]" : message.set payload', uml_content)
        self.assertIn('"ee:transform\\n[Set Var 1]" -[#pink]> "ee:transform\\n[Set Var 1]" : variables.variableName: var1', uml_content)
        self.assertIn('"db:insert\\n[Insert var1 into db1]" -[#pink]> "Database\\nA" : Database Change: (Insert)', uml_content)
        self.assertIn('"Database\\nA" -[#pink]-> "db:insert\\n[Insert var1 into db1]" : ', uml_content)
        self.assertIn('"ee:transform\\n[Set Var 2]" -[#pink]> "ee:transform\\n[Set Var 2]" : variables.variableName: var2', uml_content)
        self.assertIn('"db:insert\\n[Insert var2 into db2]" -[#pink]> "Database\\nB" : Database Change: (Insert)', uml_content)
        self.assertIn('"Database\\nB" -[#pink]-> "db:insert\\n[Insert var2 into db2]" : ', uml_content)

        # Assert SQL-related messages
        self.assertIn('"db:insert\\n[Insert var1 into db1]" -[#pink]> "db:insert\\n[Insert var1 into db1]" : insert.sql', uml_content)
        self.assertIn('"db:insert\\n[Insert var2 into db2]" -[#pink]> "db:insert\\n[Insert var2 into db2]" : insert.sql', uml_content)
        self.assertIn('"db:insert\\n[Insert var2 into db2]" -[#pink]> "db:insert\\n[Insert var2 into db2]" : insert.input parameters', uml_content)

if __name__ == '__main__':
    unittest.main()


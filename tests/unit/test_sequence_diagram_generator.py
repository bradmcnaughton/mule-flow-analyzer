import unittest
from pathlib import Path
import os
import shutil
import random
import copy
import yaml
from unittest.mock import patch, MagicMock
from mule_flow_analyzer.analyzer.sequence_diagram_generator import SequenceDiagramGenerator, ConfigurationError
from mule_flow_analyzer.analyzer.mermaid_sequence_diagram_generator import MermaidSequenceDiagramGenerator
from mule_flow_analyzer.analyzer.mule_flow_analyzer import MuleFlowAnalyzer
from mule_flow_analyzer.analyzer.mule_flow_element import MuleFlowElement
from mule_flow_analyzer.config.default_properties import DEFAULT_PROPERTIES
from io import StringIO
import sys
from mule_flow_analyzer.config.constants import OutputFormat

class TestSequenceDiagramGenerator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures that can be reused for all tests"""
        cls.test_files_dir = Path('tests/mule/analyzer-tests/src/main/mule')
        cls.output_dir = Path('tests/output/plantuml')
        cls.log_dir = Path('tests/output/logs')
        
        # Isolated copy so tests do not mutate the module-level DEFAULT_PROPERTIES
        test_properties = copy.deepcopy(DEFAULT_PROPERTIES)
        test_properties['analyzer_properties']['plantuml']['output_directory'] = cls.output_dir
        test_properties['analyzer_properties']['logging']['file'] = cls.log_dir / 'test_mule_flow_analyzer.log'

        # Randomize the colors for testing
        test_properties['diagram_formatting_properties']['mule']['box-color'] = ''.join(random.choices('0123456789ABCDEF', k=6))
        test_properties['diagram_formatting_properties']['transactions']['arrows'][1] = ''.join(random.choices('0123456789ABCDEF', k=6))
        test_properties['diagram_formatting_properties']['transactions']['arrows'][2] = ''.join(random.choices('0123456789ABCDEF', k=6))
        test_properties['diagram_formatting_properties']['transactions']['arrows'][3] = ''.join(random.choices('0123456789ABCDEF', k=6))
        test_properties['diagram_formatting_properties']['errors']['color'] = ''.join(random.choices('0123456789ABCDEF', k=6))
        test_properties['diagram_formatting_properties']['try']['label-color'] = ''.join(random.choices('0123456789ABCDEF', k=6))
        test_properties['diagram_formatting_properties']['try']['background-color'] = ''.join(random.choices('0123456789ABCDEF', k=6))
        test_properties['diagram_formatting_properties']['async']['background-color'] = ''.join(random.choices('0123456789ABCDEF', k=6))
        test_properties['diagram_formatting_properties']['batch']['step']['background-color'] = ''.join(random.choices('0123456789ABCDEF', k=6))
        test_properties['diagram_formatting_properties']['batch']['on-complete']['background-color'] = ''.join(random.choices('0123456789ABCDEF', k=6))
        test_properties['diagram_formatting_properties']['batch']['process-records']['background-color'] = ''.join(random.choices('0123456789ABCDEF', k=6))
        test_properties['diagram_formatting_properties']['batch']['aggregator']['background-color'] = ''.join(random.choices('0123456789ABCDEF', k=6))
        test_properties['diagram_formatting_properties']['batch']['job']['background-color'] = ''.join(random.choices('0123456789ABCDEF', k=6))
        
        # Set the properties for the analyzer
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

        # Set up the render_file mock
        self.render_patcher = patch('plantweb.render.render_file')
        self.mock_render_file = self.render_patcher.start()
        self.mock_render_file.return_value = str(self.output_dir / "test_output.png")

    def tearDown(self):
        """Clean up after each test"""
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)
        self.render_patcher.stop()

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
        # Keep analyzer in sync with class-level analyzer_properties (e.g. verbose.logging toggles)
        self.analyzer.set_configuration_properties(self.analyzer_properties)

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

        self.analyzer_properties['diagram_formatting_properties']['verbose']['logging'] = True

        uml_content = self._common_analyze_flow_and_get_content(flow_name, flow_source_file)

        # Find indices of box start and end
        # TODO: Move to a general formatting test case
        box_start_idx = uml_content.index(f'box #{self.analyzer_properties["diagram_formatting_properties"]["mule"]["box-color"]}')
        box_end_idx = uml_content.index('end box')
        
        # Check all Mule component participant lines are between box start and end
        for participant_idx in ['participant "http:basic-security-filter\\n[Basic security filter]"', 'participant "tracing:set-logging-variable\\n[loggingVar]"', 'participant "ee:transform\\n[Set Variable: myMainVar1]"']:
            self.assertTrue(box_start_idx < uml_content.index(participant_idx) < box_end_idx,
                          f"Participant at line {participant_idx} should be between box lines {box_start_idx} and {box_end_idx}")

        # Assert that the HTTP and LocalFileServer actors are present
        self.assertIn(f'participant "<size:30>{self.analyzer_properties["diagram_formatting_properties"]["actors"]["http"]}\\nHTTP" as HTTP', uml_content)
        self.assertIn(f'participant "<size:30>{self.analyzer_properties["diagram_formatting_properties"]["actors"]["file"]}\\nLocalFileServer SFTP" as LocalFileServer', uml_content)       

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

    def test_analyzer_batch_job_flow(self):
        """Test analyzer batch job flow"""
        flow_name = "batch-job-flow"
        flow_source_file = "src\\main\\mule\\batch-job-flow.xml"

        uml_content = self._common_analyze_flow_and_get_content(flow_name, flow_source_file)

        # Assert that the main components are present
        self.assertIn('participant "sftp:listener\\n[On New or Updated Ships Log File]"', uml_content)
        self.assertIn('participant "tracking:transaction\\n[Set Transaction Id]"', uml_content)
        self.assertIn('participant "ee:transform\\n[Transform to Pirate Data Model]"', uml_content)
        self.assertIn('participant "db:insert\\n[Insert Shanty]"', uml_content)
        self.assertIn('participant "ibm-mq:publish\\n[Walk Plank]"', uml_content)
        self.assertIn('participant "workday:student-transfer-credit\\n[Pay Shanty Writers]"', uml_content)

        # Assert batch job structure
        self.assertIn(f'group #{self.analyzer_properties["diagram_formatting_properties"]["batch"]["process-records"]["background-color"]} Batch Process Records', uml_content)
        self.assertIn(f'group #{self.analyzer_properties["diagram_formatting_properties"]["batch"]["step"]["background-color"]} Batch Step DetectTales, Accept Policy: ALL', uml_content)
        self.assertIn(f'group #{self.analyzer_properties["diagram_formatting_properties"]["batch"]["step"]["background-color"]} Batch Step RecordShanties, Accept Policy: NO_FAILURES', uml_content)
        self.assertIn(f'group #{self.analyzer_properties["diagram_formatting_properties"]["batch"]["step"]["background-color"]} Batch Step WalkPlanks, Accept Policy: ONLY_FAILURES', uml_content)
        self.assertIn(f'group #{self.analyzer_properties["diagram_formatting_properties"]["batch"]["on-complete"]["background-color"]} Batch On Complete', uml_content)

        # Assert key interactions and messages
        self.assertIn('"LocalFileServer" -> "sftp:listener\\n[On New or Updated Ships Log File]" : File Transfer: (Listener)', uml_content)
        self.assertIn('"db:insert\\n[Insert Shanty]" -> "Database\\nA" : Database Change: (Insert)', uml_content)
        self.assertIn('"ibm-mq:publish\\n[Walk Plank]" -> "Queue\\nshanty-errors" : Message (shanty-errors)', uml_content)
        self.assertIn('"workday:student-transfer-credit\\n[Pay Shanty Writers]" -> "Workday" : student-transfer-credit', uml_content)

        # Assert error handling
        self.assertIn(f'alt#{self.analyzer_properties["diagram_formatting_properties"]["try"]["label-color"]} #{self.analyzer_properties["diagram_formatting_properties"]["try"]["background-color"]} Try', uml_content)
        self.assertIn(f'note over "workday:student-transfer-credit\\n[Pay Shanty Writers]" #{self.analyzer_properties["diagram_formatting_properties"]["errors"]["color"]}: Inline Error Handler', uml_content)

        # Assert subflow
        self.assertIn('group sub-flow multi-purpose-subflow', uml_content)

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

        # Assert transaction notes are present
        transaction_color = self.analyzer_properties["diagram_formatting_properties"]["transactions"]["arrows"][1]  # Using first transaction color
        self.assertIn(f'note right of "jms:listener\\n[my-queue-name]" #{transaction_color} : XA Transaction Starting', uml_content)

        # Assert that the arrows and messages are present
        self.assertIn('"Queue\\nmy-queue-name" -> "jms:listener\\n[my-queue-name]" : Message (my-queue-name)', uml_content)
        self.assertIn(f'"ee:transform\\n[Set Var 1]" -[#{transaction_color}]> "ee:transform\\n[Set Var 1]" : message.set payload', uml_content)
        self.assertIn(f'"ee:transform\\n[Set Var 1]" -[#{transaction_color}]> "ee:transform\\n[Set Var 1]" : variables.variableName: var1', uml_content)
        self.assertIn(f'"db:insert\\n[Insert var1 into db1]" -[#{transaction_color}]> "Database\\nA" : Database Change: (Insert)', uml_content)
        self.assertIn(f'"Database\\nA" -[#{transaction_color}]-> "db:insert\\n[Insert var1 into db1]" : ', uml_content)
        self.assertIn(f'"ee:transform\\n[Set Var 2]" -[#{transaction_color}]> "ee:transform\\n[Set Var 2]" : variables.variableName: var2', uml_content)
        self.assertIn(f'"db:insert\\n[Insert var2 into db2]" -[#{transaction_color}]> "Database\\nB" : Database Change: (Insert)', uml_content)
        self.assertIn(f'"Database\\nB" -[#{transaction_color}]-> "db:insert\\n[Insert var2 into db2]" : ', uml_content)

        # Assert SQL-related messages
        self.assertIn(f'"db:insert\\n[Insert var1 into db1]" -[#{transaction_color}]> "db:insert\\n[Insert var1 into db1]" : insert.sql', uml_content)
        self.assertIn(f'"db:insert\\n[Insert var2 into db2]" -[#{transaction_color}]> "db:insert\\n[Insert var2 into db2]" : insert.sql', uml_content)
        self.assertIn(f'"db:insert\\n[Insert var2 into db2]" -[#{transaction_color}]> "db:insert\\n[Insert var2 into db2]" : insert.input parameters', uml_content)

    def test_analyzer_control_flows_single_choice(self):
        """Test analyzer control flows with single choice"""
        flow_name = "control-flows-single-choice"
        flow_source_file = "src\\main\\mule\\control-flows.xml"

        uml_content = self._common_analyze_flow_and_get_content(flow_name, flow_source_file)

        # Assert that the main components are present
        self.assertIn('participant "http:listener\\n[Ice Cube Listener]"', uml_content)
        self.assertIn('participant "set-variable\\n[goodDay]"', uml_content)
        self.assertIn('participant "ee:transform\\n[Set Payload]"', uml_content)
        self.assertIn('participant "http:request\\n[Stereo API]"', uml_content)
        self.assertIn('participant "ee:transform\\n[Set Payload (Maybe Baby)]"', uml_content)
        self.assertIn('participant "http:request\\n[Fridge API]"', uml_content)
        self.assertIn('participant "ee:transform\\n[Transform Message]"', uml_content)
        self.assertIn('participant "raise-error\\n[Raise Time is a Flat Circle]"', uml_content)
        
        # Assert HTTP actors
        self.assertIn('participant "<size:30><&globe>\\nHTTP" as HTTP', uml_content)
        self.assertIn('participant "<size:30><&globe>\\nstereo" as HTTP_1', uml_content)
        self.assertIn('participant "<size:30><&globe>\\nfridge" as HTTP_2', uml_content)
        
        # Assert initial HTTP request
        self.assertIn('"HTTP" -> "http:listener\\n[Ice Cube Listener]" : HTTP Request: (/api)', uml_content)
        
        # Assert choice structure and flow
        self.assertIn('"http:listener\\n[Ice Cube Listener]" -> "set-variable\\n[goodDay]" : ', uml_content)
        self.assertIn('alt vars.goodDay == \'YES\'', uml_content)
        self.assertIn('"http:request\\n[Stereo API]" -> "HTTP_1" : HTTP Request: (GET /tunes)', uml_content)
        self.assertIn('else vars.goodDay == \'NO\'', uml_content)
        self.assertIn('"http:request\\n[Stereo API]" -> "HTTP_1" : HTTP Request: (DELETE /tunes)', uml_content)
        self.assertIn('else vars.goodDay == \'MAYBE\'', uml_content)
        self.assertIn('"http:request\\n[Fridge API]" -> "HTTP_2" : HTTP Request: (PATCH /pizza)', uml_content)
        self.assertIn('else else', uml_content)
        
        # Assert error handling
        self.assertIn(f'note over "raise-error\\n[Raise Time is a Flat Circle]" #{self.analyzer_properties["diagram_formatting_properties"]["errors"]["color"]}: Raising Error:\\nANY\\n\\nError Handler:\\nInline Error Handler', uml_content)
        self.assertIn('end', uml_content)

    def test_analyzer_control_flows_loops(self):
        """Test analyzer control flows with loops"""
        flow_name = "control-flows-loops"
        flow_source_file = "src\\main\\mule\\control-flows.xml"

        uml_content = self._common_analyze_flow_and_get_content(flow_name, flow_source_file)

        # Assert that the main components are present
        self.assertIn('participant "http:listener\\n[Listener]"', uml_content)
        self.assertIn('participant "validation:validate-size\\n[Validate Payload Size]"', uml_content)
        self.assertIn('participant "file:write\\n[Write Payload to File]"', uml_content)
        self.assertIn('participant "jms:publish\\n[Publish Name to Names Queue]"', uml_content)

        # Assert external systems
        self.assertIn('participant "<size:30><&globe>\\nHTTP" as HTTP', uml_content)
        self.assertIn('participant "<size:30><&file>\\nfile" as file', uml_content)
        self.assertIn('queue "Queue\\nnames"', uml_content)

        # Assert initial HTTP request
        self.assertIn('"HTTP" -> "http:listener\\n[Listener]" : HTTP Request: (/loops)', uml_content)

        # Assert foreach loops
        self.assertIn('loop For Each Payload Item\\nCollection: payload', uml_content)
        self.assertIn('loop For Each Name in Payload Names\\nCollection: payload.names', uml_content)

        # Assert file operations
        self.assertIn('"file:write\\n[Write Payload to File]" -> "file" : File Transfer: (Write)', uml_content)
        self.assertIn('"file" --> "file:write\\n[Write Payload to File]" : ', uml_content)

        # Assert queue operations
        self.assertIn('"jms:publish\\n[Publish Name to Names Queue]" -> "Queue\\nnames" : Message (names)', uml_content)
        self.assertIn('"Queue\\nnames" --> "jms:publish\\n[Publish Name to Names Queue]" : ', uml_content)

    def test_analyzer_control_flows_until_successful(self):
        """Test analyzer control flows with until successful"""
        flow_name = "control-flows-until-successful"
        flow_source_file = "src\\main\\mule\\control-flows.xml"

        uml_content = self._common_analyze_flow_and_get_content(flow_name, flow_source_file)

        # Assert that the main components are present
        self.assertIn('participant "sftp:listener\\n[New Cattle Transcript Uploaded]"', uml_content)
        self.assertIn('participant "ee:transform\\n[Create requestBody]"', uml_content)
        self.assertIn('participant "http:request\\n[GET Cow Tunes]"', uml_content)
        self.assertIn('participant "ee:transform\\n[Create Mixtape]"', uml_content)
        self.assertIn('participant "anypoint-mq:publish\\n[Publish Tracklist to Queue]"', uml_content)

        # Assert external systems
        self.assertIn('participant "<size:30><&file>\\nLocalFileServer SFTP" as LocalFileServer', uml_content)
        self.assertIn('participant "<size:30><&globe>\\nRequest" as HTTP', uml_content)
        self.assertIn('queue "Queue\\nroadtrip"', uml_content)

        # Assert initial event
        self.assertIn('"LocalFileServer" -> "sftp:listener\\n[New Cattle Transcript Uploaded]" : File Transfer: (Listener)', uml_content)

        # Assert SFTP listener configuration
        self.assertIn('"sftp:listener\\n[New Cattle Transcript Uploaded]" -> "sftp:listener\\n[New Cattle Transcript Uploaded]" : listener.maxRedeliveryCount: 2', uml_content)
        self.assertIn('"sftp:listener\\n[New Cattle Transcript Uploaded]" -> "sftp:listener\\n[New Cattle Transcript Uploaded]" : scheduling-strategy.frequency: 10', uml_content)
        self.assertIn('"sftp:listener\\n[New Cattle Transcript Uploaded]" -> "sftp:listener\\n[New Cattle Transcript Uploaded]" : scheduling-strategy.timeUnit: SECONDS', uml_content)

        # Assert try blocks
        self.assertIn(f'alt#{self.analyzer_properties["diagram_formatting_properties"]["try"]["label-color"]} #{self.analyzer_properties["diagram_formatting_properties"]["try"]["background-color"]} Try Getting Tunes', uml_content)
        self.assertIn(f'alt#{self.analyzer_properties["diagram_formatting_properties"]["try"]["label-color"]} #{self.analyzer_properties["diagram_formatting_properties"]["try"]["background-color"]} Try Creating Request Arguments', uml_content)
        
        # Assert until successful blocks
        self.assertIn('loop Until Successful max retries: 3', uml_content)
        self.assertIn('loop Until Successful - Never Give Up max retries: 99999', uml_content)

        # Assert HTTP request
        cow_tunes_path = Path("tests/mule/analyzer-tests/src/main/resources/properties/dummy.yaml")
        with cow_tunes_path.open('r', encoding='utf-8') as file:
            dummy_yaml = yaml.safe_load(file)
        cow_tunes_path_value = dummy_yaml['cow']['tunes']['path']
        
        self.assertIn(f'"http:request\\n[GET Cow Tunes]" -> "HTTP" : HTTP Request: (GET {cow_tunes_path_value})', uml_content)
        self.assertIn('"HTTP" --> "http:request\\n[GET Cow Tunes]" : ', uml_content)

        # Assert queue message
        self.assertIn('"anypoint-mq:publish\\n[Publish Tracklist to Queue]" -> "Queue\\nroadtrip" : Message (roadtrip)', uml_content)
        self.assertIn('"Queue\\nroadtrip" --> "anypoint-mq:publish\\n[Publish Tracklist to Queue]" : ', uml_content)

        # Assert error handling
        self.assertIn(f'note over "ee:transform\\n[Create requestBody]" #{self.analyzer_properties["diagram_formatting_properties"]["errors"]["color"]}: Inline Error Handler', uml_content)
        self.assertIn(f'note over "http:request\\n[GET Cow Tunes]" #{self.analyzer_properties["diagram_formatting_properties"]["errors"]["color"]}: Inline Error Handler', uml_content)

    def test_analyzer_icons_test_flow(self):
        """Test analyzer icons test flow with email and HTTP"""
        flow_name = "icons-testFlow"
        flow_source_file = "src\\main\\mule\\icons-test.xml"

        uml_content = self._common_analyze_flow_and_get_content(flow_name, flow_source_file)

        # Assert that the main components are present
        self.assertIn('participant "email:listener-imap\\n[On New Email - IMAP]"', uml_content)
        self.assertIn('participant "set-payload\\n[Set Request Payload]"', uml_content)
        self.assertIn('participant "http:request\\n[POST Customer Details]"', uml_content)

        # Assert external systems with icons
        self.assertIn('participant "<size:30><&envelope-closed>\\nIMAP" as Email', uml_content)
        self.assertIn('participant "<size:30><&globe>\\nRequest" as HTTP', uml_content)

        # Assert initial email event
        self.assertIn('"Email" -> "email:listener-imap\\n[On New Email - IMAP]" : Email Message', uml_content)

        # Assert scheduler configuration
        self.assertIn('"email:listener-imap\\n[On New Email - IMAP]" -> "email:listener-imap\\n[On New Email - IMAP]" : scheduling-strategy.frequency: 60', uml_content)
        self.assertIn('"email:listener-imap\\n[On New Email - IMAP]" -> "email:listener-imap\\n[On New Email - IMAP]" : scheduling-strategy.timeUnit: SECONDS', uml_content)

        # Assert HTTP request
        self.assertIn('"http:request\\n[POST Customer Details]" -> "HTTP" : HTTP Request: (GET /)', uml_content)
        self.assertIn('"HTTP" --> "http:request\\n[POST Customer Details]" : ', uml_content)

    def test_analyzer_icons_test_flow1(self):
        """Test analyzer icons test flow with scheduler and sockets"""
        flow_name = "icons-testFlow1"
        flow_source_file = "src\\main\\mule\\icons-test.xml"

        uml_content = self._common_analyze_flow_and_get_content(flow_name, flow_source_file)

        # Assert that the main components are present
        self.assertIn('participant "scheduler\\n[Scheduler]"', uml_content)
        self.assertIn('participant "sockets:send\\n[Send Data]"', uml_content)

        # Assert external systems with icons
        self.assertIn('participant "<size:30><&clock>\\nScheduler" as Scheduler', uml_content)
        self.assertIn('participant "<size:30><&link-intact>\\nSockets" as Sockets', uml_content)

        # Assert initial scheduler event
        self.assertIn('"Scheduler" -> "scheduler\\n[Scheduler]" : Scheduled Task', uml_content)

        # Assert scheduler configuration
        self.assertIn('"scheduler\\n[Scheduler]" -> "scheduler\\n[Scheduler]" : scheduling-strategy.expression: * * * * * *', uml_content)
        self.assertIn('"scheduler\\n[Scheduler]" -> "scheduler\\n[Scheduler]" : scheduling-strategy.timeZone: Adelaide/Australia', uml_content)

        # Assert socket connection
        self.assertIn('"sockets:send\\n[Send Data]" -> "Sockets" : Socket Connection', uml_content)
        self.assertIn('"Sockets" --> "sockets:send\\n[Send Data]" : ', uml_content)

    def test_analyzer_async_operation(self):
        """Test analyzer async operation flow with Salesforce, database, and email"""
        flow_name = "async-operation"
        flow_source_file = "src\\main\\mule\\async-operations.xml"

        uml_content = self._common_analyze_flow_and_get_content(flow_name, flow_source_file)

        # Assert that the main components are present
        self.assertIn('participant "salesforce:subscribe-channel-listener\\n[Subscribe channel listener]"', uml_content)
        self.assertIn('participant "db:insert\\n[Insert Subscription]"', uml_content)
        self.assertIn('participant "set-variable\\n[customerId]"', uml_content)
        self.assertIn('participant "email:send\\n[New Subscription Email]"', uml_content)
        self.assertIn('participant "db:update\\n[Update Subscription Emails]"', uml_content)
        self.assertIn('participant "salesforce:delete\\n[Delete Subscription]"', uml_content)

        # Assert external systems with icons
        self.assertIn('participant "<size:30><color:#00A1E0><&cloud>\\nExperience Cloud" as Experience', uml_content)
        self.assertIn('database "Database\\nA"', uml_content)
        self.assertIn('participant "<size:30><&envelope-closed>\\nSMTP" as Email', uml_content)

        # Assert initial Salesforce event
        self.assertIn('"Experience" -> "salesforce:subscribe-channel-listener\\n[Subscribe channel listener]" : subscribe-channel-listener', uml_content)

        # Assert database operations
        self.assertIn('"db:insert\\n[Insert Subscription]" -> "db:insert\\n[Insert Subscription]" : insert.sql', uml_content)
        self.assertIn('"db:insert\\n[Insert Subscription]" -> "db:insert\\n[Insert Subscription]" : insert.input parameters', uml_content)
        self.assertIn('"db:insert\\n[Insert Subscription]" -> "Database\\nA" : Database Change: (Insert)', uml_content)
        self.assertIn('"Database\\nA" --> "db:insert\\n[Insert Subscription]" : ', uml_content)

        # Assert async group and sub-flow
        self.assertIn(f'group #{self.analyzer_properties["diagram_formatting_properties"]["async"]["background-color"]} async', uml_content)
        self.assertIn('group sub-flow new-subscription-email', uml_content)

        # Assert email operations is async
        async_arrow = self.analyzer_properties['diagram_formatting_properties']['arrows']['async']
        self.assertIn(f'"email:send\\n[New Subscription Email]" {async_arrow} "Email" : Email Message', uml_content)
        self.assertIn('"Email" --> "email:send\\n[New Subscription Email]" : ', uml_content)

        # Assert final Salesforce operation
        self.assertIn('"salesforce:delete\\n[Delete Subscription]" -> "Experience_4" : delete', uml_content)
        self.assertIn('"Experience_4" --> "salesforce:delete\\n[Delete Subscription]" : ', uml_content)

        # Assert database update in sub-flow
        self.assertIn(f'"db:update\\n[Update Subscription Emails]" -> "db:update\\n[Update Subscription Emails]" : update.sql', uml_content)
        self.assertIn(f'"db:update\\n[Update Subscription Emails]" -> "db:update\\n[Update Subscription Emails]" : update.input parameters', uml_content)
        self.assertIn(f'"db:update\\n[Update Subscription Emails]" -> "Database\\nA" : Database Change: (Update)', uml_content)
        self.assertIn('"Database\\nA" --> "db:update\\n[Update Subscription Emails]" : ', uml_content)

    def test_analyzer_control_flows_cache(self):
        """Test analyzer control flows with cache and database operations"""
        flow_name = "control-flows-cache"
        flow_source_file = "src\\main\\mule\\control-flows-cache.xml"

        self.analyzer_properties['diagram_formatting_properties']['verbose']['logging'] = True

        uml_content = self._common_analyze_flow_and_get_content(flow_name, flow_source_file)

        # Assert that the main components are present
        self.assertIn('participant "sockets:listener\\n[WebSocket Listener]"', uml_content)
        self.assertIn('participant "tracing:set-logging-variable\\n[Set logging variable]"', uml_content)
        self.assertIn('participant "java:invoke\\n[Execute MyClass]"', uml_content)
        self.assertIn('participant "db:stored-procedure\\n[Convert ID to Object]"', uml_content)
        self.assertIn('participant "ee:transform\\n[Create Message]"', uml_content)
        self.assertIn('participant "ibm-mq:publish\\n[Publish]"', uml_content)

        # Assert external systems
        self.assertIn('participant "<size:30><&link-intact>\\nSockets Listener" as Sockets', uml_content)
        self.assertIn('database "Database\\nB"', uml_content)
        self.assertIn('queue "Queue\\nidmessages"', uml_content)

        # Assert initial socket connection
        self.assertIn('"Sockets" -> "sockets:listener\\n[WebSocket Listener]" : Socket Connection', uml_content)

        # Assert cache structure
        self.assertIn('alt Cache Miss', uml_content)
        self.assertIn('note over "tracing:set-logging-variable\\n[Set logging variable]": Cache by ID', uml_content)
        self.assertIn('else Cache Hit', uml_content)
        self.assertIn('"tracing:set-logging-variable\\n[Set logging variable]" -> "ee:transform\\n[Create Message]" : Use Cached Value', uml_content)
        self.assertIn('end', uml_content)

        # Assert database stored procedure details
        self.assertIn('"db:stored-procedure\\n[Convert ID to Object]" -> "db:stored-procedure\\n[Convert ID to Object]" : stored-procedure.sql', uml_content)
        self.assertIn('"db:stored-procedure\\n[Convert ID to Object]" -> "db:stored-procedure\\n[Convert ID to Object]" : in-out-parameters.key: id', uml_content)
        self.assertIn('"db:stored-procedure\\n[Convert ID to Object]" -> "db:stored-procedure\\n[Convert ID to Object]" : in-out-parameters.value: payload.id', uml_content)
        self.assertIn('"db:stored-procedure\\n[Convert ID to Object]" -> "db:stored-procedure\\n[Convert ID to Object]" : output-parameters.key: 0', uml_content)
        self.assertIn('"db:stored-procedure\\n[Convert ID to Object]" -> "db:stored-procedure\\n[Convert ID to Object]" : output-parameters.type: STRUCT', uml_content)
        self.assertIn('"db:stored-procedure\\n[Convert ID to Object]" -> "Database\\nB" : Database Change: (Stored procedure)', uml_content)
        self.assertIn('"Database\\nB" --> "db:stored-procedure\\n[Convert ID to Object]" : ', uml_content)

        # Assert transform and queue operations
        self.assertIn('"ee:transform\\n[Create Message]" -> "ee:transform\\n[Create Message]" : variables.variableName: myMessage', uml_content)
        self.assertIn('"ibm-mq:publish\\n[Publish]" -> "ibm-mq:publish\\n[Publish]" : message.body', uml_content)
        self.assertIn('"ibm-mq:publish\\n[Publish]" -> "Queue\\nidmessages" : Message (idmessages)', uml_content)
        self.assertIn('"Queue\\nidmessages" --> "ibm-mq:publish\\n[Publish]" : ', uml_content)

    def test_analyzer_control_flows_scatter_and_verbose_logger_output(self):
        """Test analyzer control flows with scatter-gather, first-successful, and parallel-foreach"""
        flow_name = "control-flows-scatterFlow"
        flow_source_file = "src\\main\\mule\\control-flows-scatter.xml"

        self.analyzer_properties['diagram_formatting_properties']['verbose']['logging'] = True

        uml_content = self._common_analyze_flow_and_get_content(flow_name, flow_source_file)

        # Assert that the main components are present
        self.assertIn('participant "http:listener\\n[Treasure Listener]"', uml_content)
        self.assertIn('participant "set-variable\\n[coordinates]"', uml_content)
        self.assertIn('participant "logger\\n[To Tatooga]"', uml_content)
        self.assertIn('participant "http:request\\n[Request Tatooga Payload]"', uml_content)
        self.assertIn('participant "logger\\n[To Bermuda]"', uml_content)
        self.assertIn('participant "http:request\\n[Request Bermuda Payload]"', uml_content)
        self.assertIn('participant "logger\\n[To Aruba]"', uml_content)
        self.assertIn('participant "http:request\\n[Request Aruba Payload]"', uml_content)
        self.assertIn('participant "ee:transform\\n[Set Shanty and Loot]"', uml_content)
        self.assertIn('participant "logger\\n[First Success]"', uml_content)
        self.assertIn('participant "logger\\n[Second Success]"', uml_content)
        self.assertIn('participant "set-payload\\n[Set Payload]"', uml_content)
        self.assertIn('participant "logger\\n[Booty Value]"', uml_content)

        # Assert external systems with icons
        self.assertIn('participant "<size:30><&globe>\\nHTTP" as HTTP', uml_content)
        self.assertIn('participant "<size:30><&globe>\\nRequest" as HTTP_1', uml_content)

        # Assert initial HTTP request
        self.assertIn('"HTTP" -> "http:listener\\n[Treasure Listener]" : HTTP Request: (/treasure)', uml_content)

        # Assert scatter-gather structure
        self.assertIn('par Visit Coordinates', uml_content)
        self.assertIn('else', uml_content)
        self.assertIn('end', uml_content)

        # Assert HTTP requests for each route
        for island in ['Tatooga', 'Bermuda', 'Aruba']:
            self.assertIn(f'"http:request\\n[Request {island} Payload]" -> "http:request\\n[Request {island} Payload]" : request.body', uml_content)
            self.assertIn(f'"http:request\\n[Request {island} Payload]" -> "http:request\\n[Request {island} Payload]" : request.uri params', uml_content)
            self.assertIn(f'"http:request\\n[Request {island} Payload]" -> "HTTP_1" : HTTP Request: (GET /islands/{{island-name}})', uml_content)
            self.assertIn(f'"HTTP_1" --> "http:request\\n[Request {island} Payload]" : ', uml_content)
            self.assertIn(f'"http:request\\n[Request {island} Payload]" -\\ "ee:transform\\n[Set Shanty and Loot]" : ', uml_content)

        # Assert first-successful structure
        self.assertIn('par Parallel Logging Competition', uml_content)
        self.assertIn('note over "ee:transform\\n[Set Shanty and Loot]" : First Successful Will Be Used', uml_content)
        self.assertIn('"logger\\n[First Success]" -\\ "set-payload\\n[Set Payload]" : ', uml_content)
        self.assertIn('"logger\\n[Second Success]" -\\ "set-payload\\n[Set Payload]" : ', uml_content)

        # Assert parallel-foreach
        self.assertIn('loop Parallel For Each\\nCollection: vars.booty', uml_content)
        self.assertIn('"set-payload\\n[Set Payload]" -> "logger\\n[Booty Value]" : ', uml_content)

    def test_analyzer_text_output(self):
        """Test analyzer text output"""
        flow_name = "control-flows-until-successful"
        flow_source_file = "src\\main\\mule\\control-flows.xml"

        # Set output type to TEXT
        self.analyzer_properties['analyzer_properties']['output_type'] = OutputFormat.TEXT
        print(f"Output type set to: {self.analyzer_properties['analyzer_properties']['output_type']}")

        # Update analyzer configuration
        self.analyzer.set_configuration_properties(self.analyzer_properties)

        # Assert the configuration was updated correctly
        config = self.analyzer.get_configuration_properties()
        self.assertEqual(config['analyzer_properties']['output_type'], OutputFormat.TEXT)

        # Capture stdout
        captured_output = StringIO()
        output = ""

        try:
            sys.stdout = captured_output
            self.analyzer.analyze_mule_flows(flow_name=flow_name)
            output = captured_output.getvalue()
        finally:
            # Restore stdout
            sys.stdout = sys.__stdout__

        print(f"Captured output length: {len(output)}")
        print(f"Captured output: {output}")

        # Expected output structure
        expected_output = """--------------------------------
Flow: control-flows-until-successful
--------------------------------
flow [control-flows-until-successful]
  sftp:listener [New Cattle Transcript Uploaded]
  try [Try Getting Tunes]
    try [Try Creating Request Arguments]
      ee:transform [Create requestBody]
    until-successful [Until Successful]
      http:request [GET Cow Tunes]
  ee:transform [Create Mixtape]
  until-successful [Never Give Up]
    anypoint-mq:publish [Publish Tracklist to Queue]
"""

        # Assert the output matches expected structure
        self.assertEqual(output.strip(), expected_output.strip())

    def test_renderer_mode_defaults_to_server_for_backwards_compatibility(self):
        """If mode is omitted, rendering should default to server mode."""
        config_without_mode = copy.deepcopy(self.analyzer_properties)
        config_without_mode['analyzer_properties']['plantuml'].pop('mode', None)
        generator = SequenceDiagramGenerator(configuration_properties=config_without_mode)
        self.assertEqual(generator._detect_renderer_mode(), 'server')

    def test_renderer_mode_validation_rejects_invalid_mode(self):
        """Invalid PlantUML mode should raise ConfigurationError."""
        invalid_mode_config = copy.deepcopy(self.analyzer_properties)
        invalid_mode_config['analyzer_properties']['plantuml']['mode'] = 'invalid-mode'
        generator = SequenceDiagramGenerator(configuration_properties=invalid_mode_config)
        with self.assertRaises(ConfigurationError):
            generator._detect_renderer_mode()

    def test_render_image_dispatches_based_on_mode(self):
        """render_image should dispatch to the correct renderer backend."""
        syntax = ["@startuml", "Alice -> Bob : hello", "@enduml"]

        for mode, expected_backend in [('server', '_render_with_server'), ('jar', '_render_with_jar'), ('cli', '_render_with_cli')]:
            with self.subTest(mode=mode):
                config = copy.deepcopy(self.analyzer_properties)
                config['analyzer_properties']['plantuml']['mode'] = mode
                config['analyzer_properties']['plantuml']['output_directory'] = self.output_dir
                generator = SequenceDiagramGenerator(configuration_properties=config)
                fake_outfile = str(self.output_dir / f"{mode}.png")

                with patch.object(generator, '_render_with_server', return_value=fake_outfile) as mock_server, \
                     patch.object(generator, '_render_with_jar', return_value=fake_outfile) as mock_jar, \
                     patch.object(generator, '_render_with_cli', return_value=fake_outfile) as mock_cli:
                    result = generator.render_image(syntax, f"dispatch-{mode}")
                    self.assertEqual(result, fake_outfile)

                    called = {
                        '_render_with_server': mock_server.called,
                        '_render_with_jar': mock_jar.called,
                        '_render_with_cli': mock_cli.called
                    }
                    self.assertTrue(called[expected_backend], f"{expected_backend} should be called for mode={mode}")
                    for backend, was_called in called.items():
                        if backend != expected_backend:
                            self.assertFalse(was_called, f"{backend} should not be called for mode={mode}")

    def test_mermaid_generator_creates_sequence_syntax(self):
        """Mermaid generator should emit sequenceDiagram syntax."""
        flow = MuleFlowElement(
            'flow',
            {'name': 'test-flow'},
            children=[
                MuleFlowElement('http:listener', {'config-ref': 'HTTP_CONFIG', 'path': '/orders'}),
                MuleFlowElement('choice', {}, children=[
                    MuleFlowElement('when', {'expression': '#[payload.valid]'}, children=[
                        MuleFlowElement('db:select', {'config-ref': 'DB_CUSTOMER_CONFIG'}),
                    ]),
                    MuleFlowElement('otherwise', {}, children=[
                        MuleFlowElement('logger', {'message': 'invalid'}),
                    ]),
                ]),
                MuleFlowElement('async', {}, children=[
                    MuleFlowElement('http:request', {'config-ref': 'HTTP_DOWNSTREAM', 'method': 'POST', 'path': '/notify'}),
                ]),
            ],
        )
        config = copy.deepcopy(self.analyzer_properties)
        config['analyzer_properties']['diagram_engine'] = 'mermaid'
        generator = MermaidSequenceDiagramGenerator(configuration_properties=config)

        mermaid_content = generator.generate_sequence_diagram_syntax(flow)

        self.assertEqual(mermaid_content[0], 'sequenceDiagram')
        self.assertEqual(mermaid_content[1], 'title test-flow')
        self.assertIn('box Consumers', mermaid_content)
        self.assertIn('actor HTTP as Consumer - HTTP', mermaid_content)
        self.assertIn('box Mule Components', mermaid_content)
        self.assertIn('participant http_listener as Mule - http:listener', mermaid_content)
        self.assertIn('box Providers', mermaid_content)
        self.assertIn('participant HTTP_DOWNSTREAM as Provider - HTTP DOWNSTREAM', mermaid_content)
        self.assertIn('alt payload.valid', mermaid_content)
        self.assertIn('else otherwise', mermaid_content)
        self.assertIn('Note over http_listener: Async Start', mermaid_content)
        self.assertTrue(any('HTTP_DOWNSTREAM' in line for line in mermaid_content))

    def test_mermaid_scatter_gather_consolidates_all_parallel_routes(self):
        """Mermaid scatter-gather output should keep every route endpoint before the join."""
        flow = MuleFlowElement(
            'flow',
            {'name': 'scatter-flow'},
            children=[
                MuleFlowElement('http:listener', {'config-ref': 'HTTP_CONFIG', 'path': '/scatter'}),
                MuleFlowElement('scatter-gather', {'documentation:name': 'Fan Out'}, children=[
                    MuleFlowElement('route', {}, children=[
                        MuleFlowElement('set-variable', {'variableName': 'routeA'}),
                    ]),
                    MuleFlowElement('route', {}, children=[
                        MuleFlowElement('set-variable', {'variableName': 'routeB'}),
                    ]),
                ]),
                MuleFlowElement('ee:transform', {'documentation:name': 'Join Routes'}),
            ],
        )
        config = copy.deepcopy(self.analyzer_properties)
        config['analyzer_properties']['diagram_engine'] = 'mermaid'
        generator = MermaidSequenceDiagramGenerator(configuration_properties=config)

        mermaid_content = generator.generate_sequence_diagram_syntax(flow)

        self.assertIn('set_variable_routeA ->> ee_transform_Join_Routes: ', mermaid_content)
        self.assertIn('set_variable_routeB ->> ee_transform_Join_Routes: ', mermaid_content)

    def test_mermaid_transactions_follow_plantuml_start_and_end_semantics(self):
        """Mermaid transaction notes should only mark actual transaction boundaries."""
        flow = MuleFlowElement(
            'flow',
            {'name': 'transaction-flow'},
            children=[
                MuleFlowElement(
                    'jms:listener',
                    {
                        'destination': 'orders',
                        'transactionalAction': 'ALWAYS_BEGIN',
                        'transactionType': 'XA',
                    },
                ),
                MuleFlowElement('db:insert', {'config-ref': 'DB_A', 'transactionalAction': 'ALWAYS_JOIN'}),
            ],
        )
        config = copy.deepcopy(self.analyzer_properties)
        config['analyzer_properties']['diagram_engine'] = 'mermaid'
        generator = MermaidSequenceDiagramGenerator(configuration_properties=config)

        mermaid_content = generator.generate_sequence_diagram_syntax(flow)

        self.assertIn('Note over jms_listener: XA Transaction Starting', mermaid_content)
        self.assertIn('Note over db_insert: XA Transaction End', mermaid_content)
        self.assertFalse(any('Local Transaction Starting' in line for line in mermaid_content))

    def test_mermaid_render_file_mode_writes_mmd_source(self):
        """Mermaid file mode should write source and return the .mmd path."""
        mermaid_output_dir = Path('tests/output/mermaid')
        if mermaid_output_dir.exists():
            shutil.rmtree(mermaid_output_dir)

        config = copy.deepcopy(self.analyzer_properties)
        config['analyzer_properties']['mermaid']['output_directory'] = mermaid_output_dir
        config['analyzer_properties']['mermaid']['mode'] = 'file'
        generator = MermaidSequenceDiagramGenerator(configuration_properties=config)

        result = generator.render_image(['sequenceDiagram', 'participant A', 'participant B', 'A ->> B: hello'], 'mermaid-flow')

        expected_path = mermaid_output_dir / 'mermaid-flow.mmd'
        self.assertEqual(result, str(expected_path))
        self.assertTrue(expected_path.exists())
        self.assertIn('A ->> B: hello', expected_path.read_text())
        shutil.rmtree(mermaid_output_dir)

    def test_mermaid_render_cli_mode_is_mockable(self):
        """Mermaid CLI mode should dispatch to the CLI renderer without requiring mmdc in tests."""
        mermaid_output_dir = Path('tests/output/mermaid-cli')
        if mermaid_output_dir.exists():
            shutil.rmtree(mermaid_output_dir)

        config = copy.deepcopy(self.analyzer_properties)
        config['analyzer_properties']['mermaid']['output_directory'] = mermaid_output_dir
        config['analyzer_properties']['mermaid']['mode'] = 'cli'
        config['analyzer_properties']['mermaid']['format'] = 'svg'
        generator = MermaidSequenceDiagramGenerator(configuration_properties=config)
        fake_outfile = str(mermaid_output_dir / 'mermaid-cli-flow.svg')

        with patch.object(generator, '_render_with_cli', return_value=fake_outfile) as mock_cli:
            result = generator.render_image(['sequenceDiagram', 'A ->> B: hello'], 'mermaid-cli-flow')

        self.assertEqual(result, fake_outfile)
        mock_cli.assert_called_once()
        self.assertTrue((mermaid_output_dir / 'mermaid-cli-flow.mmd').exists())
        shutil.rmtree(mermaid_output_dir)

    def test_analyzer_selects_mermaid_generator(self):
        """Analyzer should select Mermaid generator when diagram_engine is mermaid."""
        analyzer = MuleFlowAnalyzer(user_config={
            'analyzer_properties': {
                'output_type': OutputFormat.SEQUENCE,
                'diagram_engine': 'mermaid',
            }
        })

        self.assertIsInstance(analyzer._get_sequence_diagram_generator(), MermaidSequenceDiagramGenerator)

if __name__ == '__main__':
    unittest.main()


import copy
import os
import shutil
import sys
import unittest
from io import StringIO
from pathlib import Path

from mule_flow_analyzer.analyzer.mule_flow_analyzer import MuleFlowAnalyzer
from mule_flow_analyzer.analyzer.mule_flow_element import MuleFlowElement
from mule_flow_analyzer.analyzer.natural_language_description_generator import (
    NaturalLanguageDescriptionGenerator,
)
from mule_flow_analyzer.config.constants import OutputFormat, normalize_output_format
from mule_flow_analyzer.config.default_properties import DEFAULT_PROPERTIES


class TestNaturalLanguageDescriptionGenerator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_project_path = Path("tests/mule/analyzer-tests")
        cls.output_dir = Path("tests/output/natural")
        cls.analyzer_properties = copy.deepcopy(DEFAULT_PROPERTIES)
        cls.analyzer_properties["analyzer_properties"]["natural"]["output_directory"] = cls.output_dir

    def setUp(self):
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)
        os.makedirs(self.output_dir)
        self.generator = NaturalLanguageDescriptionGenerator(
            configuration_properties=self.analyzer_properties
        )
        self.analyzer = MuleFlowAnalyzer(
            project_path=self.test_project_path,
            property_files=None,
            user_config=self.analyzer_properties,
        )

    def tearDown(self):
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)

    def test_normalize_output_format_accepts_strings(self):
        self.assertEqual(normalize_output_format("NATURAL"), OutputFormat.NATURAL)
        self.assertEqual(normalize_output_format("text"), OutputFormat.TEXT)
        self.assertEqual(normalize_output_format(OutputFormat.SEQUENCE), OutputFormat.SEQUENCE)

    def test_generate_description_includes_target_variable_save(self):
        flow = MuleFlowElement(
            "flow",
            {"name": r"post:\tickets:application\json:target-flow"},
            children=[
                MuleFlowElement(
                    "os:retrieve",
                    {
                        "documentation:name": "Retrieve Current Ticket",
                        "target": "currentTicketNumber",
                    },
                ),
            ],
        )

        description = self.generator.generate_description(flow)
        text = "\n".join(description)

        self.assertIn("Save output to variable currentTicketNumber.", text)

    def test_generate_description_includes_trigger_and_steps(self):
        flow_name = "control-flows-until-successful"
        config = copy.deepcopy(self.analyzer_properties)
        config["analyzer_properties"]["output_type"] = OutputFormat.NATURAL
        self.analyzer.set_configuration_properties(config)
        self.analyzer.analyze_mule_flows(flow_name=flow_name)
        flow = self.analyzer.project_files[
            "src/main/mule/control-flows.xml"
        ].get_flows(flow_name)[0]

        description = self.generator.generate_description(flow)
        text = "\n".join(description)

        self.assertIn('Flow "control-flows-until-successful":', text)
        self.assertIn(
            "Triggered by File Transfer: (Listener) (New Cattle Transcript Uploaded).",
            text,
        )
        self.assertIn("Try (Try Getting Tunes):", text)
        self.assertIn("Transform data: Create requestBody.", text)
        self.assertIn("Call HTTP Request: (GET", text)
        self.assertIn('via "HTTP_Request_configuration"', text)
        self.assertIn("Transform data: Create Mixtape.", text)
        self.assertIn("Retry until successful in Until Successful", text)

    def test_write_output_creates_file_with_sanitized_name(self):
        flow_name = "control-flows-until-successful"
        lines = ['Flow "control-flows-until-successful":', "Triggered by test."]
        output_file = self.generator.write_output(lines, flow_name)

        expected_path = self.output_dir / "control-flows-until-successful.txt"
        self.assertEqual(output_file, str(expected_path))
        self.assertTrue(expected_path.exists())
        self.assertIn("Triggered by test.", expected_path.read_text(encoding="utf-8"))

    def test_analyzer_natural_output_writes_file_not_stdout(self):
        flow_name = "control-flows-until-successful"
        config = copy.deepcopy(self.analyzer_properties)
        config["analyzer_properties"]["output_type"] = OutputFormat.NATURAL
        self.analyzer.set_configuration_properties(config)

        captured_output = StringIO()
        try:
            sys.stdout = captured_output
            self.analyzer.analyze_mule_flows(flow_name=flow_name)
        finally:
            sys.stdout = sys.__stdout__

        self.assertEqual(captured_output.getvalue(), "")
        expected_path = self.output_dir / "control-flows-until-successful.txt"
        self.assertTrue(expected_path.exists())
        content = expected_path.read_text(encoding="utf-8")
        self.assertIn("Triggered by File Transfer: (Listener)", content)

    def test_analyzer_natural_output_from_string_config(self):
        flow_name = "control-flows-until-successful"
        config = copy.deepcopy(self.analyzer_properties)
        config["analyzer_properties"]["output_type"] = "NATURAL"
        analyzer = MuleFlowAnalyzer(
            project_path=self.test_project_path,
            property_files=None,
            user_config=config,
        )

        analyzer.analyze_mule_flows(flow_name=flow_name)

        expected_path = self.output_dir / "control-flows-until-successful.txt"
        self.assertTrue(expected_path.exists())

    def test_text_output_still_prints_to_stdout(self):
        flow_name = "control-flows-until-successful"
        config = copy.deepcopy(self.analyzer_properties)
        config["analyzer_properties"]["output_type"] = OutputFormat.TEXT
        self.analyzer.set_configuration_properties(config)

        captured_output = StringIO()
        try:
            sys.stdout = captured_output
            self.analyzer.analyze_mule_flows(flow_name=flow_name)
            output = captured_output.getvalue()
        finally:
            sys.stdout = sys.__stdout__

        self.assertIn("Flow: control-flows-until-successful", output)
        self.assertIn("flow [control-flows-until-successful]", output)
        self.assertFalse(list(self.output_dir.glob("*.txt")))

    def test_quotes_embedded_custom_names(self):
        flow_name = "batch-job-flow"
        config = copy.deepcopy(self.analyzer_properties)
        config["analyzer_properties"]["output_type"] = OutputFormat.NATURAL
        self.analyzer.set_configuration_properties(config)
        self.analyzer.analyze_mule_flows(flow_name=flow_name)
        flow = self.analyzer.project_files["src/main/mule/batch-job-flow.xml"].get_flows(flow_name)[0]

        text = "\n".join(self.generator.generate_description(flow))

        self.assertIn('Batch job "MegaPirateBatchProcessor":', text)
        self.assertIn('Batch "process records":', text)
        self.assertIn('Batch step "DetectTales":', text)
        self.assertIn("Transform data: Transform to Pirate Data Model.", text)
        self.assertIn("Execute tracking:custom-event [Custom Business Event]", text)
        self.assertIn(
            'Publish message to "shanty-errors" (Walk Plank) via "IBM_MQ_Config", then return to Mule.',
            text,
        )
        self.assertIn('Call "student-transfer-credit" via "Workday_Config"', text)
        self.assertIn('Call Database Operation: (Insert) via "DB_A_Database_Config"', text)

    def test_vm_queues_preserves_messaging_operations(self):
        flow_name = "vm-queues-queues"
        config = copy.deepcopy(self.analyzer_properties)
        config["analyzer_properties"]["output_type"] = OutputFormat.NATURAL
        self.analyzer.set_configuration_properties(config)
        self.analyzer.analyze_mule_flows(flow_name=flow_name)
        flow = self.analyzer.project_files["src/main/mule/jms-transaction.xml"].get_flows(flow_name)[0]

        text = "\n".join(self.generator.generate_description(flow))

        self.assertIn(
            'Triggered by Listen for messages on "my-vm-queue" (Listener) via "BradsVm_queue_config".',
            text,
        )
        self.assertIn(
            'Publish and consume message on "some-vm-queue" (Publish consume) via "BradsVm_queue_config", then return to Mule.',
            text,
        )
        self.assertIn(
            'Consume message from "some-vm-queue2" (Consume) via "BradsVm_queue_config", then return to Mule.',
            text,
        )
        self.assertIn(
            'Publish message to "some-vm-queue2" (Publish) via "BradsVm_queue_config", then return to Mule.',
            text,
        )
        self.assertNotIn('Call Message (some-vm-queue2) via "BradsVm_queue_config"', text)


if __name__ == "__main__":
    unittest.main()

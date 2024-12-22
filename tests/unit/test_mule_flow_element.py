import unittest
from src.mule_flow_element import MuleFlowElement

class TestMuleFlowElement(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test"""
        self.basic_element = MuleFlowElement(
            tag="test-tag",
            attributes={"name": "test-name"},
            content="test content"
        )

    def test_initialization_basic(self):
        """Test basic initialization of MuleFlowElement"""
        element = MuleFlowElement(tag="test-tag")
        self.assertEqual(element.tag, "test-tag")
        self.assertEqual(element.attributes, {})
        self.assertEqual(element.children, [])
        self.assertEqual(element.processes, [])
        self.assertEqual(element.content, "")
        self.assertEqual(element.notes, "")
        self.assertTrue(element.standalone)
        self.assertIsNone(element.error_handler_ref)
        self.assertIsNone(element.error_handler_element)

    def test_initialization_with_all_params(self):
        """Test initialization with all parameters"""
        attributes = {"name": "test-name", "type": "test-type"}
        children = [MuleFlowElement(tag="child1"), MuleFlowElement(tag="child2")]
        processes = [MuleFlowElement(tag="process1")]
        error_handler = [MuleFlowElement(tag="error-handler")]

        element = MuleFlowElement(
            tag="test-tag",
            attributes=attributes,
            children=children,
            processes=processes,
            content="test content",
            notes="test notes",
            standalone=False,
            error_handler_ref="test-error-handler",
            error_handler_element=error_handler
        )

        self.assertEqual(element.tag, "test-tag")
        self.assertEqual(element.attributes, attributes)
        self.assertEqual(element.children, children)
        self.assertEqual(element.processes, processes)
        self.assertEqual(element.content, "test content")
        self.assertEqual(element.notes, "test notes")
        self.assertFalse(element.standalone)
        self.assertEqual(element.error_handler_ref, "test-error-handler")
        self.assertEqual(element.error_handler_element, error_handler)

    def test_initialization_empty_tag(self):
        """Test initialization with empty tag raises ValueError"""
        with self.assertRaises(ValueError):
            MuleFlowElement(tag="")
        with self.assertRaises(ValueError):
            MuleFlowElement(tag=None)

    def test_str_representation(self):
        """Test string representation of different element types"""
        # Test set-variable element
        set_var_element = MuleFlowElement(
            tag="set-variable",
            attributes={"variableName": "myVar"}
        )
        self.assertEqual(str(set_var_element), "set-variable [myVar]")

        # Test error handler element with 'when' attribute
        error_element = MuleFlowElement(
            tag="on-error-propagate",
            attributes={"when": "error-condition"}
        )
        self.assertEqual(str(error_element), "on-error-propagate [error-condition]")

        # Test error handler element with 'type' attribute
        error_element = MuleFlowElement(
            tag="on-error-continue",
            attributes={"type": "ERROR_TYPE"}
        )
        self.assertEqual(str(error_element), "on-error-continue [ERROR_TYPE]")

        # Test element with name attribute
        named_element = MuleFlowElement(
            tag="flow",
            attributes={"name": "test-flow"}
        )
        self.assertEqual(str(named_element), "flow [test-flow]")

        # Test element with documentation:name attribute
        doc_element = MuleFlowElement(
            tag="flow",
            attributes={"documentation:name": "doc-flow"}
        )
        self.assertEqual(str(doc_element), "flow [doc-flow]")

        # Test element without identifier attributes
        plain_element = MuleFlowElement(tag="logger")
        self.assertEqual(str(plain_element), "logger")

    def test_add_child(self):
        """Test adding child elements"""
        parent = MuleFlowElement(tag="parent")
        child = MuleFlowElement(tag="child")
        
        parent.add_child(child)
        self.assertEqual(len(parent.children), 1)
        self.assertEqual(parent.children[0], child)

        # Add another child
        child2 = MuleFlowElement(tag="child2")
        parent.add_child(child2)
        self.assertEqual(len(parent.children), 2)
        self.assertEqual(parent.children[1], child2)

    def test_set_note(self):
        """Test setting notes"""
        element = MuleFlowElement(tag="test-tag")
        test_note = "This is a test note"
        
        element.set_note(test_note)
        self.assertEqual(element.notes, test_note)

        # Test updating existing note
        new_note = "Updated note"
        element.set_note(new_note)
        self.assertEqual(element.notes, new_note)

    def test_set_error_handler_ref(self):
        """Test setting error handler reference"""
        element = MuleFlowElement(tag="test-tag")
        error_ref = "test-error-handler"
        
        element.set_error_handler_ref(error_ref)
        self.assertEqual(element.error_handler_ref, error_ref)

        # Test updating existing error handler ref
        new_error_ref = "new-error-handler"
        element.set_error_handler_ref(new_error_ref)
        self.assertEqual(element.error_handler_ref, new_error_ref)

    def test_get_flows_no_name(self):
        """Test getting all flows when no specific name is provided"""
        root = MuleFlowElement(tag="mule")
        flow1 = MuleFlowElement(tag="flow", attributes={"name": "flow1"})
        flow2 = MuleFlowElement(tag="flow", attributes={"name": "flow2"})
        non_flow = MuleFlowElement(tag="logger")
        
        root.add_child(flow1)
        root.add_child(non_flow)
        root.add_child(flow2)

        flows = root.get_flows()
        self.assertEqual(len(flows), 2)
        self.assertEqual(flows[0], flow1)
        self.assertEqual(flows[1], flow2)

    def test_get_flows_with_name(self):
        """Test getting a specific flow by name"""
        root = MuleFlowElement(tag="mule")
        flow1 = MuleFlowElement(tag="flow", attributes={"name": "flow1"})
        flow2 = MuleFlowElement(tag="flow", attributes={"name": "flow2"})
        
        root.add_child(flow1)
        root.add_child(flow2)

        # Test finding existing flow
        flows = root.get_flows("flow1")
        self.assertEqual(len(flows), 1)
        self.assertEqual(flows[0], flow1)

        # Test with non-existent flow name
        flows = root.get_flows("non-existent")
        self.assertEqual(len(flows), 0)

    def test_get_flows_with_invalid_children(self):
        """Test getting flows when there are invalid children elements"""
        root = MuleFlowElement(tag="mule")
        flow1 = MuleFlowElement(tag="flow", attributes={"name": "flow1"})
        
        # Add a valid flow and an invalid child
        root.children.append(flow1)
        root.children.append(None)  # Invalid child

        flows = root.get_flows()
        self.assertEqual(len(flows), 1)
        self.assertEqual(flows[0], flow1)

if __name__ == '__main__':
    unittest.main()


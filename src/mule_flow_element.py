from typing import Dict, List, Optional

class MuleFlowElement:
        
    def __init__(self, 
                 tag: str, 
                 attributes: Dict[str, str] = None, 
                 children: List['MuleFlowElement'] = None, 
                 processes: List['MuleFlowElement'] = None, 
                 content: str = "",
                 notes: str = "", 
                 standalone: bool = True, 
                 error_handler_ref: Optional[str] = None,
                 error_handler_element: Optional[List['MuleFlowElement']] = None):
        self.tag = tag
        self.attributes = attributes or {}
        
        self.children = children or []
        self.processes = processes or []
        self.content = content
        print(f"Processing {self.tag}")

        self.notes = notes
        self.standalone = standalone
        self.error_handler_ref = error_handler_ref
        self.error_handler_element = error_handler_element

    def __str__(self):
        # A Case Statement to handle stringifying the tag based on the key attributes of the element
        # Defaults to name if no other identifier is found
        # Extend as needed
        if self.tag == 'set-variable':
            identifier = self.attributes.get('variableName') or ''
        elif self.tag in ['on-error-propagate', 'on-error-continue']:
            identifier = self.attributes.get('when') or self.attributes.get('type') or '' 
        else:
            identifier = self.attributes.get('name') or self.attributes.get('documentation:name') or ''
        return f"{self.tag} [{identifier}]" if identifier else self.tag

    def add_child(self, child: 'MuleFlowElement'):
        self.children.append(child)

    def set_note(self, note: str):
        self.notes = note

    def set_error_handler_ref(self, ref: str):
        self.error_handler_ref = ref

    """
    Get all flows in the current element
    If flow_name is provided, return only the flow with that name
    """
    def get_flows(self, flow_name: str = None) -> List['MuleFlowElement']:
        flows = []
        for child in self.children:
            if child.tag in ['flow']:
                if flow_name is None or child.attributes.get('name') == flow_name:
                    flows.append(child)
        return flows
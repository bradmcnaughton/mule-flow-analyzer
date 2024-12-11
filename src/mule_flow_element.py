from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

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
        try:
            if not tag:
                raise ValueError("Tag cannot be empty or None")
            
            self.tag = tag
            self.attributes = attributes or {}
            self.children = children or []
            self.processes = processes or []
            self.content = content
            
            logger.debug(f"Processing {self.tag}")
            
            self.notes = notes
            self.standalone = standalone
            self.error_handler_ref = error_handler_ref
            self.error_handler_element = error_handler_element

        except Exception as e:
            logger.error(f"Error initializing MuleFlowElement: {str(e)}")
            raise

    def __str__(self):
        try:
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
            
        except Exception as e:
            logger.error(f"Error converting MuleFlowElement to string: {str(e)}")
            return f"<Error: {self.tag}>"

    def add_child(self, child: 'MuleFlowElement'):
        try:
            if not isinstance(child, MuleFlowElement):
                raise TypeError(f"Child must be a MuleFlowElement, not {type(child)}")
            
            self.children.append(child)
            logger.debug(f"Added child {child.tag} to {self.tag}")
            
        except Exception as e:
            logger.error(f"Error adding child to {self.tag}: {str(e)}")
            raise

    def set_note(self, note: str):
        try:
            if not isinstance(note, str):
                raise TypeError(f"Note must be a string, not {type(note)}")
            
            self.notes = note
            logger.debug(f"Set note for {self.tag}")
            
        except Exception as e:
            logger.error(f"Error setting note for {self.tag}: {str(e)}")
            raise

    def set_error_handler_ref(self, ref: str):
        try:
            if not isinstance(ref, str):
                raise TypeError(f"Error handler reference must be a string, not {type(ref)}")
            
            self.error_handler_ref = ref
            logger.debug(f"Set error handler reference for {self.tag}")
            
        except Exception as e:
            logger.error(f"Error setting error handler reference for {self.tag}: {str(e)}")
            raise

    def get_flows(self, flow_name: str = None) -> List['MuleFlowElement']:
        """
        Get all flows in the current element
        If flow_name is provided, return only the flow with that name
        """
        try:
            flows = []
            for child in self.children:
                try:
                    if child.tag in ['flow']:
                        if flow_name is None or child.attributes.get('name') == flow_name:
                            flows.append(child)
                except AttributeError as e:
                    logger.warning(f"Invalid child element while getting flows: {str(e)}")
                    continue
            
            if flow_name and not flows:
                logger.warning(f"No flow found with name: {flow_name}")
                
            return flows
            
        except Exception as e:
            logger.error(f"Error getting flows from {self.tag}: {str(e)}")
            return []
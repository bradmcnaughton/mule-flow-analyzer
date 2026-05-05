import os
import re
import logging
import traceback
import shutil
import subprocess
from typing import Dict, List, Optional, Tuple, Any
from .mule_flow_element import MuleFlowElement
from ..exceptions import ConfigurationError, RenderingError, DiagramGenerationException

logger = logging.getLogger(__name__)

# Re-export for callers that imported these from this module
DiagramGenerationError = DiagramGenerationException

CONTROL_FLOW_TAGS = ['choice', 'foreach', 'parallel-foreach', 'round-robin', 'scatter-gather', 'until-successful', 'first-successful']
CONTROL_FLOW_BOUNDARY_TAGS = ['flow-ref', 'when', 'otherwise', 'on-error-propagate', 'on-error-continue', 'route']
LOGGING_PROCESSORS = ['logger', 'tracing:set-logging-variable']

class ArrowType:
    def __init__(self, label: str, arrow: str, priority: int):
        self.label = label
        self.arrow = arrow 
        self.priority = priority

class SequenceDiagramGenerator:
    def __init__(self, configuration_properties: Dict[str, Any]) -> None:
        if not configuration_properties:
            raise ConfigurationError("Configuration properties cannot be empty")
        
        required_keys = ['diagram_formatting_properties', 'analyzer_properties']
        missing_keys = [key for key in required_keys if key not in configuration_properties]
        if missing_keys:
            raise ConfigurationError(f"Missing required configuration keys: {missing_keys}")

        self.properties = configuration_properties

        self.mule_box_format = f"box #{self.properties['diagram_formatting_properties']['mule']['box-color']}"
        self.skinparam_options = self.properties['diagram_formatting_properties']['skinparam']
        self.arrow_legend = {}
        
    def add_arrow_to_legend(self, arrow_type: str, label: Optional[str]) -> None:
        
        high_priority_arrows = ['->']
        
        if arrow_type not in self.arrow_legend.keys():
            if arrow_type in high_priority_arrows:
                priority = 0
            else:
                priority = len(self.arrow_legend) + 1

            label = label if label else next((k.capitalize() for k, v in self.properties['diagram_formatting_properties']['arrows'].items() if v == arrow_type), arrow_type)

            self.arrow_legend[arrow_type] = ArrowType(
                label=label,
                arrow=arrow_type,
                priority=priority
            )

    def remove_expression_brackets(self, input_string: str) -> str:
        """
        Remove the Dataweave expression brackets from the string
        """
        if input_string.startswith('#[') and input_string.endswith(']'):
            return input_string[2:-1]
        else:
            return input_string

    def clean_uml_note(self, input_string:str) -> str:
        # Escape any double quotes and convert line breaks to \n
        return input_string.replace('"', '\\"').replace('\n', '\\n')

    def clean_uml_syntax(self, input_string:str):
        cleaned_string = input_string.replace("\"", "").replace(" [", "\\n[")
        if cleaned_string:
            return f"\"{cleaned_string}\""
        else:
            return ""

    def clean_uml_alias(self, input_string:str):
        # Remove special characters for PlantUML Aliases (:,-,spaces, quotes)
        return input_string.replace(":", "").replace("-", "").replace(" ", "").replace("\"", "")
    
    def clean_config_ref(self, input_string: str) -> str:
        """
        Attempt to convert a config reference into a description of the source/target
        """
        # Uppercase the input_string
        #input_string = input_string.upper()

        # Remove common prefixes and suffixes
        cleaned_string = re.sub(r'^(CONFIG_|DB_|DATABASE_|HTTP_|CONFIGURATION_|SALESFORCE_)', '', input_string, flags=re.IGNORECASE)
        cleaned_string = re.sub(r'(_CONFIG|_DB|_DATABASE|_HTTP|_CONFIGURATION|_SALESFORCE)$', '', cleaned_string, flags=re.IGNORECASE)

        # Replace hyphens, dashes, and underscores with spaces
        cleaned_string = re.sub(r'[-–—_]', ' ', cleaned_string)

        # Remove any remaining instances of "CONFIG", "DB", "DATABASE", "CONFIGURATION", "HTTP", or "SALESFORCE"
        cleaned_string = re.sub(r'\b(CONFIG|DB|DATABASE|CONFIGURATION|HTTP|SALESFORCE)\b', '', cleaned_string, flags=re.IGNORECASE)

        # Ensure spaces are maximum one space and strip leading/trailing spaces
        cleaned_string = re.sub(r'\s+', ' ', cleaned_string).strip()

        return cleaned_string

    def pretty_participant(self, element: MuleFlowElement, source_or_target: str = "source") -> Tuple[Optional[str], Optional[str], str]:
        """
        Formats a Mule flow element as a PlantUML participant.

        Args:
            element: The Mule flow element to format
            source_or_target: Whether this is a source or target element ("source" or "target")

        Returns:
            Tuple containing:
            - alias: The participant alias (or None)
            - description: The participant description (or None)
            - class_name: The participant class name

        Raises:
            ValueError: If source_or_target is not "source" or "target"
        """
        
        def alias_from_config_ref(element:MuleFlowElement):
            config_ref = element.attributes.get('config-ref', None)
            if config_ref:
                return self.clean_config_ref(config_ref)
            else:
                return self.clean_uml_alias(element.tag.split(":")[0])

        alias, description, class_name = None, None, "participant"
        if element.tag == 'scheduler':
            # clock
            alias = "Scheduler"
            description = "Scheduled Task"
            class_name = "scheduler"
        elif 'listener' in element.tag or 'subscriber' in element.tag or source_or_target == "target":
            if element.tag.startswith('db'):
                # database row
                if 'config-ref' in element.attributes.keys():
                    # DB Names use uppercase
                    db_name = self.clean_config_ref(element.attributes.get('config-ref')).upper()
                else:
                    db_name = None
                alias = f"Database\\n{db_name}".strip()
                description = f"Database Change: ({(element.tag.split(':')[-1]).replace('-', ' ').capitalize()})"
                class_name = "database"
            elif element.tag.startswith('http'):
                # web   
                if source_or_target=='target' and 'config-ref' in element.attributes.keys():
                    http_name = self.clean_config_ref(element.attributes.get('config-ref'))
                else:
                    http_name = None
                alias = ' '.join(filter(None, ['HTTP', http_name])).strip()

                if 'method' in element.attributes.keys():
                    http_method = element.attributes.get('method')
                else:
                    http_method = None

                if 'path' in element.attributes.keys():
                    http_path = element.attributes.get('path')
                else:
                    http_path = None
                if http_path or http_method:
                    description = f"HTTP Request: ({' '.join(filter(None, [http_method, http_path])).strip()})" 
                else:
                    description = f"HTTP Request ({(element.tag.split(':')[-1]).replace('-', ' ').capitalize()})"
                class_name = "http"
            elif element.tag.startswith('email'):
                # email
                alias = alias_from_config_ref(element)
                description = "Email Message"
                class_name = "email"
            elif element.tag.startswith('sockets'):
                # sockets
                alias = alias_from_config_ref(element)
                description = "Socket Connection"
                class_name = "socket"
            elif element.tag.startswith('sftp') or element.tag.startswith('file'):
                # file  
                alias = alias_from_config_ref(element)
                description = f"File Transfer: ({(element.tag.split(':')[-1]).replace('-', ' ').capitalize()})"
                class_name = "file"
            elif element.tag.startswith('jms') or element.tag.startswith('vm') or element.tag.split(":")[0].endswith("mq"):               
                # queue
                # destination (ibmmq, anypointmq, jms) or queueName (vm)
                if 'destination' in element.attributes.keys():
                    queue_name = element.attributes.get('destination')
                elif 'queueName' in element.attributes.keys():
                    queue_name = element.attributes.get('queueName')
                else:
                    queue_name = None
                if queue_name:
                    alias = f"Queue\\n{queue_name}"
                    description = f"Message ({queue_name})"
                else:
                    alias = "Queue"
                    description = "Message"
                class_name = "queue"
            elif element.tag.startswith('salesforce'):
                # Salesforce
                alias = alias_from_config_ref(element)
                description = f"{element.tag.split(':')[1]}"
                class_name = "salesforce"
            elif ":" in element.tag:
                if element.tag.split(":")[0] in self.properties['diagram_formatting_properties']['actors'].keys():
                    class_name = element.tag.split(":")[0]
                    alias = alias_from_config_ref(element)
                    description = f"{element.tag.split(':')[1]}"
                elif element.tag.split(":")[0] not in self.properties['analyzer_properties']['tag_rules']['internal_targets']:
                    # External Processor
                    class_name = "http"
                    alias = alias_from_config_ref(element)
                    description = f"{element.tag.split(':')[1]}"

        return alias, description, class_name

    def attributes_to_activities(self, element:MuleFlowElement, activities:list, process_prefix:str=None) -> list:
        if len(element.attributes) > 0:
            # Attributes of the XML are mapped to activities
            for key, value in element.attributes.items():
                if process_prefix:
                    key = f"{process_prefix}.{key}"
                activities.append(f"{key}: {value}")
        else:
            if element.content:
                # Tag of the XML represents the activity
                label = element.tag.split(":")[-1].replace('-', ' ')
                if process_prefix:
                    label = f"{process_prefix}.{label}"
                activities.append(label)

        # Add the children process tags as well
        if len(element.processes) > 0:
            process_prefix = element.tag.split(":")[-1]
            for child_process in element.processes:
                activities = self.attributes_to_activities(child_process, activities, process_prefix)
            
        return activities

    def generate_sequence_diagram_syntax(self, flow:MuleFlowElement):
        
        def sequence_line_formatter(source_actor, target_actor, description=None, arrow_style="->", tracking_vars:dict=None):
            cleaned_source_actor = self.clean_uml_syntax(source_actor) if source_actor else "" 
            cleaned_target_actor = self.clean_uml_syntax(target_actor) if target_actor else ""
            
            arrow_label = None
            
            # Description should not need to be quoted
            cleaned_description = description if description else ""
            
            # inject colour into arrows depending on the tracking vars
            if tracking_vars and 'transaction_stack' in tracking_vars.keys() and len(tracking_vars['transaction_stack']) > 0:
                arrow_colour = f"[#{self.properties['diagram_formatting_properties']['transactions']['arrows'][len(tracking_vars['transaction_stack'])]}]"
            else:
                arrow_colour = ""

            # insert arrow color into the arrow provided:
            # Logic handles all types of PlantUML arrows
            if arrow_colour:
                if arrow_style[1] == "<":
                    arrow_style = f"{arrow_style[:2]}{arrow_colour}{arrow_style[2:]}"
                else:
                    arrow_style = f"{arrow_style[0]}{arrow_colour}{arrow_style[1:]}"
                       
            if tracking_vars and 'create_mode' in tracking_vars.keys() and tracking_vars['create_mode'] and cleaned_source_actor != cleaned_target_actor :
                mode_string = "** "
            else:
                mode_string = ""
            
            self.add_arrow_to_legend(arrow_style, arrow_label)

            return f"{cleaned_source_actor} {arrow_style} {cleaned_target_actor} {mode_string}: {cleaned_description}"
        
        def record_actor(actor, actors_stack, actor_class:str="participant", relative_position:str="mule", sub_label:str=None) -> list:
            def format_actor(actor, actor_class):
                actor_size = 56
                actor_prefix = actor.split(":")[0].lower()
                local_sub_label = sub_label

                if not local_sub_label:
                    if (actor_class == "http" and actor != "HTTP") or actor_class in self.properties['diagram_formatting_properties']['actors'].keys():
                        local_sub_label = actor
                
                if local_sub_label:
                    actor_size = 30

                # Switch the actor name to get the right UML participant type
                if actor_class == "queue":
                    actor_class = "queue"
                elif actor_class == "database":
                    actor_class = "database"
                elif actor_class in self.properties['diagram_formatting_properties']['actors'].keys():
                    actor_class = f"participant \"<size:{actor_size}>{self.properties['diagram_formatting_properties']['actors'].get(actor_class, actor_class)}\" as"

                # sub labels only apply to participants with as
                # This is how an Icon gets a label underneath it
                if local_sub_label and actor_class and actor_class.endswith("as"):
                    actor_class = f"{actor_class[:-4]}\\n{local_sub_label}{actor_class[-4:]}"

                if actor_class and actor_class.endswith("as"):
                    return f"{actor_class} {actor}"
                else:   
                    return f"{actor_class} {self.clean_uml_syntax(actor)}"
            
            formatted_actor = format_actor(actor, actor_class)
            if formatted_actor not in actors_stack:
                if relative_position == "mule":
                    actors_stack.insert(actors_stack.index('end box'), formatted_actor)
                elif relative_position == "source":
                    actors_stack.insert(actors_stack.index(self.mule_box_format), formatted_actor)
                elif relative_position == "target":
                    actors_stack.append(formatted_actor)
            
            return actors_stack

        def process_element(element:MuleFlowElement, content:list, tracking_vars:dict):
            logger.debug(f"Creating UML content for {element.tag}")
            
            transactions_success_list = ['flow', 'try', 'on-error-continue']
            transactions_failure_list = ['on-error-propagate', 'raise-error']

            skip_end_group = False

            # Opening Element Checks
            if element.tag in ['flow', 'sub-flow']:
                if not content[-1].startswith("title"):
                    content.append(f"group {element.tag} {element.attributes.get('name')}")
                else:
                    skip_end_group = True
            elif element.tag in ['choice', 'round-robin']:
                # Do alt branches
                tracking_vars['choice_stack'].append(element.children)
                
                choice_opened = False
                choice_previous_actor = tracking_vars['previous_actor']
                
                # Group is implicitly created by the first choice "alt" and subsequent choices are "else"
                for choice in tracking_vars['choice_stack'][len(tracking_vars['choice_stack'])-1]:
                    if not choice_opened:
                        if element.tag == 'round-robin':
                            content.append(f"alt Round Robin First Target")
                            content.append(f"note over {self.clean_uml_syntax(tracking_vars['current_actor'])}: {element.attributes.get('documentation:name', 'Round Robin')}")
                        else:
                            content.append(f"alt {self.remove_expression_brackets(choice.attributes.get('expression',''))}")
                        choice_opened = True
                        content = process_element(choice, content, tracking_vars)
                    else:
                        if element.tag == 'round-robin':
                            content.append(f"else Round Robin Next Target")
                        else:
                            content.append(f"else {self.remove_expression_brackets(choice.attributes.get('expression', 'else'))}")
                        content = process_element(choice, content, tracking_vars)
                    # Reset the previous actor to the choice actor
                    
                    tracking_vars['previous_actor'] = choice_previous_actor
                
            elif element.tag in ['foreach', 'until-successful', 'parallel-foreach']:
                # Track the loop event source
                tracking_vars['loop_event_source'] = element
                                              
                for item in element.children:
                    content = process_element(item, content, tracking_vars)
            elif element.tag in ['scatter-gather', 'first-successful']:
                # Track the parallel event source
                tracking_vars['parallel_sources'] = []
                local_parallel_sources = []
                parallel_previous_actor = tracking_vars['previous_actor']

                content.append(f"par {element.attributes.get('documentation:name', element.tag)}")
                if element.tag == 'first-successful':
                    content.append(f"note over {self.clean_uml_syntax(tracking_vars['previous_actor'])} : First Successful Will Be Used")
                routes_opened = False

                # Process the children (route tags)
                for route in element.children:
                    if routes_opened:
                        content.append("else")
                        
                    for child in route.children:
                        content = process_element(child, content, tracking_vars)

                    # Open Routes (to trigger "else" syntax)
                    routes_opened = True
                    # Keep track of the last actor of each route to be used as the previous actor for the consolidating route
                    local_parallel_sources.append(tracking_vars['previous_actor'])
                    # Reset the previous actor to the parallel source for any future loops
                    tracking_vars['previous_actor'] = parallel_previous_actor
                
                # Add the parallel sources consolidating
                tracking_vars['parallel_sources'] = local_parallel_sources
            
            elif element.tag == 'async':
                # Don't create a participant for async, show the async processors instead
                # Set tracking to NEW so it will trigger the async start (different arrow)
                tracking_vars['async_source'] = str(element.tag)
                async_previous_actor = tracking_vars['previous_actor']
                
                if self.properties['diagram_formatting_properties']['async']['note']:
                    # Append the async start Note
                    content.append(f"note over {self.clean_uml_syntax(tracking_vars['previous_actor'])} #{self.properties['diagram_formatting_properties'].get('async', {}).get('background-color', 'transparent')}: Async Start")
                if self.properties['diagram_formatting_properties']['async']['group']:
                    # Wrap the async in a group
                    content.append(f"group #{self.properties['diagram_formatting_properties']['async'].get('background-color', 'transparent')} async")
            elif element.tag == 'try':
                content.append(f"alt#{self.properties['diagram_formatting_properties']['try']['label-color']} #{self.properties['diagram_formatting_properties']['try']['background-color']} {element.attributes.get('documentation:name', 'Try')}")
            elif element.tag.split(':')[0] == 'batch':
                # Batch Branch Grouping
                if element.tag == 'batch:job' and self.properties['diagram_formatting_properties']['batch']['job']['group']:
                    content.append(f"group #{self.properties['diagram_formatting_properties']['batch']['job'].get('background-color', 'transparent')} Batch Job {element.attributes.get('jobName', '')}")
                elif element.tag == 'batch:process-records' and self.properties['diagram_formatting_properties']['batch']['process-records']['group']:
                    content.append(f"group #{self.properties['diagram_formatting_properties']['batch']['process-records'].get('background-color', 'transparent')} Batch Process Records")
                elif element.tag == 'batch:step' and self.properties['diagram_formatting_properties']['batch']['step']['group']:
                    content.append(f"group #{self.properties['diagram_formatting_properties']['batch']['step'].get('background-color', 'transparent')} Batch Step {element.attributes.get('name', '')}, Accept Policy: {element.attributes.get('acceptPolicy', 'NO_FAILURES')}")
                elif element.tag == 'batch:aggregator' and self.properties['diagram_formatting_properties']['batch']['aggregator']['group']    :
                    content.append(f"group #{self.properties['diagram_formatting_properties']['batch']['aggregator'].get('background-color', 'transparent')} Batch Aggregator {element.attributes.get('name', '')}")
                elif element.tag == 'batch:on-complete' and self.properties['diagram_formatting_properties']['batch']['on-complete']['group']:
                    content.append(f"group #{self.properties['diagram_formatting_properties']['batch']['on-complete'].get('background-color', 'transparent')} Batch On Complete")
            elif element.tag == 'ee:cache':
                tracking_vars['cache_source'] = self.clean_uml_syntax(tracking_vars['current_actor'])
                content.append(f"alt Cache Miss")
                if element.attributes.get('documentation:name', 'Cache') != 'Cache':
                    # Add a note matching the customised cache scope name
                    content.append(f"note over {self.clean_uml_syntax(tracking_vars['current_actor'])}: {element.attributes.get('documentation:name')}")

            #--------------------------------------------------------------------------------------------
            # General Handling for all elements and processors that do something in the flow rather than controlling it
            #--------------------------------------------------------------------------------------------
            elif element.tag not in CONTROL_FLOW_BOUNDARY_TAGS and (element.tag not in LOGGING_PROCESSORS or self.properties['diagram_formatting_properties']['verbose']['logging']):  
                # Default arrow style, Can be overridden by async or transaction
                arrow_style=self.properties['diagram_formatting_properties']['arrows']['flow']
                
                # Previous actor is calling this element (may be self)
                tracking_vars['current_actor'] = str(element)
                tracking_vars['actors_stack'] = record_actor(tracking_vars['current_actor'], tracking_vars['actors_stack'], relative_position="mule")
                # Store the previous actor for the response line
                previous_actor = tracking_vars['previous_actor']
                
                # Check if element is start of a loop by finding a loop element in the loop_event_source
                if tracking_vars['loop_event_source']:
                    loop_element = tracking_vars['loop_event_source']
                    # Handle format for various types of loops
                    if loop_element.tag in ['foreach', 'parallel-foreach']:
                        content.append(f"loop {loop_element.attributes.get('documentation:name')}\\nCollection: {loop_element.attributes.get('collection', '')}")
                    elif loop_element.tag == 'until-successful':
                        until_successful_statement = "loop "
                        if 'until successful' in loop_element.attributes.get('documentation:name', '').lower(): 
                            until_successful_statement += loop_element.attributes.get('documentation:name')
                        else:
                            until_successful_statement += "Until Successful - " + loop_element.attributes.get('documentation:name')
                        
                        if loop_element.attributes.get('maxRetries', None):
                            until_successful_statement += f" max retries: {loop_element.attributes.get('maxRetries')}"
                        content.append(until_successful_statement)
                            
                    # Unset the loop event source
                    tracking_vars['loop_event_source'] = None

                # check if element is inside an async process
                if tracking_vars['async_source']:
                    arrow_style=self.properties['diagram_formatting_properties']['arrows']['async']
                    tracking_vars['async_source'] = None

                # Check if element is starting a transaction
                if element.attributes.get('transactionalAction', None):
                    # New Transaction
                    if element.attributes.get('transactionalAction') == 'ALWAYS_BEGIN' or \
                        (element.attributes.get('transactionalAction') == 'BEGIN_OR_JOIN' and len(tracking_vars['transaction_stack']) == 0):
                        # TODO: Handle local transactions having ALWAYS_BEGIN when an existing transaction is already in progress
                        # (That should be an error)
                        tracking_vars['transaction_stack'].append(element.attributes.get('transactionType', None))
                        content.append(f"note right of {self.clean_uml_syntax(tracking_vars['current_actor'])} #{self.properties['diagram_formatting_properties']['transactions']['arrows'][len(tracking_vars['transaction_stack'])]} : {element.attributes.get('transactionType', None)} Transaction Starting")

                
                # Append the incoming call line ----------------------------->
                # (Skip if event source)
                if not tracking_vars['event_source'] and len(tracking_vars['parallel_sources']) == 0:                                   
                    content.append(sequence_line_formatter(previous_actor, tracking_vars['current_actor'], arrow_style=arrow_style, tracking_vars=tracking_vars))
                elif len(tracking_vars['parallel_sources']) > 0:
                    # Add the parallel sources consolidating
                    for parallel_source in tracking_vars['parallel_sources']:
                        content.append(sequence_line_formatter(parallel_source, tracking_vars['current_actor'], arrow_style=self.properties['diagram_formatting_properties']['arrows']['parallel'], tracking_vars=tracking_vars))
                    # Clear tracking_vars['parallel_sources']
                    tracking_vars['parallel_sources'] = []

                # Manage Errors
                if element.error_handler_ref:
                    # Change to new/updated error handler reference
                    tracking_vars['error_handler_ref'] = element.error_handler_ref

                # Check if element is raising an error and note the error handler
                if element.tag == 'raise-error':
                    note = f"note over {self.clean_uml_syntax(tracking_vars['current_actor'])} #{self.properties['diagram_formatting_properties'].get('errors', {}).get('color', 'transparent')}: Raising Error:\\n{element.attributes.get('type', 'Missing Error Type')}"
                    if tracking_vars['error_handler_ref']:
                        note += f"\\n\\nError Handler:\\n{tracking_vars['error_handler_ref']}"
                    else:
                        note += f"\\n\\nNo Error Handler Defined"
                    content.append(note)

                # Add any documentation as a note above.
                if self.properties['diagram_formatting_properties']['verbose']['notes']:
                    if element.attributes.get('documentation:description', None):
                        content.append(f"note over {self.clean_uml_syntax(tracking_vars['current_actor'])}: { self.clean_uml_note(element.attributes.get('documentation:description')) }")
                
                # Add the internal workings of the processor
                if len(element.processes) > 0:
                    # Append the internal workings of the processor as actions on itself
                    activities = []
                    for process in element.processes:
                        activities = self.attributes_to_activities(process, activities, process_prefix=element.tag.split(":")[-1])

                    for activity in activities:
                        content.append(sequence_line_formatter(tracking_vars['current_actor'], tracking_vars['current_actor'], activity, arrow_style=arrow_style, tracking_vars=tracking_vars))
                    
                if not tracking_vars['event_source']:
                    
                    # Check if we should add a target side actor  -----------------------------> 0
                    # (Downstream System)                         <----------------------------- 0
                     
                    target_alias, target_description, target_class_name = self.pretty_participant(element, source_or_target="target")
                    if target_alias:
                        # Aliases can't have spaces in plantuml so we will keep only first word as the alias and the rest as a sub label
                        if ' ' in target_alias:
                            # For extra niceness, remove the class name from the sub label as it's implicit in the icon
                            target_alias_sub_label = target_alias
                            if target_class_name.lower() in target_alias.lower():
                                target_alias_sub_label = ' '.join(word for word in target_alias.split() if word.lower() not in target_class_name.lower().split())
                            target_alias_sub_label = target_alias_sub_label.strip()
                            target_alias = target_alias.split(' ')[0]
                        else:
                            target_alias_sub_label = None

                        # Handle duplicate aliases
                        if tracking_vars['alias_reference'].get(str(element), None):
                            # Element is already in the alias reference
                            target_alias = tracking_vars['alias_reference'][str(element)]
                        else:
                            # Element is not in the alias reference, so it will be added
                            if any(target_alias == value for value in tracking_vars['alias_reference'].values()):
                                # Alias is already in use, so we need to make it unique, check if it shares the same config-ref
                                if element.attributes.get('config-ref', None) and tracking_vars['alias_config_reference'].get(element.attributes.get('config-ref', None), None):
                                    target_alias = tracking_vars['alias_config_reference'][element.attributes.get('config-ref', None)]
                                else:
                                    target_alias = f"{target_alias}_{len(tracking_vars['alias_reference'])}"
                                                                               
                            tracking_vars['alias_reference'][str(element)] = target_alias
                            # And add it to the config reference
                            if element.attributes.get('config-ref', None):
                                if not tracking_vars['alias_config_reference'].get(element.attributes.get('config-ref', None), None):
                                    tracking_vars['alias_config_reference'][element.attributes.get('config-ref', None)] = target_alias
 
                        tracking_vars['actors_stack'] = record_actor(tracking_vars['alias_reference'].get(str(element), target_alias), tracking_vars['actors_stack'], target_class_name, relative_position="target", sub_label=target_alias_sub_label)
                        
                        # Outbound line to external target ---------------------> 0
                        content.append(sequence_line_formatter(
                            tracking_vars['current_actor'],
                            tracking_vars['alias_reference'].get(str(element),target_alias),
                            target_description,
                            arrow_style=arrow_style,
                            tracking_vars=tracking_vars
                        ))

                        # Return line to the current actor <-------------------- 0
                        content.append(sequence_line_formatter(
                            tracking_vars['alias_reference'].get(str(element), target_alias),
                            tracking_vars['current_actor'],
                            None,
                            arrow_style=self.properties['diagram_formatting_properties']['arrows']['return'],
                            tracking_vars=tracking_vars
                        ))

                else:
                    # Set it to None to track we are past the event source
                    tracking_vars['event_source'] = None
                        
                # Update the previous actor for children
                tracking_vars['previous_actor'] = tracking_vars['current_actor']

            # Recursively process children (unless already done in a control flow)
            if element.tag not in CONTROL_FLOW_TAGS:
                for child in element.children:
                    content = process_element(child, content, tracking_vars)

            # Closing Element Checks
            # Ending a Transaction
            if len(tracking_vars['transaction_stack']) > 0 and element.tag in transactions_success_list + transactions_failure_list:
                if element.tag in transactions_success_list:
                    content.append(f"note right of {self.clean_uml_syntax(tracking_vars['current_actor'])}  #{self.properties['diagram_formatting_properties']['transactions']['arrows'][len(tracking_vars['transaction_stack'])]}: {tracking_vars['transaction_stack'][-1]} Transaction End")
                else:
                    content.append(f"note right of {self.clean_uml_syntax(tracking_vars['current_actor'])}  #{self.properties['diagram_formatting_properties']['transactions']['arrows'][len(tracking_vars['transaction_stack'])]}: \"{tracking_vars['transaction_stack'][-1]} Transaction Failure\"")
                tracking_vars['transaction_stack'].pop()
            
            # Ending a Group
            if not skip_end_group and element.tag in (['flow', 'sub-flow'] + CONTROL_FLOW_TAGS):
                content.append("end")
            else:
                # Response line
                #content.append(sequence_line_formatter(str(element), previous_actor, "return", arrow_style="-->"))
                pass

            # Ending an Async
            if element.tag == 'async':
                # Ensure the previous actor is set back to the async executor
                tracking_vars['previous_actor'] = async_previous_actor
                if self.properties['diagram_formatting_properties']['async']['group']:
                    content.append("end")

            # Ending any kind of Batch Job group
            if element.tag in ['batch:job', 'batch:process-records', 'batch:on-complete', 'batch:step', 'batch:aggregator']:
                if self.properties['diagram_formatting_properties']['batch'][element.tag.split(':')[1]]['group']:
                    content.append("end")

            # Ending a Cache
            if element.tag == 'ee:cache':
                content.append("else Cache Hit")
                content.append(sequence_line_formatter(tracking_vars['cache_source'], tracking_vars['current_actor'], 'Use Cached Value', arrow_style=self.properties['diagram_formatting_properties']['arrows']['flow'], tracking_vars=tracking_vars))
                content.append("end")
                tracking_vars['cache_source'] = None

            # Ending a Try
            elif element.tag == 'try':
                content.append(f"else Error Handling")
                if self.properties['diagram_formatting_properties']['verbose']['errors']:
                    # Track the last actor before the error handler
                    try_previous_actor = tracking_vars['previous_actor']
                    # Add the error handler's processors
                    if element.error_handler_element and len(element.error_handler_element.children) > 0:
                        # Inject the inline error handler processors into the content
                        # Always use create mode for error handlers
                        tracking_vars['create_mode'] = True
                        # Use an alt to track multiple error handler options
                        if len(element.error_handler_element.children) > 0:
                            do_alt = True
                        else:
                            do_alt = False  
                        alt_count = 0
                        
                        if do_alt:
                            content.append(f"alt#{self.properties['diagram_formatting_properties'].get('errors', {}).get('color', 'transparent')} {str(element.error_handler_element.children[0])}")
                            alt_count = 1
                        
                        for child in element.error_handler_element.children:
                            # Each error handler will originate from the last actor before the error handler
                            tracking_vars['previous_actor'] = try_previous_actor
                            
                            if do_alt:
                                if alt_count > 1:
                                    content.append(f"else {str(child)}")
                                alt_count += 1
                            
                            content = process_element(child, content, tracking_vars)

                        if do_alt:
                            content.append("end")

                        # Reset the create mode to the global setting
                        tracking_vars['create_mode'] = self.properties['diagram_formatting_properties']['create_mode']
                    # Reset the previous actor to the last actor before the error handler
                    tracking_vars['previous_actor'] = try_previous_actor
                else:
                    content.append(f"note over {self.clean_uml_syntax(tracking_vars['current_actor'])} #{self.properties['diagram_formatting_properties'].get('errors', {}).get('color', 'transparent')}: {element.error_handler_ref}")
                # End the Try Catch
                content.append("end")

            return content

        # Initialize tracking variables
        tracking_vars = {
            'previous_actor': None,
            'current_actor': "[",
            'transaction_stack': [],
            'actors_stack': [self.mule_box_format, "end box"],
            'event_source': None,
            'event_targets': [],
            'choice_stack': [],
            'alias_reference': {},
            'alias_config_reference': {}, # Used to group aliases that share the same config-ref
            'error_handler_ref': flow.error_handler_ref if flow.error_handler_ref else None,
            'loop_event_source': None,
            'parallel_sources': [],
            'async_source': None,
            'cache_source': None,
            'create_mode': self.properties['diagram_formatting_properties']['create_mode'] # If true, will prefix actors with ** to create them if they don't already exist
        }

        # The content list will be used to build the diagram syntax
        content = []
        content.append("@startuml")

        # Define scaling
        content.append(self.properties['diagram_formatting_properties']['scale'])
               
        if self.skinparam_options:
            content.append("'start formatting")
            content += self.skinparam_options
            content.append("'end formatting")

        # insert participants placeholder
        # it will later be replaced by the participants
        content.append("##PP##")

        # Determine the Event Source
        # Check for APIKit flows and manually set the event source alias for APIKit
        if flow.attributes['name'] and re.match(r'^(get|put|post|patch|delete|options):\\', flow.attributes['name'], re.IGNORECASE):
            logging.debug(f"Setting event source alias for APIKit flow: {flow.attributes['name']}")
            event_source = 'apikit'
            event_source_alias, event_source_description, event_source_class_name = 'apikit', 'APIKit Router', 'apikit'
        else:
            event_source = flow.children[0] if flow.children else None
            # Mule does not differentiate between an event source and the first processor in a flow
            # So test the first element to see if it's a known type of event source
            # If it's a listener, subscriber, etc the event_source_alias will be populated.
            if event_source:
                event_source_alias, event_source_description, event_source_class_name = self.pretty_participant(event_source)

        if event_source_alias:
            if ' ' in event_source_alias:
                # For extra niceness, remove the class name from the sub label as it's implicit in the icon
                event_source_label = event_source_alias
                if event_source_class_name.lower() in event_source_alias.lower():
                    event_source_label = ' '.join(word for word in event_source_alias.split() if word.lower() not in event_source_class_name.lower().split())
                event_source_label = event_source_label.strip()
                event_source_alias = event_source_alias.split(' ')[0]
            else:
                event_source_label = event_source_alias
        
        # track the alias references
        if not tracking_vars['alias_reference'].get(str(event_source), None):
            # Create it as is
            tracking_vars['alias_reference'][str(event_source)] = event_source_alias
        else:
            # Append a Unique Number to the alias
            tracking_vars['alias_reference'][str(event_source)] = f"{event_source_alias}_{len(tracking_vars['alias_reference'])}"

        # If we get back an alias, we have a valid event source
        if event_source_alias:
            # Track that the flow has an event source
            tracking_vars['event_source'] = True
            # Add the event source participant to the actors
            tracking_vars['actors_stack'] = record_actor(
                tracking_vars['alias_reference'].get(str(event_source), event_source_alias), 
                tracking_vars['actors_stack'], 
                event_source_class_name, 
                relative_position="source",
                sub_label=event_source_label)
           
            # Add the event source line to the diagram
            
            # Special case for APIKit flows
            if event_source == 'apikit':
                target_actor = str(flow.children[0] if flow.children else None)
            else:
                target_actor = str(event_source)
            
            # Create the event source line
            content.append("'source event")
            content.append(sequence_line_formatter(
                tracking_vars['alias_reference'].get(str(event_source), str(event_source)), 
                target_actor, 
                event_source_description, 
                self.properties['diagram_formatting_properties']['arrows']['flow'],
                tracking_vars=tracking_vars))

        # Even though the Event Source has started the diagram, we can add the title now
        # And use it as a flag to prevent the primary flow from being added as a group
        if flow.attributes.get('name'):
            content.append(f"title {flow.attributes.get('name')}")
        else:
            content.append("title Unnamed Flow")

        # Recursively process the flow elements starting with the root flow
        process_element(flow, content, tracking_vars)

        content.append("@enduml")

        # Replace the participants placeholder
        content[content.index("##PP##")] = "\n".join(tracking_vars['actors_stack'])
        
        # Remove any duplicate create symbols
        # Hack until a better way of checking at add time is possible
        # probably by adding "content" into the tracking_vars
        for i, line in enumerate(content):
            if " ** " in line:
                pattern = re.search(r'"[^"]+"\s\*\*\s:', line)
                if pattern:
                    match = pattern.group()
                    # Check subsequent lines for the same pattern
                    for j in range(i+1, len(content)):
                        if match in content[j]:
                            # Remove the "** " from the subsequent line
                            content[j] = content[j].replace(" ** ", " ")

        return content


    def render_legend(self, arrow_legend:dict, flow_name:str):
        """
        @startuml

        !procedure $arrow($legend, $text)
        \n<font:monospaced.bold>$legend</font> => \n{{\ntop to bottom direction\nskinparam backgroundcolor transparent\nlabel " " as A\nlabel " " as B\nA $text B\n}}\n
        !endprocedure

        map "Legend" as arrows {
            $arrow("Flow", "->")
            $arrow("Return", "-[dashed]>")
            $arrow("Parallel", "-\\\\")
            $arrow("Async", "->>")
            $arrow("Transaction", "-[#red]>")
            $arrow("Transaction Return", "-[#red,dashed]>")
        }

        @enduml
        """
        
        content = []
        content.append("@startuml")
        content.append("!procedure $arrow($legend, $text)") 
        content.append("\\n<font:monospaced.bold>$legend</font> => \\n{{\\nleft to right direction\\nskinparam backgroundcolor transparent\\nlabel \" \" as A\\nlabel \" \" as B\\nA $text B\\n}}\\n")
        content.append("!endprocedure")
        content.append("map \"Legend\" as arrows {")
        for arrow, arrow_details in arrow_legend.items():
            # See above for how to style, need to add more details to the properties probably
            # doesn't support arrows ending with o or x
            content.append(f"  $arrow(\"{arrow_details.label}\", \"{arrow}\")")
        content.append("}")
        content.append("@enduml")

        self.render_image(content, flow_name + "_legend")
        pass

    def clean_flow_name(self, flow_name:str) -> str:
        """
        Remove special characters from flow_name so it can be used as a file name
        """
        return re.sub(r'[^a-zA-Z0-9_-]', '_', flow_name)

    def _detect_renderer_mode(self) -> str:
        plantuml_properties = self.properties['analyzer_properties'].get('plantuml', {})
        mode = plantuml_properties.get('mode')

        # Backwards compatibility: if mode is omitted, default to server behavior.
        if not mode:
            return 'server'

        mode = str(mode).strip().lower()
        if mode not in ('server', 'jar', 'cli'):
            raise ConfigurationError(
                f"Invalid PlantUML mode '{mode}'. Supported modes are: server, jar, cli."
            )
        return mode

    def _render_with_server(self, infile: str, outfile: str) -> Optional[str]:
        from plantweb.render import render_file

        return render_file(
            infile=infile,
            outfile=outfile,
            renderopts={
                "engine": "plantuml",
                "format": self.properties['analyzer_properties']['plantuml']['format'],
                "server": self.properties['analyzer_properties']['plantuml']['server']
            },
            cacheopts={
                "use_cache": False
            }
        )

    def _render_with_jar(self, infile: str, outfile: str) -> Optional[str]:
        plantuml_properties = self.properties['analyzer_properties'].get('plantuml', {})
        jar_path = plantuml_properties.get('jar_path')
        if not jar_path:
            raise ConfigurationError(
                "PlantUML mode 'jar' requires analyzer_properties.plantuml.jar_path."
            )

        java_command = plantuml_properties.get('java_command', 'java')
        jar_path = os.path.abspath(jar_path)
        output_dir = os.path.dirname(outfile)
        output_format = plantuml_properties['format']

        if shutil.which(java_command) is None:
            raise RenderingError(
                f"Java command '{java_command}' not found. Install Java or configure analyzer_properties.plantuml.java_command."
            )
        if not os.path.isfile(jar_path):
            raise RenderingError(f"PlantUML jar not found at: {jar_path}")

        cmd = [
            java_command,
            "-jar",
            jar_path,
            f"-t{output_format}",
            "-charset",
            "UTF-8",
            "-o",
            output_dir,
            infile,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            raise RenderingError(
                f"PlantUML jar rendering failed (exit code {result.returncode}): {stderr}"
            )

        if not os.path.exists(outfile):
            raise RenderingError(f"PlantUML jar did not produce expected output: {outfile}")
        return outfile

    def _render_with_cli(self, infile: str, outfile: str) -> Optional[str]:
        plantuml_properties = self.properties['analyzer_properties'].get('plantuml', {})
        cli_command = plantuml_properties.get('cli_command', 'plantuml')
        output_dir = os.path.dirname(outfile)
        output_format = plantuml_properties['format']

        if shutil.which(cli_command) is None:
            raise RenderingError(
                f"PlantUML CLI command '{cli_command}' not found. Install PlantUML CLI or configure analyzer_properties.plantuml.cli_command."
            )

        cmd = [
            cli_command,
            f"-t{output_format}",
            "-charset",
            "UTF-8",
            "-o",
            output_dir,
            infile,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            raise RenderingError(
                f"PlantUML CLI rendering failed (exit code {result.returncode}): {stderr}"
            )

        if not os.path.exists(outfile):
            raise RenderingError(f"PlantUML CLI did not produce expected output: {outfile}")
        return outfile

    def render_image(self, diagram_syntax: List[str], flow_name: str) -> Optional[str]:
        plantuml_output_directory = self.properties['analyzer_properties']['plantuml']['output_directory']

        # Remove special characters from flow_name
        flow_name_file_name = self.clean_flow_name(flow_name)

        # Create output directory
        try:
            os.makedirs(plantuml_output_directory, exist_ok=True)
        except OSError as e:
            raise RenderingError(f"Failed to create output directory: {e}")
               
        # Render the PlantUML diagram
        infile = os.path.join(plantuml_output_directory, f"{flow_name_file_name}.txt")
        try:
            with open(infile, 'wb') as fd:
                fd.write('\n'.join(diagram_syntax).encode('utf-8'))
        except IOError as e:
            raise RenderingError(f"Failed to write diagram file: {e}")

        outfile_path = os.path.join(
            plantuml_output_directory,
            f"{flow_name_file_name}.{self.properties['analyzer_properties']['plantuml']['format']}"
        )

        try:
            mode = self._detect_renderer_mode()
            if mode == 'server':
                outfile = self._render_with_server(infile, outfile_path)
            elif mode == 'jar':
                outfile = self._render_with_jar(infile, outfile_path)
            else:
                outfile = self._render_with_cli(infile, outfile_path)
        except Exception as e:
            logger.error(
                f"Error rendering diagram for flow {flow_name}. Syntax saved to {infile}."
            )
            logger.debug(f"{str(e)}")
            logger.debug(f"{traceback.format_exc()}")
            return None

        # Return the final syntax list
        return outfile


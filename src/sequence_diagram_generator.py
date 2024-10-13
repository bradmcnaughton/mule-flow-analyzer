import os
import re
from src.mule_flow_analyzer import MuleFlowElement

class SequenceDiagramGenerator:
    def __init__(self):
        self.mule_box_format = "box #LightBlue"
        pass

    def clean_uml_syntax(self, input_string:str):
        def quote_actor(actor):
                if actor:
                    return f"\"{actor}\""
                else:
                    return ""
        
        return quote_actor(input_string.replace("\"", "").replace(" [", "\\n["))

    def pretty_participant(self, element:MuleFlowElement, source_or_target:str="source"):
        alias, description, class_name = None, None, "participant"
        if element.tag == 'scheduler':
            # clock
            alias = "Scheduler"
            description = "Scheduled Task"
            class_name = "scheduler"
        elif 'listener' in element.tag or source_or_target == "target":
            print(f"Adding Listener: {element.tag}")
            if element.tag.startswith('db'):
                # database row
                alias = "Database"
                description = "Database Change"
                class_name = "database"
            elif element.tag.startswith('http'):
                # web   
                alias = "HTTP"
                description = "HTTP Request" 
                class_name = "http"
            elif element.tag.startswith('email'):
                # email
                alias = "Email"
                description = "Email Message"
                class_name = "email"
            elif element.tag.startswith('sockets'):
                # sockets
                alias = "Socket"
                description = "Socket Connection"
                class_name = "socket"
            elif element.tag.startswith('sftp') or element.tag.startswith('file'):
                # file  
                alias = "File"
                description = "File Transfer"
                class_name = "file"
            elif element.tag.startswith('jms') or element.tag.startswith('vm') or element.tag.split(":")[0].endswith("mq"):
                # queue
                alias = "Queue"
                description = "Message"
                class_name = "queue"

        return alias, description, class_name

    def generate_sequence_diagram_syntax(self, flow:MuleFlowElement):
        
        def sequence_line_formatter(source_actor, target_actor, description=None, arrow_style="->"):
            cleaned_source_actor = self.clean_uml_syntax(source_actor) if source_actor else "" 
            cleaned_target_actor = self.clean_uml_syntax(target_actor) if target_actor else ""
            # Description should not need to be quoted
            cleaned_description = description if description else ""
            
            return f"{cleaned_source_actor} {arrow_style} {cleaned_target_actor}: {cleaned_description}"
        
        def record_actor(actor, actors_stack, actor_class:str="participant", relative_position:str="mule") -> list:
            def format_actor(actor, actor_class):
                # Switch the actor name to get the right UML participant type
                # Icon Names are here: https://www.plantuml.com/plantuml/png/SoWkIImgAStDuSh9B2x9BqZDoqpE1s8kXzIy5A0m0000
                if actor_class == "queue": # or actor.startswith("jms") or actor.startswith("vm") or actor.split(":")[0].endswith("mq"):
                    actor_class = "queue"
                elif actor_class == "database": # or actor.startswith("db:"):
                    actor_class = "database"
                elif actor_class == "email":
                    actor_class = "participant \"<size:56><&envelope-closed>\" as"
                elif actor_class == "scheduler":
                    actor_class = "participant \"<size:56><&clock>\" as"
                elif actor_class == "file":
                    actor_class = "participant \"<size:56><&file>\" as"
                elif actor_class == "http":
                    actor_class = "participant \"<size:56><&globe>\" as"
                elif actor_class == "socket":
                    actor_class = "participant \"<size:56><&link-intact>\" as"
                
                if actor_class and actor_class.endswith("as"):
                    return f"{actor_class} {actor}"
                else:   
                    return f"{actor_class} {self.clean_uml_syntax(actor)}"
            
            if format_actor(actor, actor_class) not in actors_stack:
                if relative_position == "mule":
                    actors_stack.insert(actors_stack.index('end box'), format_actor(actor, actor_class))
                elif relative_position == "source":
                    actors_stack.insert(actors_stack.index(self.mule_box_format), format_actor(actor, actor_class))
                elif relative_position == "target":
                    actors_stack.append(format_actor(actor, actor_class))
            
            return actors_stack

        # Initialize tracking variables
        tracking_vars = {
            'previous_actor': None,
            'current_actor': "[",
            'transaction_stack': [],
            'actors_stack': [self.mule_box_format, "end box"],
            'event_source': None,
            'event_targets': []
        }

        # The content list will be used to build the diagram syntax
        content = []
        content.append("@startuml")
        
        # TODO: Add formatting option to some user input
        # https://plantuml.com/skinparam
        content.append("skinparam monochrome false")

        # insert participants placeholder
        content.append("##PP##")

        # Determine the Event Source
        event_source = flow.children[0] if flow.children else None
        
        # Mule does not differentiate between an event source and the first processor in a flow
        # So test the first element to see if it's a known type of event source
        if event_source:
            event_source_alias, event_source_description, event_source_class_name = self.pretty_participant(event_source)
        
            # If we get back an alias, we have a valid event source
            if event_source_alias:
                # Track that the flow has an event source
                tracking_vars['event_source'] = True
                # Add the event source participant to the actors
                tracking_vars['actors_stack'] = record_actor(event_source_alias, tracking_vars['actors_stack'], event_source_class_name, relative_position="source")
                # Add the event source line to the diagram
                content.append(sequence_line_formatter(event_source_alias, str(event_source), event_source_description))

        # Even though the Event Source has started the diagram, we can add the title now
        # And use it as a flag to prevent the primary flow from being added as a group
        if flow.attributes.get('name'):
            content.append(f"title {flow.attributes.get('name')}")
        else:
            content.append("title Unnamed Flow")

        def process_element(element:MuleFlowElement, content:list, tracking_vars:dict):
            
            print(f"Creating UML for {element.tag}")

            ignore_list = ['flow-ref']
            transactions_success_list = ['flow', 'try', 'on-error-continue']
            transactions_failure_list = ['on-error-propagate', 'raise-error']

            skip_end_group = False

            # Opening Element Checks
            if element.tag in ['flow', 'sub-flow']:
                if not content[-1].startswith("title"):
                    content.append(f"group {element.tag} {element.attributes.get('name')}")
                else:
                    skip_end_group = True
            elif element.tag not in ignore_list:  
                # Previous actor is calling this element (may be self)
                tracking_vars['current_actor'] = str(element)
                tracking_vars['actors_stack'] = record_actor(tracking_vars['current_actor'], tracking_vars['actors_stack'], relative_position="mule")
                # Store the previous actor for the response line
                previous_actor = tracking_vars['previous_actor']
                
                # Check if element is starting a transaction
                if element.attributes.get('transactionalAction', None):
                    # New Transaction
                    if element.attributes.get('transactionalAction') == 'ALWAYS_BEGIN' or \
                        (element.attributes.get('transactionalAction') == 'BEGIN_OR_JOIN' and len(tracking_vars['transaction_stack']) == 0):
                        # TODO: Handle local transactions having ALWAYS_BEGIN when an existing transaction is already in progress
                        # That should be an error
                        tracking_vars['transaction_stack'].append(element.attributes.get('transactionType', None))
                    
                        content.append(f"note right of {self.clean_uml_syntax(tracking_vars['current_actor'])}: {element.attributes.get('transactionType', None)} Transaction Starting")

                # Append the call line
                # (Skip if event source)
                if not tracking_vars['event_source']:
                    
                    # Add the internal workings of the processor
                    # TODO: sometimes a "process" will have no text/attributes but will have a child with the "process"
                    pass
                    
                    content.append(sequence_line_formatter(previous_actor, tracking_vars['current_actor']))
                    # Check if we should add a target side actor
                    target_alias, target_description, target_class_name = self.pretty_participant(element, source_or_target="target")
                    if target_alias:
                        # TODO: Differentiate targets (e.g. two different databases) by the XML configuration                       
                        tracking_vars['actors_stack'] = record_actor(target_alias, tracking_vars['actors_stack'], target_class_name, relative_position="target")
                        content.append(sequence_line_formatter(tracking_vars['current_actor'], target_alias, target_description))
                        content.append(sequence_line_formatter(target_alias, tracking_vars['current_actor'], None, arrow_style="-->"))

                else:
                    # Set it to None to track we are past the event source
                    tracking_vars['event_source'] = None
                        
                # Update the previous actor for children
                tracking_vars['previous_actor'] = tracking_vars['current_actor']

            # Recursively process children
            for child in element.children:
                content = process_element(child, content, tracking_vars)

            # Closing Element Checks
            # Ending a Transaction
            if len(tracking_vars['transaction_stack']) > 0 and element.tag in transactions_success_list + transactions_failure_list:
                if element.tag in transactions_success_list:
                    content.append(f"note right of {self.clean_uml_syntax(tracking_vars['current_actor'])}: \"{tracking_vars['transaction_stack'][-1]} Transaction Success\"")
                else:
                    content.append(f"note right of {self.clean_uml_syntax(tracking_vars['current_actor'])}: \"{tracking_vars['transaction_stack'][-1]} Transaction Failure\"")
                tracking_vars['transaction_stack'].pop()
            
            # Ending a Group
            if not skip_end_group and element.tag in ['flow', 'sub-flow', 'choice', 'foreach', 'parallel-foreach', 'round-robin', 'scatter-gather']:
                content.append("end")
            else:
                # Response line
                #content.append(sequence_line_formatter(str(element), previous_actor, "return", arrow_style="-->"))
                pass

            return content

        process_element(flow, content, tracking_vars)
        pass

        content.append("@enduml")

        # Replace the participants placeholder
        content[content.index("##PP##")] = "\n".join(tracking_vars['actors_stack'])
        
        return content


    def render_image(self, diagram_syntax:list, flow_name:str):
        import properties
        from plantweb.render import render_file
        plantuml_output_directory = properties.analyzer_properties['plantuml']['output_directory']

        # Remove special characters from flow_name
        flow_name_file_name = re.sub(r'[^a-zA-Z0-9_]', '_', flow_name)

        # create output directory if it doesn't exist
        os.makedirs(plantuml_output_directory, exist_ok=True)   
               
        # Render the PlantUML diagram
        infile = os.path.join(plantuml_output_directory, f"{flow_name_file_name}.txt")
        with open(infile, 'wb') as fd:
            fd.write('\n'.join(diagram_syntax).encode('utf-8'))

        outfile = render_file(
            infile=infile,
            outfile=os.path.join(plantuml_output_directory, f"{flow_name_file_name}.png"),
            renderopts={
                "engine": "plantuml",
                "format": "png"
            },
            cacheopts={
                "use_cache": False
            }
        )

        # Return the final syntax list
        return outfile
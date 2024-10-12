import os
import re
from src.mule_flow_analyzer import MuleFlowElement

class SequenceDiagramGenerator:
    def __init__(self):
        pass

    def generate_sequence_diagram_syntax(self, flow:MuleFlowElement):
        
        def sequence_line_formatter(source_actor, target_actor, description, arrow_style="->"):
            cleaned_source_actor = source_actor.replace("\"", "") if source_actor else None 
            cleaned_target_actor = target_actor.replace("\"", "") if target_actor else None
            cleaned_description = description.replace("\"", "") if description else None

            def quote_actor(actor):
                if actor:
                    return f"\"{actor}\""
                else:
                    return None

            return f"{quote_actor(cleaned_source_actor)} {arrow_style} {quote_actor(cleaned_target_actor)}: {cleaned_description}"
        
        # Initialize tracking variables
        tracking_vars = {
            'current_actor': None,
            'previous_actor': None,
            'actor_stack': [None],  # To track nested actors based on indentation levels
            'current_processor': None,
            'target_processor': None,
            'indent_level': 0
        }

        # Track Flow Refs, Loops and Nested Loops
        flow_ref_stack = []
        choice_stack = []
        loop_stack = []

        # The content list will be used to build the diagram syntax
        content = []
        content.append("@startuml")
        
        # TODO: Add formatting option to some user input
        # https://plantuml.com/skinparam
        content.append("skinparam monochrome true")

        if flow.attributes.get('name'):
            content.append(f"title {flow.attributes.get('name')}")

        def process_element(element, content, tracking_vars):
            # Opening Element Checks
            if element.tag in ['flow', 'subflow']:
                content.append(f"group {element.tag} {element.attributes.get('name')}")

            # Previous actor is calling this element (may be self)
            tracking_vars['current_actor'] = element.attributes.get('name')
            content.append(sequence_line_formatter(tracking_vars['previous_actor'], tracking_vars['current_actor'], "call"))
            
            tracking_vars['previous_actor'] = tracking_vars['current_actor']
            for child in element.children:
                content = process_element(child, content, tracking_vars)

            # Closing Element Checks
            if element.tag in ['flow', 'subflow', 'choice', 'foreach', 'parallel-foreach', 'round-robin', 'scatter-gather']:
                content.append("end")

            return content

        process_element(flow, content, tracking_vars)
        pass

        """ for mule_element in flow:
            # Strip leading and trailing whitespace

            # convert flow-ref into a group
            if stripped_line.startswith("flow-ref"):
                content.append(f"group flow-ref{len(flow_ref_stack)}") # TODO: Add the flow name
                flow_ref_stack.append(indent_level+1)
            else:
                # If the new indent level is greater than the current, it's a nested flow
                if new_indent_level > indent_level:
                    
                    # Check if this is an action on the current processor or invoking a new one.
                    # Explode stripped_line into left and right of first ":" char, handling for no ":"
                    parts = stripped_line.split(':', 1)
                    left = parts[0].strip() if parts else stripped_line
                    right = parts[1].strip() if len(parts) > 1 else ""

                    # Determine if this is a new processor or an action on the current one
                    if ':' in stripped_line and left != current_processor:
                        target_processor = left
                        action = right
                        actor_stack.append(stripped_line)
                        content.append(sequence_line_formatter(actor_stack[-2], actor_stack[-1], action))
                    else:
                        # It's an action on the current processor
                        target_processor = current_processor
                        action = stripped_line
                        content.append(sequence_line_formatter(actor_stack[-1], actor_stack[-1], action))

                    # Update the current processor if it's a new one for the next loop
                    if target_processor != current_processor:
                        current_processor = target_processor               
                    
                elif new_indent_level < indent_level:
                    current_actor = actor_stack.pop()
                    content.append(sequence_line_formatter(current_actor, actor_stack[-1], "return", arrow_style="-->"))

            # Handle Closing Nested Groups
            if len(flow_ref_stack) > 0 and flow_ref_stack[-1] <= indent_level :
                flow_ref_stack.pop()
                content.append(f"end // flow-ref{len(flow_ref_stack)}")

        # Unravel the current stack with returns
        while actor_stack and len(actor_stack) > 1:
            current_actor = actor_stack.pop()
            content.append(sequence_line_formatter(current_actor, actor_stack[-1], "return", arrow_style="-->"))    """ 

        content.append("@enduml")

        return content


    def render_image(self, diagram_syntax:list, flow_name:str):
        import properties
        from plantweb.render import render_file
        plantuml_output_directory = properties.analyzer_properties['plantuml']['output_directory']

        # create output directory if it doesn't exist
        os.makedirs(plantuml_output_directory, exist_ok=True)   
               
        # Render the PlantUML diagram
        infile = 'plantuml.in'
        with open(infile, 'wb') as fd:
            fd.write('\n'.join(diagram_syntax).encode('utf-8'))

        # Remove special characters from flow_name
        flow_name_file_name = re.sub(r'[^a-zA-Z0-9_]', '_', flow_name)

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

        # Remove the temporary input file
        os.remove(infile)

        # Return the final syntax list
        return outfile
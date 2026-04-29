import logging
import os
import re
import shutil
import subprocess
import traceback
from typing import Any, Dict, List, Optional

from .mule_flow_element import MuleFlowElement
from .sequence_diagram_generator import (
    CONTROL_FLOW_BOUNDARY_TAGS,
    CONTROL_FLOW_TAGS,
    LOGGING_PROCESSORS,
    SequenceDiagramGenerator,
)
from ..exceptions import ConfigurationError, RenderingError

logger = logging.getLogger(__name__)


class MermaidSequenceDiagramGenerator(SequenceDiagramGenerator):
    """Generate Mermaid sequence diagram syntax for Mule flows."""

    def __init__(self, configuration_properties: Dict[str, Any]) -> None:
        super().__init__(configuration_properties)
        self._alias_counts: Dict[str, int] = {}

    def clean_mermaid_alias(self, input_string: str) -> str:
        alias = re.sub(r'\W+', '_', input_string or '').strip('_')
        if not alias:
            alias = 'Participant'
        if alias[0].isdigit():
            alias = f'p_{alias}'
        return alias

    def clean_mermaid_label(self, input_string: str) -> str:
        label = str(input_string or '').replace('"', "'")
        label = label.replace('\\n', ' ').replace('\n', ' ')
        label = re.sub(r'\s+', ' ', label).strip()
        return label

    def clean_mermaid_note(self, input_string: str) -> str:
        note = str(input_string or '').replace('\r\n', '\n').replace('\r', '\n')
        return note.replace('\n', '<br/>').replace(':', '&#58;')

    def _unique_alias(self, label: str, aliases: Dict[str, str]) -> str:
        base_alias = self.clean_mermaid_alias(label)
        alias = base_alias
        while alias in aliases and aliases[alias] != label:
            self._alias_counts[base_alias] = self._alias_counts.get(base_alias, 1) + 1
            alias = f"{base_alias}_{self._alias_counts[base_alias]}"
        return alias

    def _record_participant(
        self,
        label: str,
        participants: Dict[str, str],
        participant_type: str = 'participant',
    ) -> str:
        clean_label = self.clean_mermaid_label(label)
        alias = self._unique_alias(clean_label, participants)
        participants[alias] = clean_label
        participant_type = 'actor' if participant_type == 'actor' else 'participant'
        return alias

    def _format_message(
        self,
        source_alias: str,
        target_alias: str,
        description: Optional[str] = None,
        arrow_style: str = 'flow',
    ) -> str:
        arrow_map = {
            'flow': '->>',
            'return': '-->>',
            'async': '-)',
            'parallel': '->>',
        }
        arrow = arrow_map.get(arrow_style, '->>')
        label = self.clean_mermaid_label(description) if description else ''
        return f"{source_alias} {arrow} {target_alias}: {label}"

    def _loop_label(self, element: MuleFlowElement) -> str:
        if element.tag in ['foreach', 'parallel-foreach']:
            label = element.attributes.get('documentation:name') or element.tag
            collection = element.attributes.get('collection')
            if collection:
                label = f"{label} collection: {collection}"
            return label

        if element.tag == 'until-successful':
            label = element.attributes.get('documentation:name') or 'Until Successful'
            max_retries = element.attributes.get('maxRetries')
            if max_retries:
                label = f"{label} max retries: {max_retries}"
            return label

        return element.attributes.get('documentation:name') or element.tag

    def generate_sequence_diagram_syntax(self, flow: MuleFlowElement):
        self._alias_counts = {}

        participants: Dict[str, str] = {}
        participant_types: Dict[str, str] = {}
        content: List[str] = ["sequenceDiagram"]
        flow_name = flow.attributes.get('name') or 'Unnamed Flow'
        content.append(f"title {self.clean_mermaid_label(flow_name)}")

        def record(label: str, participant_type: str = 'participant') -> str:
            alias = self._record_participant(label, participants, participant_type)
            if participant_types.get(alias) != 'actor':
                participant_types[alias] = participant_type
            return alias

        mule_alias = record('Mule')
        previous_actor = mule_alias

        event_source = None
        event_source_alias = None
        event_source_description = None
        event_source_class_name = 'participant'

        if flow.attributes.get('name') and re.match(r'^(get|put|post|patch|delete|options):\\', flow.attributes['name'], re.IGNORECASE):
            event_source = 'apikit'
            event_source_alias = 'apikit'
            event_source_description = 'APIKit Router'
            event_source_class_name = 'actor'
        else:
            event_source = flow.children[0] if flow.children else None
            if event_source:
                event_source_alias, event_source_description, event_source_class_name = self.pretty_participant(event_source)

        if event_source_alias:
            source_alias = record(event_source_alias, 'actor')
            target_label = str(flow.children[0]) if event_source == 'apikit' and flow.children else str(event_source)
            previous_actor = record(target_label)
            content.append(self._format_message(source_alias, previous_actor, event_source_description, 'flow'))

        def process_element(element: MuleFlowElement, current_previous_actor: str) -> str:
            nonlocal content

            if element.tag in ['flow', 'sub-flow']:
                for child in element.children:
                    current_previous_actor = process_element(child, current_previous_actor)
                return current_previous_actor

            if element.tag in ['choice', 'round-robin']:
                branches = element.children
                for index, branch in enumerate(branches):
                    branch_label = 'Round Robin' if element.tag == 'round-robin' else self.remove_expression_brackets(branch.attributes.get('expression', 'otherwise'))
                    keyword = 'alt' if index == 0 else 'else'
                    content.append(f"{keyword} {self.clean_mermaid_label(branch_label)}")
                    branch_previous = current_previous_actor
                    for child in branch.children:
                        branch_previous = process_element(child, branch_previous)
                content.append("end")
                return current_previous_actor

            if element.tag in ['foreach', 'until-successful', 'parallel-foreach']:
                content.append(f"loop {self.clean_mermaid_label(self._loop_label(element))}")
                loop_previous = current_previous_actor
                for child in element.children:
                    loop_previous = process_element(child, loop_previous)
                content.append("end")
                return loop_previous

            if element.tag in ['scatter-gather', 'first-successful']:
                routes = element.children
                route_end_aliases = []
                for index, route in enumerate(routes):
                    keyword = 'par' if index == 0 else 'and'
                    label = route.attributes.get('documentation:name') or route.attributes.get('name') or f"Route {index + 1}"
                    content.append(f"{keyword} {self.clean_mermaid_label(label)}")
                    route_previous = current_previous_actor
                    for child in route.children:
                        route_previous = process_element(child, route_previous)
                    route_end_aliases.append(route_previous)
                content.append("end")
                return route_end_aliases[-1] if route_end_aliases else current_previous_actor

            if element.tag == 'async':
                content.append(f"Note over {current_previous_actor}: Async Start")
                async_previous = current_previous_actor
                for child in element.children:
                    async_previous = process_element(child, async_previous)
                return current_previous_actor

            if element.tag == 'try':
                content.append(f"alt {self.clean_mermaid_label(element.attributes.get('documentation:name', 'Try'))}")
                try_previous = current_previous_actor
                for child in element.children:
                    try_previous = process_element(child, try_previous)
                content.append("else Error Handling")
                if element.error_handler_ref:
                    content.append(f"Note over {try_previous}: {self.clean_mermaid_note(element.error_handler_ref)}")
                if self.properties['diagram_formatting_properties']['verbose']['errors'] and element.error_handler_element:
                    error_previous = try_previous
                    for child in element.error_handler_element.children:
                        error_previous = process_element(child, error_previous)
                content.append("end")
                return try_previous

            if element.tag == 'ee:cache':
                content.append("alt Cache Miss")
                cache_previous = current_previous_actor
                for child in element.children:
                    cache_previous = process_element(child, cache_previous)
                content.append("else Cache Hit")
                content.append(self._format_message(current_previous_actor, cache_previous, 'Use Cached Value', 'flow'))
                content.append("end")
                return cache_previous

            should_render_processor = (
                element.tag not in CONTROL_FLOW_BOUNDARY_TAGS
                and (element.tag not in LOGGING_PROCESSORS or self.properties['diagram_formatting_properties']['verbose']['logging'])
            )

            if should_render_processor:
                current_alias = record(str(element))
                is_event_source_processor = element is event_source and current_previous_actor == current_alias
                if not is_event_source_processor:
                    content.append(self._format_message(current_previous_actor, current_alias, None, 'flow'))

                if element.attributes.get('transactionalAction'):
                    transaction_type = element.attributes.get('transactionType') or 'Local'
                    content.append(f"Note over {current_alias}: {self.clean_mermaid_note(transaction_type)} Transaction Starting")

                if element.tag == 'raise-error':
                    note = f"Raising Error<br/>{self.clean_mermaid_note(element.attributes.get('type', 'Missing Error Type'))}"
                    if element.error_handler_ref:
                        note += f"<br/><br/>Error Handler<br/>{self.clean_mermaid_note(element.error_handler_ref)}"
                    content.append(f"Note over {current_alias}: {note}")

                if self.properties['diagram_formatting_properties']['verbose']['notes']:
                    documentation = element.attributes.get('documentation:description')
                    if documentation:
                        content.append(f"Note over {current_alias}: {self.clean_mermaid_note(documentation)}")

                if element.processes:
                    activities: List[str] = []
                    for process in element.processes:
                        activities = self.attributes_to_activities(process, activities, process_prefix=element.tag.split(":")[-1])
                    for activity in activities:
                        content.append(self._format_message(current_alias, current_alias, activity, 'flow'))

                target_alias, target_description, target_class_name = self.pretty_participant(element, source_or_target='target')
                if target_alias and not is_event_source_processor:
                    external_alias = record(target_alias, 'actor' if target_class_name in ['scheduler'] else 'participant')
                    content.append(self._format_message(current_alias, external_alias, target_description, 'flow'))
                    content.append(self._format_message(external_alias, current_alias, None, 'return'))

                current_previous_actor = current_alias

            if element.tag not in CONTROL_FLOW_TAGS:
                for child in element.children:
                    current_previous_actor = process_element(child, current_previous_actor)

            return current_previous_actor

        for child in flow.children:
            previous_actor = process_element(child, previous_actor)

        participant_lines = []
        for alias, label in participants.items():
            participant_type = participant_types.get(alias, 'participant')
            participant_lines.append(f"{participant_type} {alias} as {label}")

        return content[:2] + participant_lines + content[2:]

    def _detect_renderer_mode(self) -> str:
        mermaid_properties = self.properties['analyzer_properties'].get('mermaid', {})
        mode = mermaid_properties.get('mode', 'file')

        if not mode:
            return 'file'

        mode = str(mode).strip().lower()
        if mode not in ('file', 'cli'):
            raise ConfigurationError(
                f"Invalid Mermaid mode '{mode}'. Supported modes are: file, cli."
            )
        return mode

    def _render_with_cli(self, infile: str, outfile: str) -> Optional[str]:
        mermaid_properties = self.properties['analyzer_properties'].get('mermaid', {})
        cli_command = mermaid_properties.get('cli_command', 'mmdc')

        if shutil.which(cli_command) is None:
            raise RenderingError(
                f"Mermaid CLI command '{cli_command}' not found. Install @mermaid-js/mermaid-cli or configure analyzer_properties.mermaid.cli_command."
            )

        cmd = [cli_command, "-i", infile, "-o", outfile]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            raise RenderingError(
                f"Mermaid CLI rendering failed (exit code {result.returncode}): {stderr}"
            )

        if not os.path.exists(outfile):
            raise RenderingError(f"Mermaid CLI did not produce expected output: {outfile}")
        return outfile

    def render_image(self, diagram_syntax: List[str], flow_name: str) -> Optional[str]:
        mermaid_properties = self.properties['analyzer_properties']['mermaid']
        output_directory = mermaid_properties['output_directory']
        source_extension = mermaid_properties.get('source_extension', 'mmd').lstrip('.')

        flow_name_file_name = self.clean_flow_name(flow_name)

        try:
            os.makedirs(output_directory, exist_ok=True)
        except OSError as e:
            raise RenderingError(f"Failed to create output directory: {e}")

        infile = os.path.join(output_directory, f"{flow_name_file_name}.{source_extension}")
        try:
            with open(infile, 'wb') as fd:
                fd.write('\n'.join(diagram_syntax).encode('utf-8'))
        except IOError as e:
            raise RenderingError(f"Failed to write diagram file: {e}")

        try:
            mode = self._detect_renderer_mode()
            if mode == 'file':
                return infile

            outfile = os.path.join(
                output_directory,
                f"{flow_name_file_name}.{mermaid_properties['format']}"
            )
            return self._render_with_cli(infile, outfile)
        except Exception as e:
            logger.error(
                f"Error rendering Mermaid diagram for flow {flow_name}. Syntax saved to {infile}."
            )
            logger.debug(f"{str(e)}")
            logger.debug(f"{traceback.format_exc()}")
            return None

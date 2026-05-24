import logging
import os
import re
from typing import List, Optional

from .mule_flow_element import MuleFlowElement
from .sequence_diagram_generator import (
    CONTROL_FLOW_BOUNDARY_TAGS,
    CONTROL_FLOW_TAGS,
    LOGGING_PROCESSORS,
    SequenceDiagramGenerator,
)
from ..exceptions import RenderingError

logger = logging.getLogger(__name__)

_MESSAGING_NAMESPACES = frozenset({"jms", "vm", "ibm-mq", "anypoint-mq"})
_MESSAGING_CALL_PHRASES = {
    "consume": "Consume message from",
    "publish": "Publish message to",
    "publish-consume": "Publish and consume message on",
    "ack": "Acknowledge message on",
}
_MESSAGING_TRIGGER_PHRASES = {
    "listener": "Listen for messages on",
    "subscriber": "Subscribe to messages on",
}


class NaturalLanguageDescriptionGenerator(SequenceDiagramGenerator):
    """Generate deterministic structured English descriptions of Mule flows."""

    def _indent(self, depth: int) -> str:
        return "  " * depth

    def _quote_name(self, value: str) -> str:
        if not value or not str(value).strip():
            return value
        text = str(value).strip()
        if text.startswith('"') and text.endswith('"'):
            return text
        escaped = text.replace('"', '\\"')
        return f'"{escaped}"'

    def _should_quote_embedded_name(self, text: str) -> bool:
        """Quote bare custom names embedded in boilerplate, not delimited values."""
        if not text or not str(text).strip():
            return False
        text = str(text).strip()
        if text.startswith('"') and text.endswith('"'):
            return False
        if "[" in text or "]" in text:
            return False
        if "(" in text or ")" in text:
            return False
        if ": " in text or text.endswith(":"):
            return False
        return True

    def _quoted_if_embedded(self, text: str) -> str:
        if self._should_quote_embedded_name(text):
            return self._quote_name(text)
        return text

    def _doc_name(self, element: MuleFlowElement) -> str:
        return (
            element.attributes.get("documentation:name")
            or element.attributes.get("name")
            or ""
        )

    def _loop_label(self, element: MuleFlowElement) -> str:
        if element.tag in ["foreach", "parallel-foreach"]:
            label = self._doc_name(element) or element.tag
            collection = element.attributes.get("collection")
            if collection:
                return f"{label} (collection: {collection})"
            return label

        if element.tag == "until-successful":
            label = self._doc_name(element) or "Until Successful"
            max_retries = element.attributes.get("maxRetries")
            if max_retries:
                return f"{label} (max retries: {max_retries})"
            return label

        return self._doc_name(element) or element.tag

    def _messaging_namespace(self, tag: str) -> Optional[str]:
        if ":" not in tag:
            return None
        namespace = tag.split(":", 1)[0]
        return namespace if namespace in _MESSAGING_NAMESPACES else None

    def _messaging_operation(self, element: MuleFlowElement) -> Optional[str]:
        if not self._messaging_namespace(element.tag):
            return None
        if ":" not in element.tag:
            return None
        return element.tag.split(":", 1)[1]

    def _queue_destination(self, element: MuleFlowElement) -> Optional[str]:
        return element.attributes.get("destination") or element.attributes.get("queueName")

    def _config_suffix(self, element: MuleFlowElement) -> str:
        config_ref = element.attributes.get("config-ref")
        return f" via {self._quote_name(config_ref)}" if config_ref else ""

    def _doc_suffix(self, element: MuleFlowElement) -> str:
        doc_name = self._doc_name(element)
        return f" ({doc_name})" if doc_name else ""

    def _messaging_trigger_sentence(self, element: MuleFlowElement) -> Optional[str]:
        operation = self._messaging_operation(element)
        if operation not in _MESSAGING_TRIGGER_PHRASES:
            return None

        queue_name = self._queue_destination(element)
        destination = self._quote_name(queue_name) if queue_name else "queue"
        phrase = _MESSAGING_TRIGGER_PHRASES[operation]
        return (
            f"Triggered by {phrase} {destination}"
            f"{self._doc_suffix(element)}{self._config_suffix(element)}."
        )

    def _messaging_call_sentence(self, element: MuleFlowElement) -> Optional[str]:
        operation = self._messaging_operation(element)
        if operation not in _MESSAGING_CALL_PHRASES:
            return None

        queue_name = self._queue_destination(element)
        if operation == "ack" and not queue_name:
            return (
                f"{_MESSAGING_CALL_PHRASES[operation]} queue"
                f"{self._doc_suffix(element)}{self._config_suffix(element)}, then return to Mule."
            )

        destination = self._quote_name(queue_name) if queue_name else "queue"
        phrase = _MESSAGING_CALL_PHRASES[operation]
        return (
            f"{phrase} {destination}"
            f"{self._doc_suffix(element)}{self._config_suffix(element)}, then return to Mule."
        )

    def _branch_label(self, element: MuleFlowElement, branch: MuleFlowElement) -> str:
        if element.tag == "round-robin":
            return "Round Robin route"
        expression = branch.attributes.get("expression", "otherwise")
        return self.remove_expression_brackets(expression)

    def _processor_sentence(self, element: MuleFlowElement) -> str:
        doc_name = self._doc_name(element)

        if element.tag == "set-variable":
            variable_name = element.attributes.get("variableName", "")
            if doc_name:
                return f"Set variable {variable_name} ({doc_name})."
            return f"Set variable {variable_name}."

        if element.tag == "set-payload":
            return f"Set payload ({doc_name})." if doc_name else "Set payload."

        if element.tag.startswith("ee:transform") or element.tag == "ee:transform":
            return f"Transform data: {doc_name}." if doc_name else "Transform data."

        if element.tag == "raise-error":
            error_type = element.attributes.get("type", "Missing Error Type")
            return f"Raise error {error_type}."

        messaging_sentence = self._messaging_call_sentence(element)
        if messaging_sentence:
            return messaging_sentence

        _, target_description, _ = self.pretty_participant(
            element, source_or_target="target"
        )
        if target_description:
            config_ref = element.attributes.get("config-ref")
            target_part = self._quoted_if_embedded(target_description)
            if config_ref:
                config_suffix = f" via {self._quote_name(config_ref)}"
            else:
                config_suffix = ""
            return f"Call {target_part}{config_suffix}, then return to Mule."

        return f"Execute {element}."

    def generate_description(self, flow: MuleFlowElement) -> List[str]:
        lines: List[str] = []
        flow_name = flow.attributes.get("name") or "Unnamed Flow"
        lines.append(f'Flow "{flow_name}":')
        lines.append("")

        event_source = None
        event_source_description = None

        if flow.attributes.get("name") and re.match(
            r"^(get|put|post|patch|delete|options):\\",
            flow.attributes["name"],
            re.IGNORECASE,
        ):
            event_source = "apikit"
            event_source_description = "APIKit Router"
        else:
            event_source = flow.children[0] if flow.children else None
            if event_source:
                _, event_source_description, _ = self.pretty_participant(event_source)

        if event_source_description:
            if event_source and event_source != "apikit":
                trigger_sentence = self._messaging_trigger_sentence(event_source)
                if trigger_sentence:
                    lines.append(trigger_sentence)
                elif trigger_name := self._doc_name(event_source):
                    lines.append(
                        f"Triggered by {event_source_description} ({trigger_name})."
                    )
                else:
                    lines.append(f"Triggered by {event_source_description}.")
            elif trigger_name := flow.attributes.get("name", ""):
                lines.append(
                    f"Triggered by {event_source_description} ({trigger_name})."
                )
            else:
                lines.append(f"Triggered by {event_source_description}.")
            lines.append("")

        transaction_stack: List[str] = []
        transactions_success_list = ["flow", "try", "on-error-continue"]
        transactions_failure_list = ["on-error-propagate", "raise-error"]
        verbose = self.properties["diagram_formatting_properties"]["verbose"]

        def append_transaction_end(element: MuleFlowElement, depth: int) -> None:
            if not transaction_stack:
                return
            if element.tag not in transactions_success_list + transactions_failure_list:
                return

            transaction_type = transaction_stack[-1]
            if element.tag in transactions_success_list:
                lines.append(
                    f"{self._indent(depth)}{transaction_type} transaction ends."
                )
            else:
                lines.append(
                    f"{self._indent(depth)}{transaction_type} transaction fails."
                )
            transaction_stack.pop()

        def process_element(element: MuleFlowElement, depth: int) -> None:
            if element.tag in ["flow", "sub-flow"]:
                for child in element.children:
                    process_element(child, depth)
                append_transaction_end(element, depth)
                return

            if element.tag in ["choice", "round-robin"]:
                for index, branch in enumerate(element.children):
                    prefix = "If" if index == 0 else "Else if"
                    if branch.tag == "otherwise":
                        prefix = "Otherwise"
                    branch_label = self._branch_label(element, branch)
                    lines.append(
                        f"{self._indent(depth)}{prefix} {branch_label}:"
                    )
                    for child in branch.children:
                        process_element(child, depth + 1)
                return

            if element.tag in ["foreach", "parallel-foreach"]:
                lines.append(
                    f"{self._indent(depth)}For each iteration in {self._loop_label(element)}:"
                )
                for child in element.children:
                    process_element(child, depth + 1)
                return

            if element.tag == "until-successful":
                lines.append(
                    f"{self._indent(depth)}Retry until successful in {self._loop_label(element)}:"
                )
                for child in element.children:
                    process_element(child, depth + 1)
                return

            if element.tag in ["scatter-gather", "first-successful"]:
                scope_name = self._doc_name(element) or element.tag
                if element.tag == "first-successful":
                    lines.append(
                        f"{self._indent(depth)}Execute routes in parallel until first success ({scope_name}):"
                    )
                else:
                    lines.append(
                        f"{self._indent(depth)}Execute routes in parallel ({scope_name}):"
                    )
                for index, route in enumerate(element.children):
                    route_name = (
                        route.attributes.get("documentation:name")
                        or route.attributes.get("name")
                        or f"Route {index + 1}"
                    )
                    lines.append(
                        f"{self._indent(depth + 1)}Route {self._quoted_if_embedded(route_name)}:"
                    )
                    for child in route.children:
                        process_element(child, depth + 2)
                return

            if element.tag == "async":
                lines.append(f"{self._indent(depth)}Run the following asynchronously:")
                for child in element.children:
                    process_element(child, depth + 1)
                return

            if element.tag == "try":
                scope_name = self._doc_name(element) or "Try"
                lines.append(f"{self._indent(depth)}Try ({scope_name}):")
                for child in element.children:
                    process_element(child, depth + 1)
                if element.error_handler_ref:
                    lines.append(
                        f"{self._indent(depth + 1)}Error handler: {element.error_handler_ref}."
                    )
                if verbose["errors"] and element.error_handler_element:
                    lines.append(f"{self._indent(depth + 1)}On error:")
                    for child in element.error_handler_element.children:
                        process_element(child, depth + 2)
                return

            if element.tag == "ee:cache":
                cache_name = self._doc_name(element) or "Cache"
                lines.append(f"{self._indent(depth)}On cache miss ({cache_name}):")
                for child in element.children:
                    process_element(child, depth + 1)
                return

            if element.tag.split(":")[0] == "batch":
                if element.tag == "batch:job":
                    job_name = element.attributes.get("jobName", "")
                    batch_label = f'Batch job {self._quote_name(job_name)}'.strip()
                elif element.tag == "batch:process-records":
                    batch_label = 'Batch "process records"'
                elif element.tag == "batch:step":
                    step_name = element.attributes.get("name", "")
                    batch_label = f'Batch step {self._quote_name(step_name)}'.strip()
                elif element.tag == "batch:aggregator":
                    aggregator_name = element.attributes.get("name", "")
                    if aggregator_name:
                        batch_label = f'Batch aggregator {self._quote_name(aggregator_name)}'.strip()
                    else:
                        batch_label = "Batch aggregator"
                elif element.tag == "batch:on-complete":
                    batch_label = "Batch on complete"
                else:
                    batch_label = element.tag
                lines.append(f"{self._indent(depth)}{batch_label}:")
                for child in element.children:
                    process_element(child, depth + 1)
                return

            should_render_processor = element.tag not in CONTROL_FLOW_BOUNDARY_TAGS and (
                element.tag not in LOGGING_PROCESSORS or verbose["logging"]
            )

            if should_render_processor:
                is_event_source_processor = element is event_source
                if not is_event_source_processor:
                    lines.append(
                        f"{self._indent(depth)}{self._processor_sentence(element)}"
                    )

                transactional_action = element.attributes.get("transactionalAction")
                if transactional_action in ("ALWAYS_BEGIN", "BEGIN_OR_JOIN"):
                    if transactional_action == "ALWAYS_BEGIN" or not transaction_stack:
                        transaction_type = element.attributes.get("transactionType") or "Local"
                        transaction_stack.append(transaction_type)
                        lines.append(
                            f"{self._indent(depth + 1)}{transaction_type} transaction starts."
                        )

                if element.error_handler_ref and element.tag != "try":
                    lines.append(
                        f"{self._indent(depth + 1)}Uses error handler: {element.error_handler_ref}."
                    )

                if verbose["notes"]:
                    documentation = element.attributes.get("documentation:description")
                    if documentation:
                        lines.append(f"{self._indent(depth + 1)}Note: {documentation}")

                if verbose["processors"] and element.processes:
                    for process in element.processes:
                        activities: List[str] = []
                        activities = self.attributes_to_activities(
                            process,
                            activities,
                            process_prefix=element.tag.split(":")[-1],
                        )
                        for activity in activities:
                            lines.append(f"{self._indent(depth + 1)}{activity}.")

                target_variable = self.mule_target_variable_value(element)
                if target_variable:
                    lines.append(
                        f"{self._indent(depth + 1)}Save output to variable {target_variable}."
                    )

            if element.tag not in CONTROL_FLOW_TAGS:
                for child in element.children:
                    process_element(child, depth)

            append_transaction_end(element, depth)

        start_depth = 0
        children = flow.children
        if event_source and event_source != "apikit" and children:
            for child in children[1:]:
                process_element(child, start_depth)
        elif event_source == "apikit" and children:
            for child in children:
                process_element(child, start_depth)
        else:
            for child in children:
                process_element(child, start_depth)

        append_transaction_end(flow, start_depth)
        return lines

    def write_output(self, description_lines: List[str], flow_name: str) -> str:
        natural_properties = self.properties["analyzer_properties"]["natural"]
        output_directory = natural_properties["output_directory"]
        file_extension = natural_properties.get("file_extension", "txt").lstrip(".")

        flow_name_file_name = self.clean_flow_name(flow_name)
        outfile = os.path.join(
            output_directory, f"{flow_name_file_name}.{file_extension}"
        )

        try:
            os.makedirs(output_directory, exist_ok=True)
        except OSError as error:
            raise RenderingError(f"Failed to create output directory: {error}") from error

        try:
            with open(outfile, "w", encoding="utf-8") as handle:
                handle.write("\n".join(description_lines))
                handle.write("\n")
        except OSError as error:
            raise RenderingError(f"Failed to write natural language description: {error}") from error

        return outfile

class MuleFlowException(Exception):
    """Base exception for Mule Flow Analyzer errors."""
    pass


class PropertyHierarchyError(MuleFlowException):
    """Raised when there's an error processing property hierarchy."""
    pass


class MuleFlowParsingException(MuleFlowException):
    """Exception raised when there is an error parsing a Mule flow XML file."""
    pass


class MuleFlowValidationException(MuleFlowException):
    """Exception raised when there is an error validating a Mule flow."""
    pass


class DiagramGenerationException(MuleFlowException):
    """Base exception for sequence diagram generation and rendering."""
    pass


class ConfigurationError(DiagramGenerationException):
    """Raised when diagram or analyzer configuration is invalid or incomplete."""
    pass


class RenderingError(DiagramGenerationException):
    """Raised when diagram rendering or writing output files fails."""
    pass


# Backward-compatible alias
DiagramGenerationError = DiagramGenerationException

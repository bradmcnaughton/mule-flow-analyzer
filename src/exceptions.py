class ConfigurationError(Exception):
    """Raised when there's an error in configuration"""
    pass

class PropertyHierarchyError(Exception):
    """Raised when there's an error processing property hierarchy"""
    pass

class MuleFlowException(Exception):
    """Base exception for Mule Flow Analyzer errors"""
    pass

class MuleFlowParsingException(MuleFlowException):
    """Exception raised when there is an error parsing a Mule flow XML file"""
    pass

class MuleFlowValidationException(MuleFlowException):
    """Exception raised when there is an error validating a Mule flow"""
    pass

class DiagramGenerationException(MuleFlowException):
    """Exception raised when there is an error generating a sequence diagram"""
    pass 
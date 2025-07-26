# ===== converters/base_converter.py =====
from abc import ABC, abstractmethod
from typing import Dict, Any

class ConversionError(Exception):
    """Exception raised when conversion fails"""
    pass

class BaseConverter(ABC):
    """Base class for all platform converters"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.validate_config()

    def validate_config(self):
        """Validate the provided configuration"""
        if not isinstance(self.config, dict):
            raise ConversionError("Configuration must be a dictionary")

    @abstractmethod
    def convert(self, parsed_diagram: Dict, options: Dict = None) -> Dict:
        """
        Convert parsed diagram to target platform

        Args:
            parsed_diagram: Dictionary containing parsed Mermaid diagram
            options: Optional conversion settings

        Returns:
            Dictionary with conversion results including URL and metadata
        """
        pass

    @abstractmethod
    def test_connection(self) -> Dict:
        """
        Test connection to target platform

        Returns:
            Dictionary with test results
        """
        pass

    def get_supported_diagram_types(self) -> list:
        """
        Get list of supported diagram types for this converter

        Returns:
            List of supported diagram type strings
        """
        return ['flowchart', 'sequence']  # Default supported types

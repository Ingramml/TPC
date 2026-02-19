"""
Shared XML helper utilities for TPC Pipeline.
Extracted from TPC_grants2.py and income_expense_fixed.py to eliminate duplication.
"""

import xml.etree.ElementTree as ET
from typing import Optional

IRS_NAMESPACE = "{http://www.irs.gov/efile}"


def safe_find_element(root, xpath: str, alternative_xpath: str = None) -> Optional[ET.Element]:
    """
    Safely find an element with fallback options.

    Args:
        root: XML root element
        xpath: Primary XPath expression
        alternative_xpath: Alternative XPath expression

    Returns:
        Element if found, None otherwise
    """
    element = root.find(xpath)
    if element is not None:
        return element

    if alternative_xpath:
        return root.find(alternative_xpath)

    return None


def get_element_text(element: Optional[ET.Element], default: str = '') -> str:
    """
    Safely get text from an element.

    Args:
        element: XML element
        default: Default value if element is None or has no text

    Returns:
        Element text or default value
    """
    if element is not None and element.text:
        return element.text
    return default

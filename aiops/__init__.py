"""
AIOps Framework - AI-Powered DevOps Automation

A comprehensive framework for integrating AI/LLM capabilities into DevOps workflows.
"""

__version__ = "0.1.0"
__author__ = "AIOps Team"

from aiops.core.config import Config
from aiops.core.llm_factory import LLMFactory

__all__ = ["Config", "LLMFactory", "__version__"]

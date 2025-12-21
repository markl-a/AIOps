"""Centralized prompt generation for agents."""
from typing import Optional, Dict, Any


class AgentPromptGenerator:
    """Centralized prompt generator to reduce code duplication across agents."""

    AGENT_TEMPLATES = {
        "code_reviewer": "You are an expert code reviewer...",
        "test_generator": "You are an expert test engineer...",
        "security_scanner": "You are a security expert...",
        "log_analyzer": "You are an expert log analyst...",
        "performance_analyzer": "You are a performance optimization expert...",
    }

    @classmethod
    def create_system_prompt(
        cls,
        agent_type: str,
        language: str = "",
        context: str = "",
        custom_instructions: str = ""
    ) -> str:
        """Create a system prompt for the specified agent type.

        Args:
            agent_type: Type of agent (e.g., 'code_reviewer', 'test_generator')
            language: Programming language context
            context: Additional context
            custom_instructions: Custom instructions to append

        Returns:
            Formatted system prompt string
        """
        base_template = cls.AGENT_TEMPLATES.get(
            agent_type,
            "You are an expert AI assistant."
        )

        prompt_parts = [base_template]

        if language:
            prompt_parts.append(f"Focus on {language} code.")

        if context:
            prompt_parts.append(f"Context: {context}")

        if custom_instructions:
            prompt_parts.append(custom_instructions)

        return "\n\n".join(prompt_parts)

    @classmethod
    def create_user_prompt(
        cls,
        content: str,
        task_description: str = "",
        output_format: str = ""
    ) -> str:
        """Create a user prompt with the content to analyze.

        Args:
            content: The main content (code, logs, etc.)
            task_description: Description of what to do
            output_format: Expected output format

        Returns:
            Formatted user prompt string
        """
        prompt_parts = []

        if task_description:
            prompt_parts.append(f"Task: {task_description}")

        prompt_parts.append(f"Content:\n```\n{content}\n```")

        if output_format:
            prompt_parts.append(f"Please provide output in {output_format} format.")

        return "\n\n".join(prompt_parts)

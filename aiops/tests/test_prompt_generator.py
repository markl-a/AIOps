"""
Unit tests for Agent Prompt Generator
"""

import pytest
from aiops.agents.prompt_generator import AgentPromptGenerator


class TestAgentPromptGenerator:
    """Tests for AgentPromptGenerator"""

    def test_create_system_prompt_code_reviewer(self):
        """Test system prompt for code reviewer"""
        prompt = AgentPromptGenerator.create_system_prompt("code_reviewer")

        assert "code reviewer" in prompt.lower()

    def test_create_system_prompt_test_generator(self):
        """Test system prompt for test generator"""
        prompt = AgentPromptGenerator.create_system_prompt("test_generator")

        assert "test" in prompt.lower()

    def test_create_system_prompt_security_scanner(self):
        """Test system prompt for security scanner"""
        prompt = AgentPromptGenerator.create_system_prompt("security_scanner")

        assert "security" in prompt.lower()

    def test_create_system_prompt_log_analyzer(self):
        """Test system prompt for log analyzer"""
        prompt = AgentPromptGenerator.create_system_prompt("log_analyzer")

        assert "log" in prompt.lower()

    def test_create_system_prompt_performance_analyzer(self):
        """Test system prompt for performance analyzer"""
        prompt = AgentPromptGenerator.create_system_prompt("performance_analyzer")

        assert "performance" in prompt.lower()

    def test_create_system_prompt_unknown_type(self):
        """Test system prompt for unknown agent type"""
        prompt = AgentPromptGenerator.create_system_prompt("unknown_agent")

        # Should return default
        assert "AI assistant" in prompt

    def test_create_system_prompt_with_language(self):
        """Test system prompt with language context"""
        prompt = AgentPromptGenerator.create_system_prompt(
            "code_reviewer",
            language="Python"
        )

        assert "Python" in prompt
        assert "Focus on" in prompt

    def test_create_system_prompt_with_context(self):
        """Test system prompt with additional context"""
        prompt = AgentPromptGenerator.create_system_prompt(
            "code_reviewer",
            context="This is a web application"
        )

        assert "Context:" in prompt
        assert "web application" in prompt

    def test_create_system_prompt_with_custom_instructions(self):
        """Test system prompt with custom instructions"""
        prompt = AgentPromptGenerator.create_system_prompt(
            "code_reviewer",
            custom_instructions="Focus on security vulnerabilities"
        )

        assert "security vulnerabilities" in prompt

    def test_create_system_prompt_with_all_options(self):
        """Test system prompt with all options"""
        prompt = AgentPromptGenerator.create_system_prompt(
            agent_type="code_reviewer",
            language="TypeScript",
            context="React application",
            custom_instructions="Pay attention to hooks usage"
        )

        assert "TypeScript" in prompt
        assert "React application" in prompt
        assert "hooks usage" in prompt

    def test_create_user_prompt_basic(self):
        """Test basic user prompt creation"""
        prompt = AgentPromptGenerator.create_user_prompt(
            content="def hello(): pass"
        )

        assert "def hello(): pass" in prompt
        assert "```" in prompt  # Code block formatting

    def test_create_user_prompt_with_task(self):
        """Test user prompt with task description"""
        prompt = AgentPromptGenerator.create_user_prompt(
            content="code here",
            task_description="Review this code for bugs"
        )

        assert "Task:" in prompt
        assert "Review this code for bugs" in prompt

    def test_create_user_prompt_with_output_format(self):
        """Test user prompt with output format specification"""
        prompt = AgentPromptGenerator.create_user_prompt(
            content="code here",
            output_format="JSON"
        )

        assert "JSON" in prompt
        assert "format" in prompt.lower()

    def test_create_user_prompt_with_all_options(self):
        """Test user prompt with all options"""
        prompt = AgentPromptGenerator.create_user_prompt(
            content="function test() { return 1; }",
            task_description="Analyze this JavaScript function",
            output_format="markdown"
        )

        assert "function test()" in prompt
        assert "Analyze this JavaScript function" in prompt
        assert "markdown" in prompt

    def test_agent_templates_exist(self):
        """Test that all expected templates exist"""
        expected_templates = [
            "code_reviewer",
            "test_generator",
            "security_scanner",
            "log_analyzer",
            "performance_analyzer"
        ]

        for template_name in expected_templates:
            assert template_name in AgentPromptGenerator.AGENT_TEMPLATES

    def test_agent_templates_not_empty(self):
        """Test that templates are not empty"""
        for template_name, template in AgentPromptGenerator.AGENT_TEMPLATES.items():
            assert template is not None
            assert len(template) > 0
            assert isinstance(template, str)

    def test_prompt_parts_joined_correctly(self):
        """Test that prompt parts are joined with double newlines"""
        prompt = AgentPromptGenerator.create_system_prompt(
            "code_reviewer",
            language="Python",
            context="Test context"
        )

        # Should have double newline separators
        assert "\n\n" in prompt

    def test_empty_language_not_added(self):
        """Test that empty language doesn't add text"""
        prompt = AgentPromptGenerator.create_system_prompt(
            "code_reviewer",
            language=""
        )

        assert "Focus on  code" not in prompt

    def test_empty_context_not_added(self):
        """Test that empty context doesn't add text"""
        prompt = AgentPromptGenerator.create_system_prompt(
            "code_reviewer",
            context=""
        )

        assert "Context:" not in prompt

    def test_empty_custom_instructions_not_added(self):
        """Test that empty custom instructions don't add text"""
        prompt = AgentPromptGenerator.create_system_prompt(
            "code_reviewer",
            custom_instructions=""
        )

        # Should not have trailing separator
        parts = prompt.split("\n\n")
        assert parts[-1].strip() != ""

    def test_user_prompt_empty_content(self):
        """Test user prompt with empty content"""
        prompt = AgentPromptGenerator.create_user_prompt(content="")

        assert "```" in prompt
        # Content section should still exist

    def test_user_prompt_multiline_content(self):
        """Test user prompt with multiline content"""
        content = """def function1():
    pass

def function2():
    return True
"""
        prompt = AgentPromptGenerator.create_user_prompt(content=content)

        assert "function1" in prompt
        assert "function2" in prompt


class TestAgentPromptGeneratorEdgeCases:
    """Edge case tests"""

    def test_special_characters_in_content(self):
        """Test handling of special characters in content"""
        content = "def test(): print('Hello \"World\"')"
        prompt = AgentPromptGenerator.create_user_prompt(content=content)

        assert "Hello" in prompt
        assert "World" in prompt

    def test_unicode_in_content(self):
        """Test handling of unicode characters"""
        content = "# 日本語コメント\ndef test(): pass"
        prompt = AgentPromptGenerator.create_user_prompt(content=content)

        assert "日本語" in prompt

    def test_very_long_content(self):
        """Test with very long content"""
        content = "def f(): pass\n" * 1000
        prompt = AgentPromptGenerator.create_user_prompt(content=content)

        assert prompt is not None
        assert len(prompt) > 1000

    def test_case_sensitivity_agent_type(self):
        """Test that agent type is case sensitive"""
        prompt_lower = AgentPromptGenerator.create_system_prompt("code_reviewer")
        prompt_upper = AgentPromptGenerator.create_system_prompt("CODE_REVIEWER")

        # Upper case should return default
        assert "AI assistant" in prompt_upper
        assert "code reviewer" in prompt_lower.lower()

    def test_multiple_calls_independence(self):
        """Test that multiple calls don't affect each other"""
        prompt1 = AgentPromptGenerator.create_system_prompt(
            "code_reviewer",
            language="Python"
        )
        prompt2 = AgentPromptGenerator.create_system_prompt(
            "security_scanner",
            context="AWS"
        )

        assert "Python" in prompt1
        assert "Python" not in prompt2
        assert "AWS" in prompt2
        assert "AWS" not in prompt1

    def test_none_values_handled(self):
        """Test that None values don't cause errors (if passed explicitly)"""
        # Default parameters should be empty strings, not None
        # but we test the behavior
        prompt = AgentPromptGenerator.create_system_prompt(
            "code_reviewer",
            language="",
            context="",
            custom_instructions=""
        )

        assert prompt is not None
        assert "code reviewer" in prompt.lower()

    def test_whitespace_in_parameters(self):
        """Test handling of whitespace in parameters"""
        prompt = AgentPromptGenerator.create_system_prompt(
            "code_reviewer",
            language="  Python  ",
            context="  Web app  "
        )

        # Whitespace should be preserved as passed
        assert "Python" in prompt
        assert "Web app" in prompt

    def test_backticks_in_content(self):
        """Test handling of backticks in content (edge case for markdown)"""
        content = "```python\ncode\n```"
        prompt = AgentPromptGenerator.create_user_prompt(content=content)

        # Should still work (though formatting might be weird)
        assert prompt is not None

    def test_user_prompt_empty_task_not_added(self):
        """Test that empty task description doesn't add Task: line"""
        prompt = AgentPromptGenerator.create_user_prompt(
            content="code",
            task_description=""
        )

        assert "Task:" not in prompt

    def test_user_prompt_empty_format_not_added(self):
        """Test that empty output format doesn't add format line"""
        prompt = AgentPromptGenerator.create_user_prompt(
            content="code",
            output_format=""
        )

        assert "format" not in prompt.lower()

    def test_classmethod_behavior(self):
        """Test that methods work as classmethods"""
        # Should be callable on class, not instance
        prompt1 = AgentPromptGenerator.create_system_prompt("code_reviewer")
        prompt2 = AgentPromptGenerator.create_user_prompt("code")

        assert prompt1 is not None
        assert prompt2 is not None

        # Should also work if instantiated (though not needed)
        generator = AgentPromptGenerator()
        prompt3 = generator.create_system_prompt("code_reviewer")
        assert prompt3 is not None

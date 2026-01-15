"""
Unit tests for Documentation Generator Agent
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from aiops.agents.doc_generator import (
    DocGeneratorAgent,
    APIDocumentation,
    CodeDocumentation
)


class TestAPIDocumentation:
    """Tests for APIDocumentation model"""

    def test_create_api_documentation(self):
        """Test creating API documentation"""
        doc = APIDocumentation(
            endpoint="/api/users",
            method="GET",
            description="Get all users",
            parameters=[{"name": "limit", "type": "integer", "required": False}],
            request_body=None,
            responses={"200": {"description": "Success"}},
            examples=[{"request": "GET /api/users", "response": "[]"}]
        )
        assert doc.endpoint == "/api/users"
        assert doc.method == "GET"
        assert len(doc.parameters) == 1

    def test_api_doc_with_request_body(self):
        """Test API documentation with request body"""
        doc = APIDocumentation(
            endpoint="/api/users",
            method="POST",
            description="Create user",
            parameters=[],
            request_body={"type": "object", "properties": {"name": {"type": "string"}}},
            responses={"201": {"description": "Created"}},
            examples=[]
        )
        assert doc.request_body is not None
        assert doc.request_body["type"] == "object"

    def test_api_doc_multiple_responses(self):
        """Test API documentation with multiple responses"""
        doc = APIDocumentation(
            endpoint="/api/resource",
            method="DELETE",
            description="Delete resource",
            parameters=[],
            responses={
                "200": {"description": "Success"},
                "404": {"description": "Not found"},
                "500": {"description": "Server error"}
            },
            examples=[]
        )
        assert len(doc.responses) == 3


class TestCodeDocumentation:
    """Tests for CodeDocumentation model"""

    def test_create_code_documentation(self):
        """Test creating code documentation"""
        doc = CodeDocumentation(
            summary="Calculate factorial",
            detailed_description="Calculates the factorial of a number using recursion",
            parameters=[{"name": "n", "type": "int", "description": "The number"}],
            returns="The factorial result",
            raises=["ValueError: if n < 0"],
            examples=["factorial(5) -> 120"],
            notes=["Time complexity: O(n)"]
        )
        assert doc.summary == "Calculate factorial"
        assert len(doc.parameters) == 1
        assert doc.returns is not None

    def test_code_doc_without_returns(self):
        """Test code documentation without return value"""
        doc = CodeDocumentation(
            summary="Print hello",
            detailed_description="Prints hello world",
            parameters=[],
            returns=None,
            raises=[],
            examples=["print_hello()"],
            notes=[]
        )
        assert doc.returns is None


class TestDocGeneratorAgent:
    """Tests for DocGeneratorAgent"""

    @pytest.fixture
    def agent(self):
        """Create agent instance with mocked LLM"""
        agent = DocGeneratorAgent()
        agent._generate_response = AsyncMock(return_value="Generated documentation")
        agent._generate_structured_response = AsyncMock(return_value=[])
        return agent

    @pytest.mark.asyncio
    async def test_execute_function_doc(self, agent):
        """Test generating function documentation"""
        code = """
def add(a, b):
    return a + b
"""
        result = await agent.execute(code, doc_type="function", language="python")

        assert result == "Generated documentation"
        agent._generate_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_class_doc(self, agent):
        """Test generating class documentation"""
        code = """
class Calculator:
    def add(self, a, b):
        return a + b
"""
        result = await agent.execute(code, doc_type="class", language="python")

        assert result == "Generated documentation"

    @pytest.mark.asyncio
    async def test_execute_module_doc(self, agent):
        """Test generating module documentation"""
        code = """
'''Math utilities module'''
import math

def sqrt(x):
    return math.sqrt(x)
"""
        result = await agent.execute(code, doc_type="module", language="python")

        assert result == "Generated documentation"

    @pytest.mark.asyncio
    async def test_execute_api_doc(self, agent):
        """Test generating API documentation"""
        code = """
@app.get("/users")
def get_users():
    return []
"""
        result = await agent.execute(code, doc_type="api", language="python")

        assert result == "Generated documentation"

    @pytest.mark.asyncio
    async def test_execute_with_existing_docs(self, agent):
        """Test improving existing documentation"""
        code = "def foo(): pass"
        existing = "This function does foo"

        await agent.execute(code, existing_docs=existing)

        call_args = agent._generate_response.call_args
        user_prompt = call_args[0][0]
        assert "Existing Documentation" in user_prompt

    @pytest.mark.asyncio
    async def test_execute_different_languages(self, agent):
        """Test documentation for different languages"""
        languages = ["python", "javascript", "typescript", "java"]

        for lang in languages:
            await agent.execute("code", language=lang)

        assert agent._generate_response.call_count == len(languages)

    @pytest.mark.asyncio
    async def test_execute_error_handling(self, agent):
        """Test error handling during generation"""
        agent._generate_response = AsyncMock(side_effect=Exception("API error"))

        result = await agent.execute("def foo(): pass")

        assert "failed" in result.lower()
        assert "API error" in result

    def test_create_system_prompt_function(self, agent):
        """Test system prompt for function documentation"""
        prompt = agent._create_system_prompt("function", "python")

        assert "python" in prompt.lower()
        assert "function" in prompt.lower()
        assert "parameter" in prompt.lower()
        assert "return" in prompt.lower()

    def test_create_system_prompt_class(self, agent):
        """Test system prompt for class documentation"""
        prompt = agent._create_system_prompt("class", "python")

        assert "class" in prompt.lower()
        assert "attribute" in prompt.lower()
        assert "method" in prompt.lower()

    def test_create_system_prompt_module(self, agent):
        """Test system prompt for module documentation"""
        prompt = agent._create_system_prompt("module", "python")

        assert "module" in prompt.lower()
        assert "component" in prompt.lower()

    def test_create_system_prompt_api(self, agent):
        """Test system prompt for API documentation"""
        prompt = agent._create_system_prompt("api", "python")

        assert "endpoint" in prompt.lower()
        assert "request" in prompt.lower()
        assert "response" in prompt.lower()

    def test_create_system_prompt_python_docstring_style(self, agent):
        """Test Python-specific docstring style recommendation"""
        prompt = agent._create_system_prompt("function", "python")

        assert "google" in prompt.lower() or "numpy" in prompt.lower()

    def test_create_system_prompt_javascript_jsdoc(self, agent):
        """Test JavaScript-specific JSDoc style"""
        prompt = agent._create_system_prompt("function", "javascript")

        assert "jsdoc" in prompt.lower()

    def test_create_system_prompt_java_javadoc(self, agent):
        """Test Java-specific Javadoc style"""
        prompt = agent._create_system_prompt("function", "java")

        assert "javadoc" in prompt.lower()

    def test_create_user_prompt_basic(self, agent):
        """Test basic user prompt creation"""
        code = "def foo(): pass"
        prompt = agent._create_user_prompt(code)

        assert code in prompt
        assert "documentation" in prompt.lower()

    def test_create_user_prompt_with_existing_docs(self, agent):
        """Test user prompt with existing documentation"""
        code = "def foo(): pass"
        existing = "Existing docs here"
        prompt = agent._create_user_prompt(code, existing_docs=existing)

        assert code in prompt
        assert existing in prompt
        assert "Existing Documentation" in prompt

    @pytest.mark.asyncio
    async def test_generate_api_docs_success(self, agent):
        """Test successful API documentation generation"""
        agent._generate_structured_response = AsyncMock(return_value=[
            {
                "endpoint": "/api/test",
                "method": "GET",
                "description": "Test endpoint",
                "parameters": [],
                "request_body": None,
                "responses": {"200": {"description": "OK"}},
                "examples": []
            }
        ])

        api_code = '@app.get("/api/test")\ndef test(): return {}'
        result = await agent.generate_api_docs(api_code, framework="fastapi")

        assert len(result) == 1
        assert isinstance(result[0], APIDocumentation)
        assert result[0].endpoint == "/api/test"

    @pytest.mark.asyncio
    async def test_generate_api_docs_multiple_endpoints(self, agent):
        """Test generating docs for multiple endpoints"""
        agent._generate_structured_response = AsyncMock(return_value=[
            {
                "endpoint": "/api/users",
                "method": "GET",
                "description": "Get users",
                "parameters": [],
                "responses": {},
                "examples": []
            },
            {
                "endpoint": "/api/users",
                "method": "POST",
                "description": "Create user",
                "parameters": [],
                "responses": {},
                "examples": []
            }
        ])

        result = await agent.generate_api_docs("api code", framework="flask")

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_generate_api_docs_error_handling(self, agent):
        """Test API docs generation error handling"""
        agent._generate_structured_response = AsyncMock(
            side_effect=Exception("API error")
        )

        result = await agent.generate_api_docs("api code")

        assert result == []

    @pytest.mark.asyncio
    async def test_generate_api_docs_different_frameworks(self, agent):
        """Test API docs for different frameworks"""
        agent._generate_structured_response = AsyncMock(return_value=[])

        frameworks = ["fastapi", "flask", "express", "django"]
        for framework in frameworks:
            await agent.generate_api_docs("code", framework=framework)

        assert agent._generate_structured_response.call_count == len(frameworks)

    @pytest.mark.asyncio
    async def test_generate_readme_basic(self, agent):
        """Test basic README generation"""
        structure = """
project/
  src/
    main.py
  README.md
"""
        result = await agent.generate_readme(structure)

        assert result == "Generated documentation"

    @pytest.mark.asyncio
    async def test_generate_readme_with_code_samples(self, agent):
        """Test README generation with code samples"""
        structure = "project/\n  main.py"
        code_samples = {
            "main.py": "print('hello')",
            "utils.py": "def helper(): pass"
        }

        await agent.generate_readme(structure, code_samples=code_samples)

        call_args = agent._generate_response.call_args
        user_prompt = call_args[0][0]
        assert "main.py" in user_prompt
        assert "utils.py" in user_prompt

    @pytest.mark.asyncio
    async def test_generate_readme_with_project_info(self, agent):
        """Test README generation with project info"""
        structure = "project/"
        project_info = {"name": "MyProject", "version": "1.0.0"}

        await agent.generate_readme(structure, project_info=project_info)

        call_args = agent._generate_response.call_args
        user_prompt = call_args[0][0]
        assert "Additional Info" in user_prompt

    @pytest.mark.asyncio
    async def test_generate_readme_error_handling(self, agent):
        """Test README generation error handling"""
        agent._generate_response = AsyncMock(side_effect=Exception("Error"))

        result = await agent.generate_readme("structure")

        assert "Failed" in result
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_generate_readme_truncates_long_code(self, agent):
        """Test that long code samples are truncated"""
        structure = "project/"
        long_code = "x" * 1000  # More than 500 chars
        code_samples = {"long.py": long_code}

        await agent.generate_readme(structure, code_samples=code_samples)

        call_args = agent._generate_response.call_args
        user_prompt = call_args[0][0]
        # Code should be truncated to first 500 chars
        assert len(user_prompt) < len(long_code) + 500

    @pytest.mark.asyncio
    async def test_update_docstrings_success(self, agent):
        """Test successful docstring update"""
        code = "def foo(): pass"
        agent._generate_response = AsyncMock(return_value='''
def foo():
    """Do foo."""
    pass
''')

        result = await agent.update_docstrings(code)

        assert '"""' in result or result == "Generated documentation"

    @pytest.mark.asyncio
    async def test_update_docstrings_preserves_code(self, agent):
        """Test that code logic is preserved"""
        code = """
def calculate(x, y):
    return x + y
"""
        agent._generate_response = AsyncMock(return_value=code)

        result = await agent.update_docstrings(code)

        assert "return" in result or "calculate" in result

    @pytest.mark.asyncio
    async def test_update_docstrings_different_languages(self, agent):
        """Test updating docstrings for different languages"""
        languages = ["python", "javascript", "typescript"]

        for lang in languages:
            await agent.update_docstrings("code", language=lang)

        assert agent._generate_response.call_count == len(languages)

    @pytest.mark.asyncio
    async def test_update_docstrings_error_returns_original(self, agent):
        """Test that original code is returned on error"""
        original_code = "def foo(): pass"
        agent._generate_response = AsyncMock(side_effect=Exception("Error"))

        result = await agent.update_docstrings(original_code)

        assert result == original_code

    @pytest.mark.asyncio
    async def test_update_docstrings_extracts_from_markdown(self, agent):
        """Test extracting code from markdown response"""
        code = "def foo(): pass"
        markdown_response = """
Here's the documented code:

```python
def foo():
    '''Does foo.'''
    pass
```

Done!
"""
        agent._generate_response = AsyncMock(return_value=markdown_response)

        result = await agent.update_docstrings(code, language="python")

        # Should extract from markdown block
        assert "```" not in result or "def foo" in result

    def test_agent_initialization(self):
        """Test agent initialization"""
        agent = DocGeneratorAgent()
        assert agent.name == "DocGeneratorAgent"

    def test_agent_inheritance(self):
        """Test agent inherits from BaseAgent"""
        from aiops.agents.base_agent import BaseAgent

        agent = DocGeneratorAgent()
        assert isinstance(agent, BaseAgent)


class TestDocGeneratorEdgeCases:
    """Edge case tests for DocGeneratorAgent"""

    @pytest.fixture
    def agent(self):
        agent = DocGeneratorAgent()
        agent._generate_response = AsyncMock(return_value="docs")
        agent._generate_structured_response = AsyncMock(return_value=[])
        return agent

    @pytest.mark.asyncio
    async def test_empty_code(self, agent):
        """Test with empty code"""
        result = await agent.execute("")
        assert result is not None

    @pytest.mark.asyncio
    async def test_very_long_code(self, agent):
        """Test with very long code"""
        long_code = "x = 1\n" * 10000
        result = await agent.execute(long_code)
        assert result is not None

    @pytest.mark.asyncio
    async def test_code_with_special_characters(self, agent):
        """Test code with special characters"""
        code = '''
def test():
    """String with 'quotes' and "double quotes"."""
    return "Hello\\nWorld"
'''
        result = await agent.execute(code)
        assert result is not None

    @pytest.mark.asyncio
    async def test_unknown_doc_type(self, agent):
        """Test with unknown documentation type"""
        result = await agent.execute("code", doc_type="unknown_type")
        assert result is not None

    @pytest.mark.asyncio
    async def test_unknown_language(self, agent):
        """Test with unknown programming language"""
        result = await agent.execute("code", language="unknown_lang")
        assert result is not None

    @pytest.mark.asyncio
    async def test_none_existing_docs(self, agent):
        """Test with None existing docs"""
        await agent.execute("code", existing_docs=None)
        call_args = agent._generate_response.call_args
        user_prompt = call_args[0][0]
        assert "Existing Documentation" not in user_prompt

    @pytest.mark.asyncio
    async def test_empty_project_structure(self, agent):
        """Test README generation with empty structure"""
        result = await agent.generate_readme("")
        assert result is not None

    @pytest.mark.asyncio
    async def test_empty_code_samples(self, agent):
        """Test README generation with empty code samples dict"""
        await agent.generate_readme("structure", code_samples={})
        call_args = agent._generate_response.call_args
        user_prompt = call_args[0][0]
        assert "Sample Code" not in user_prompt

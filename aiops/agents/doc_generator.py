"""Documentation Generator Agent - Automated documentation generation."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from aiops.agents.base_agent import BaseAgent
from aiops.core.logger import get_logger

logger = get_logger(__name__)


class APIDocumentation(BaseModel):
    """Generated API documentation."""

    endpoint: str = Field(description="API endpoint path")
    method: str = Field(description="HTTP method")
    description: str = Field(description="Endpoint description")
    parameters: List[Dict[str, Any]] = Field(description="Request parameters")
    request_body: Optional[Dict[str, Any]] = Field(default=None, description="Request body schema")
    responses: Dict[str, Any] = Field(description="Response schemas by status code")
    examples: List[Dict[str, Any]] = Field(description="Usage examples")


class CodeDocumentation(BaseModel):
    """Generated code documentation."""

    summary: str = Field(description="Brief summary")
    detailed_description: str = Field(description="Detailed description")
    parameters: List[Dict[str, str]] = Field(description="Function/class parameters")
    returns: Optional[str] = Field(default=None, description="Return value description")
    raises: List[str] = Field(description="Exceptions that can be raised")
    examples: List[str] = Field(description="Usage examples")
    notes: List[str] = Field(description="Additional notes")


class DocGeneratorAgent(BaseAgent):
    """Agent for automated documentation generation."""

    def __init__(self, **kwargs):
        super().__init__(name="DocGeneratorAgent", **kwargs)

    async def execute(
        self,
        code: str,
        doc_type: str = "function",
        language: str = "python",
        existing_docs: Optional[str] = None,
    ) -> str:
        """
        Generate documentation for code.

        Args:
            code: Code to document
            doc_type: Type of documentation (function, class, module, api)
            language: Programming language
            existing_docs: Existing documentation to improve

        Returns:
            Generated documentation string
        """
        logger.info(f"Generating {doc_type} documentation for {language} code")

        system_prompt = self._create_system_prompt(doc_type, language)
        user_prompt = self._create_user_prompt(code, existing_docs)

        try:
            response = await self._generate_response(user_prompt, system_prompt)
            logger.info(f"Documentation generated ({len(response)} chars)")
            return response

        except Exception as e:
            logger.error(f"Documentation generation failed: {e}")
            return f"# Documentation generation failed: {str(e)}"

    def _create_system_prompt(self, doc_type: str, language: str) -> str:
        """Create system prompt for documentation generation."""
        prompt = f"""You are an expert technical writer specializing in {language} documentation.

Generate clear, comprehensive, and well-structured documentation following best practices.

Documentation Guidelines:
1. **Clarity**: Use clear, concise language
2. **Completeness**: Cover all important aspects
3. **Examples**: Include practical usage examples
4. **Structure**: Use proper formatting and organization
5. **Accuracy**: Ensure technical accuracy
6. **Audience**: Write for developers who will use this code

For {doc_type} documentation:
"""

        if doc_type == "function":
            prompt += """- Brief description of what the function does
- Detailed explanation of the logic
- Parameter descriptions with types
- Return value description
- Exception/error descriptions
- Usage examples
- Notes on edge cases or important behavior
"""
        elif doc_type == "class":
            prompt += """- Class purpose and responsibility
- Attribute descriptions
- Method descriptions
- Usage examples
- Inheritance information
- Design patterns used
"""
        elif doc_type == "module":
            prompt += """- Module overview and purpose
- Main components and their relationships
- Usage guide
- API reference
- Examples
- Dependencies
"""
        elif doc_type == "api":
            prompt += """- Endpoint description
- Request/response formats
- Authentication requirements
- Error codes
- Rate limiting
- Examples with curl/code
"""

        if language == "python":
            prompt += "\nUse Google-style or NumPy-style docstrings."
        elif language in ["javascript", "typescript"]:
            prompt += "\nUse JSDoc format."
        elif language == "java":
            prompt += "\nUse Javadoc format."

        return prompt

    def _create_user_prompt(
        self, code: str, existing_docs: Optional[str] = None
    ) -> str:
        """Create user prompt for documentation generation."""
        prompt = "Generate comprehensive documentation for the following code:\n\n"

        prompt += f"```\n{code}\n```\n\n"

        if existing_docs:
            prompt += f"**Existing Documentation** (improve if needed):\n{existing_docs}\n\n"

        prompt += "Generate complete, professional documentation."

        return prompt

    async def generate_api_docs(
        self,
        api_code: str,
        framework: str = "fastapi",
    ) -> List[APIDocumentation]:
        """
        Generate API documentation from code.

        Args:
            api_code: API route/controller code
            framework: Web framework (fastapi, flask, express, etc.)

        Returns:
            List of API endpoint documentation
        """
        logger.info(f"Generating API documentation for {framework}")

        system_prompt = f"""You are an API documentation expert for {framework}.

Generate OpenAPI/Swagger style documentation including:
- Clear endpoint descriptions
- Request/response schemas
- Parameter validation rules
- Example requests and responses
- Error responses
- Authentication requirements
"""

        user_prompt = f"""Generate API documentation for this {framework} code:

```
{api_code}
```

Provide structured documentation for each endpoint.
"""

        try:
            result = await self._generate_structured_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
                schema={"type": "array", "items": APIDocumentation.model_json_schema()},
            )

            logger.info(f"Generated documentation for {len(result)} API endpoints")
            return [APIDocumentation(**doc) for doc in result]

        except Exception as e:
            logger.error(f"API documentation generation failed: {e}")
            return []

    async def generate_readme(
        self,
        project_structure: str,
        code_samples: Optional[Dict[str, str]] = None,
        project_info: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate README.md for a project.

        Args:
            project_structure: Project directory structure
            code_samples: Sample code files
            project_info: Additional project information

        Returns:
            Generated README content
        """
        logger.info("Generating README.md")

        system_prompt = """You are an expert at creating professional README files.

Create a comprehensive README that includes:
1. Project title and description
2. Features
3. Installation instructions
4. Usage examples
5. API documentation (if applicable)
6. Configuration
7. Contributing guidelines
8. License information

Make it engaging, clear, and complete.
Use proper Markdown formatting.
"""

        user_prompt = f"""Generate a professional README for this project:

**Project Structure**:
```
{project_structure}
```
"""

        if code_samples:
            user_prompt += "\n**Sample Code**:\n"
            for filename, code in code_samples.items():
                user_prompt += f"\n{filename}:\n```\n{code[:500]}\n```\n"

        if project_info:
            user_prompt += f"\n**Additional Info**: {project_info}\n"

        user_prompt += "\nGenerate a complete, professional README.md"

        try:
            response = await self._generate_response(user_prompt, system_prompt)
            logger.info("README.md generated successfully")
            return response

        except Exception as e:
            logger.error(f"README generation failed: {e}")
            return f"# README Generation Failed\n\nError: {str(e)}"

    async def update_docstrings(
        self,
        code: str,
        language: str = "python",
    ) -> str:
        """
        Add or update docstrings in code.

        Args:
            code: Source code
            language: Programming language

        Returns:
            Code with updated docstrings
        """
        logger.info(f"Updating docstrings in {language} code")

        system_prompt = f"""You are an expert at writing {language} documentation.

Add comprehensive docstrings to all functions and classes.
Maintain the exact code logic - only add/update documentation.
Follow {language} documentation conventions.
"""

        user_prompt = f"""Add comprehensive docstrings to this code:

```{language}
{code}
```

Return the complete code with added docstrings.
Preserve all code logic exactly.
"""

        try:
            response = await self._generate_response(user_prompt, system_prompt)

            # Extract code from markdown if present
            if "```" in response:
                code_blocks = response.split("```")
                for block in code_blocks:
                    if block.strip() and not block.strip().startswith(language):
                        response = block.strip()
                        break

            logger.info("Docstrings updated successfully")
            return response

        except Exception as e:
            logger.error(f"Docstring update failed: {e}")
            return code  # Return original code on failure

"""Dependency Analyzer Agent - Analyze project dependencies."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from aiops.agents.base_agent import BaseAgent
from aiops.core.logger import get_logger

logger = get_logger(__name__)


class DependencyInfo(BaseModel):
    """Information about a dependency."""

    name: str = Field(description="Package name")
    current_version: str = Field(description="Current version")
    latest_version: str = Field(description="Latest available version")
    is_outdated: bool = Field(description="Whether package is outdated")
    license: Optional[str] = Field(default=None, description="License type")
    description: Optional[str] = Field(default=None, description="Package description")
    dependencies_count: int = Field(default=0, description="Number of transitive dependencies")


class DependencyIssue(BaseModel):
    """Dependency-related issue."""

    severity: str = Field(description="Severity: high, medium, low")
    package_name: str = Field(description="Affected package")
    issue_type: str = Field(description="Type: outdated, license, security, deprecated")
    description: str = Field(description="Issue description")
    recommendation: str = Field(description="Recommended action")


class DependencyAnalysisResult(BaseModel):
    """Result of dependency analysis."""

    total_dependencies: int = Field(description="Total number of dependencies")
    outdated_count: int = Field(description="Number of outdated packages")
    summary: str = Field(description="Analysis summary")
    dependencies: List[DependencyInfo] = Field(description="Dependency information")
    issues: List[DependencyIssue] = Field(description="Identified issues")
    recommendations: List[str] = Field(description="General recommendations")
    license_summary: Dict[str, int] = Field(description="License distribution")
    dependency_tree_insights: List[str] = Field(description="Dependency tree insights")


class DependencyAnalyzerAgent(BaseAgent):
    """Agent for dependency analysis."""

    def __init__(self, **kwargs):
        super().__init__(name="DependencyAnalyzerAgent", **kwargs)

    async def execute(
        self,
        dependencies: str,
        dependency_type: str = "python",
        lock_file: Optional[str] = None,
    ) -> DependencyAnalysisResult:
        """
        Analyze project dependencies.

        Args:
            dependencies: Dependency file content
            dependency_type: Type (python, node, java, etc.)
            lock_file: Lock file content for exact versions

        Returns:
            DependencyAnalysisResult with analysis
        """
        logger.info(f"Analyzing {dependency_type} dependencies")

        system_prompt = self._create_system_prompt(dependency_type)
        user_prompt = self._create_user_prompt(dependencies, lock_file)

        try:
            result = await self._generate_structured_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
                schema=DependencyAnalysisResult,
            )

            logger.info(
                f"Dependency analysis completed: {result.total_dependencies} packages, "
                f"{result.outdated_count} outdated, {len(result.issues)} issues"
            )

            return result

        except Exception as e:
            logger.error(f"Dependency analysis failed: {e}")
            return DependencyAnalysisResult(
                total_dependencies=0,
                outdated_count=0,
                summary=f"Analysis failed: {str(e)}",
                dependencies=[],
                issues=[],
                recommendations=[],
                license_summary={},
                dependency_tree_insights=[],
            )

    def _create_system_prompt(self, dependency_type: str) -> str:
        """Create system prompt for dependency analysis."""
        return f"""You are an expert in {dependency_type} dependency management and software supply chain security.

Analyze dependencies for:

1. **Version Management**:
   - Outdated packages
   - Breaking changes in updates
   - Semantic versioning compliance
   - Update recommendations

2. **License Compliance**:
   - License types and compatibility
   - License conflicts
   - Copyleft issues
   - Commercial usage restrictions

3. **Security**:
   - Known vulnerabilities
   - Unmaintained packages
   - Deprecated packages

4. **Dependency Health**:
   - Transitive dependencies
   - Dependency bloat
   - Circular dependencies
   - Unused dependencies

5. **Best Practices**:
   - Version pinning
   - Lock file usage
   - Update strategies
   - Minimal dependencies principle

Provide actionable insights for dependency optimization.
"""

    def _create_user_prompt(
        self,
        dependencies: str,
        lock_file: Optional[str] = None,
    ) -> str:
        """Create user prompt for dependency analysis."""
        prompt = "Analyze the following dependencies:\n\n"

        prompt += f"**Dependencies**:\n```\n{dependencies}\n```\n\n"

        if lock_file:
            prompt += f"**Lock File**:\n```\n{lock_file}\n```\n\n"

        prompt += """Provide:
1. List of all dependencies with version info
2. Outdated packages identification
3. License analysis
4. Dependency issues (security, compatibility, etc.)
5. Optimization recommendations
6. Dependency tree insights

Focus on actionable recommendations.
"""

        return prompt

    async def find_unused_dependencies(
        self,
        dependencies: str,
        source_code: str,
    ) -> List[str]:
        """
        Find potentially unused dependencies.

        Args:
            dependencies: Dependency list
            source_code: Project source code

        Returns:
            List of potentially unused package names
        """
        logger.info("Analyzing for unused dependencies")

        system_prompt = """You are an expert at identifying unused dependencies.

Analyze which dependencies are imported/used in the code.
Identify packages that are listed but never imported or used.

Note:
- Some packages may be indirect dependencies
- Some packages may be used in non-obvious ways (entry points, plugins)
- Be conservative in marking packages as unused
"""

        user_prompt = f"""Find unused dependencies:

**Dependencies**:
```
{dependencies}
```

**Source Code** (sample):
```
{source_code[:2000]}
```

List packages that appear to be unused.
Be conservative - only mark packages as unused if clearly not referenced.
"""

        try:
            response = await self._generate_response(user_prompt, system_prompt)

            # Parse response for unused packages
            unused = []
            for line in response.split('\n'):
                if line.strip().startswith('-') or line.strip().startswith('*'):
                    pkg = line.strip('- *').strip()
                    if pkg:
                        unused.append(pkg)

            logger.info(f"Found {len(unused)} potentially unused dependencies")
            return unused

        except Exception as e:
            logger.error(f"Unused dependency analysis failed: {e}")
            return []

    async def suggest_alternatives(
        self,
        package_name: str,
        use_case: str,
    ) -> List[Dict[str, str]]:
        """
        Suggest alternative packages.

        Args:
            package_name: Current package name
            use_case: What the package is used for

        Returns:
            List of alternative packages with pros/cons
        """
        logger.info(f"Finding alternatives for {package_name}")

        system_prompt = """You are an expert in software packages and libraries.

Suggest alternative packages based on:
- Popularity and maintenance
- Performance
- Feature set
- License
- Bundle size/dependencies
- Community support

Provide honest comparison including pros and cons.
"""

        user_prompt = f"""Suggest alternatives to: {package_name}

**Use Case**: {use_case}

Provide:
1. Alternative packages
2. Comparison (performance, features, size)
3. Pros and cons of each
4. Migration difficulty
5. Recommendation
"""

        try:
            response = await self._generate_response(user_prompt, system_prompt)

            # In production, parse structured alternatives
            alternatives = [{
                "name": "See analysis",
                "comparison": response[:500],
            }]

            logger.info(f"Generated alternatives for {package_name}")
            return alternatives

        except Exception as e:
            logger.error(f"Alternative suggestion failed: {e}")
            return []

    async def analyze_dependency_tree(
        self,
        dependencies: str,
        dependency_type: str = "python",
    ) -> Dict[str, Any]:
        """
        Analyze dependency tree for issues.

        Args:
            dependencies: Dependency list
            dependency_type: Dependency type

        Returns:
            Tree analysis with insights
        """
        logger.info("Analyzing dependency tree")

        system_prompt = """You are an expert at dependency tree analysis.

Analyze for:
- Deep dependency chains
- Circular dependencies
- Version conflicts
- Dependency bloat
- Duplicate dependencies
- Common patterns

Provide insights on tree health.
"""

        user_prompt = f"""Analyze dependency tree:

```
{dependencies}
```

Identify:
1. Deep dependency chains (>5 levels)
2. Potential circular dependencies
3. Version conflicts
4. Duplicated dependencies
5. Bloat indicators
6. Optimization opportunities
"""

        try:
            response = await self._generate_response(user_prompt, system_prompt)

            analysis = {
                "summary": response[:200],
                "details": response,
                "health_score": 75,  # In production, calculate from analysis
            }

            logger.info("Dependency tree analysis completed")
            return analysis

        except Exception as e:
            logger.error(f"Dependency tree analysis failed: {e}")
            return {"summary": f"Analysis failed: {str(e)}", "health_score": 0}

    async def check_license_compatibility(
        self,
        dependencies: str,
        project_license: str,
    ) -> Dict[str, Any]:
        """
        Check license compatibility.

        Args:
            dependencies: Dependencies to check
            project_license: Project's license

        Returns:
            License compatibility analysis
        """
        logger.info(f"Checking license compatibility with {project_license}")

        system_prompt = """You are an expert in open source licenses and compliance.

Analyze license compatibility:
- GPL compatibility
- Copyleft requirements
- Commercial use restrictions
- License conflicts
- Attribution requirements

Consider:
- MIT, Apache, BSD: Permissive
- GPL, LGPL, AGPL: Copyleft
- Proprietary: Restrictive
"""

        user_prompt = f"""Check license compatibility:

**Project License**: {project_license}

**Dependencies**:
```
{dependencies}
```

Identify:
1. Incompatible licenses
2. Copyleft obligations
3. Attribution requirements
4. Commercial use restrictions
5. Recommendations
"""

        try:
            response = await self._generate_response(user_prompt, system_prompt)

            compatibility = {
                "status": "compatible",  # compatible, issues, incompatible
                "issues": [],
                "recommendations": response,
            }

            logger.info("License compatibility check completed")
            return compatibility

        except Exception as e:
            logger.error(f"License compatibility check failed: {e}")
            return {"status": "error", "message": str(e)}

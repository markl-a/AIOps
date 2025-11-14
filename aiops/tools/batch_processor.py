"""Batch processing tools for multiple files/projects."""

import asyncio
from pathlib import Path
from typing import List, Dict, Any, Callable, Optional
from concurrent.futures import ThreadPoolExecutor
from aiops.core.logger import get_logger

logger = get_logger(__name__)


class BatchProcessor:
    """Batch processor for running agents on multiple files."""

    def __init__(self, max_concurrent: int = 5):
        """
        Initialize batch processor.

        Args:
            max_concurrent: Maximum concurrent operations
        """
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def process_files(
        self,
        files: List[Path],
        processor_func: Callable,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """
        Process multiple files in batch.

        Args:
            files: List of file paths
            processor_func: Async function to process each file
            **kwargs: Additional arguments for processor function

        Returns:
            List of results
        """
        logger.info(f"Processing {len(files)} files in batch...")

        tasks = []
        for file_path in files:
            task = self._process_single_file(file_path, processor_func, **kwargs)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successes and failures
        successes = sum(1 for r in results if not isinstance(r, Exception))
        failures = len(results) - successes

        logger.info(f"Batch processing complete: {successes} success, {failures} failures")

        return [
            r if not isinstance(r, Exception) else {"error": str(r), "file": files[i]}
            for i, r in enumerate(results)
        ]

    async def _process_single_file(
        self,
        file_path: Path,
        processor_func: Callable,
        **kwargs,
    ) -> Dict[str, Any]:
        """Process a single file with semaphore."""
        async with self.semaphore:
            try:
                logger.debug(f"Processing {file_path}...")

                # Read file
                content = file_path.read_text()

                # Process with function
                result = await processor_func(code=content, **kwargs)

                return {
                    "file": str(file_path),
                    "result": result,
                    "success": True,
                }

            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                return {
                    "file": str(file_path),
                    "error": str(e),
                    "success": False,
                }

    async def review_project(
        self,
        project_path: Path,
        language: str = "python",
        exclude_patterns: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Review all files in a project.

        Args:
            project_path: Project root path
            language: Programming language
            exclude_patterns: Patterns to exclude

        Returns:
            Aggregated review results
        """
        from aiops.agents.code_reviewer import CodeReviewAgent

        logger.info(f"Reviewing project at {project_path}")

        # Find all source files
        if language == "python":
            pattern = "**/*.py"
        elif language in ["javascript", "typescript"]:
            pattern = "**/*.{js,ts}"
        else:
            pattern = f"**/*.{language}"

        files = list(project_path.glob(pattern))

        # Apply exclusions
        if exclude_patterns:
            files = [
                f
                for f in files
                if not any(pattern in str(f) for pattern in exclude_patterns)
            ]

        logger.info(f"Found {len(files)} files to review")

        # Process files
        agent = CodeReviewAgent()
        results = await self.process_files(
            files, agent.execute, language=language
        )

        # Aggregate results
        total_issues = 0
        critical_issues = 0
        avg_score = 0
        successful_reviews = 0

        for result in results:
            if result.get("success"):
                review = result["result"]
                total_issues += len(review.issues)
                critical_issues += sum(
                    1 for issue in review.issues if issue.severity == "critical"
                )
                avg_score += review.overall_score
                successful_reviews += 1

        if successful_reviews > 0:
            avg_score /= successful_reviews

        return {
            "project_path": str(project_path),
            "files_reviewed": successful_reviews,
            "total_files": len(files),
            "average_score": avg_score,
            "total_issues": total_issues,
            "critical_issues": critical_issues,
            "results": results,
        }

    async def generate_tests_bulk(
        self,
        source_files: List[Path],
        output_dir: Path,
        language: str = "python",
    ) -> Dict[str, Any]:
        """
        Generate tests for multiple files.

        Args:
            source_files: Source files to generate tests for
            output_dir: Output directory for tests
            language: Programming language

        Returns:
            Generation results
        """
        from aiops.agents.test_generator import TestGeneratorAgent

        logger.info(f"Generating tests for {len(source_files)} files")

        output_dir.mkdir(parents=True, exist_ok=True)
        agent = TestGeneratorAgent()

        results = await self.process_files(
            source_files, agent.execute, language=language
        )

        # Save generated tests
        saved_count = 0
        for i, result in enumerate(results):
            if result.get("success"):
                test_suite = result["result"]
                source_file = source_files[i]

                # Generate test file name
                test_file = output_dir / f"test_{source_file.name}"

                # Write tests
                with open(test_file, "w") as f:
                    if test_suite.setup_code:
                        f.write(test_suite.setup_code + "\n\n")

                    for test_case in test_suite.test_cases:
                        f.write(f"# {test_case.name}\n")
                        f.write(f"{test_case.test_code}\n\n")

                saved_count += 1
                logger.info(f"Saved tests to {test_file}")

        return {
            "files_processed": len(source_files),
            "tests_generated": saved_count,
            "output_dir": str(output_dir),
        }

    async def analyze_dependencies(
        self,
        project_path: Path,
    ) -> Dict[str, Any]:
        """
        Analyze all dependency files in a project.

        Args:
            project_path: Project root path

        Returns:
            Dependency analysis results
        """
        from aiops.agents.dependency_analyzer import DependencyAnalyzerAgent

        logger.info(f"Analyzing dependencies in {project_path}")

        # Find dependency files
        dep_files = {
            "python": ["requirements.txt", "Pipfile", "pyproject.toml"],
            "node": ["package.json"],
            "java": ["pom.xml", "build.gradle"],
        }

        found_deps = []
        for lang, files in dep_files.items():
            for file_name in files:
                dep_file = project_path / file_name
                if dep_file.exists():
                    found_deps.append((dep_file, lang))

        if not found_deps:
            logger.warning("No dependency files found")
            return {"error": "No dependency files found"}

        # Analyze each dependency file
        agent = DependencyAnalyzerAgent()
        results = []

        for dep_file, dep_type in found_deps:
            content = dep_file.read_text()
            result = await agent.execute(
                dependencies=content,
                dependency_type=dep_type,
            )
            results.append({
                "file": str(dep_file),
                "type": dep_type,
                "analysis": result,
            })

        return {
            "project_path": str(project_path),
            "dependency_files": len(found_deps),
            "results": results,
        }

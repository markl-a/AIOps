"""Project scanner for comprehensive analysis."""

from pathlib import Path
from typing import Dict, Any, List, Optional
import json
from aiops.core.logger import get_logger

logger = get_logger(__name__)


class ProjectScanner:
    """Scanner for project-wide analysis."""

    def __init__(self, project_path: Path):
        """
        Initialize project scanner.

        Args:
            project_path: Root path of the project
        """
        self.project_path = Path(project_path)

    def get_project_structure(self) -> Dict[str, Any]:
        """Get project structure analysis."""
        logger.info(f"Scanning project structure: {self.project_path}")

        structure = {
            "root": str(self.project_path),
            "directories": [],
            "files_by_type": {},
            "total_files": 0,
            "total_lines": 0,
        }

        # Walk directory tree
        for path in self.project_path.rglob("*"):
            # Skip hidden and common excluded directories
            if any(
                part.startswith(".")
                or part in ["node_modules", "venv", "__pycache__", "dist", "build"]
                for part in path.parts
            ):
                continue

            if path.is_file():
                ext = path.suffix or "no_extension"

                # Count files by type
                if ext not in structure["files_by_type"]:
                    structure["files_by_type"][ext] = {
                        "count": 0,
                        "total_lines": 0,
                        "files": [],
                    }

                structure["files_by_type"][ext]["count"] += 1
                structure["files_by_type"][ext]["files"].append(str(path.relative_to(self.project_path)))

                # Count lines for text files
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = len(f.readlines())
                        structure["files_by_type"][ext]["total_lines"] += lines
                        structure["total_lines"] += lines
                except Exception:
                    pass

                structure["total_files"] += 1

            elif path.is_dir():
                structure["directories"].append(str(path.relative_to(self.project_path)))

        return structure

    def identify_project_type(self) -> Dict[str, Any]:
        """Identify project type and framework."""
        logger.info("Identifying project type...")

        indicators = {
            "python": [
                "setup.py",
                "pyproject.toml",
                "requirements.txt",
                "Pipfile",
            ],
            "node": ["package.json", "yarn.lock", "package-lock.json"],
            "java": ["pom.xml", "build.gradle", "gradle.build"],
            "rust": ["Cargo.toml"],
            "go": ["go.mod"],
            "ruby": ["Gemfile"],
            "php": ["composer.json"],
        }

        frameworks = {
            "python": {
                "django": ["manage.py", "settings.py"],
                "flask": ["app.py", "wsgi.py"],
                "fastapi": ["main.py"],
            },
            "node": {
                "react": ["src/App.jsx", "src/App.tsx"],
                "vue": ["vue.config.js"],
                "express": ["server.js", "app.js"],
            },
        }

        detected = {
            "languages": [],
            "frameworks": [],
            "confidence": {},
        }

        # Check for language indicators
        for lang, files in indicators.items():
            found = sum(1 for f in files if (self.project_path / f).exists())
            if found > 0:
                detected["languages"].append(lang)
                detected["confidence"][lang] = found / len(files)

        # Check for frameworks
        for lang, fw_indicators in frameworks.items():
            if lang in detected["languages"]:
                for framework, files in fw_indicators.items():
                    if any((self.project_path / f).exists() for f in files):
                        detected["frameworks"].append(f"{lang}/{framework}")

        return detected

    def find_test_files(self) -> List[Path]:
        """Find all test files in the project."""
        test_patterns = [
            "**/test_*.py",
            "**/*_test.py",
            "**/tests/**/*.py",
            "**/*.spec.js",
            "**/*.spec.ts",
            "**/*.test.js",
            "**/*.test.ts",
        ]

        test_files = []
        for pattern in test_patterns:
            test_files.extend(self.project_path.glob(pattern))

        return list(set(test_files))  # Remove duplicates

    def calculate_test_coverage_potential(self) -> Dict[str, Any]:
        """Estimate test coverage potential."""
        logger.info("Calculating test coverage potential...")

        # Find source and test files
        test_files = self.find_test_files()

        # Find source files (simplified)
        source_files = list(self.project_path.glob("**/*.py"))  # Example for Python
        source_files = [
            f
            for f in source_files
            if "test" not in str(f) and "venv" not in str(f)
        ]

        return {
            "source_files": len(source_files),
            "test_files": len(test_files),
            "files_without_tests": len(source_files) - len(test_files),
            "coverage_ratio": len(test_files) / len(source_files) if source_files else 0,
        }

    def find_security_sensitive_files(self) -> List[Path]:
        """Find files that might contain sensitive information."""
        sensitive_patterns = [
            "**/.env",
            "**/.env.*",
            "**/secrets.json",
            "**/credentials.json",
            "**/config.json",
            "**/*.key",
            "**/*.pem",
        ]

        sensitive_files = []
        for pattern in sensitive_patterns:
            sensitive_files.extend(self.project_path.glob(pattern))

        return sensitive_files

    def generate_project_report(self) -> str:
        """Generate comprehensive project report."""
        logger.info("Generating project report...")

        structure = self.get_project_structure()
        project_type = self.identify_project_type()
        test_coverage = self.calculate_test_coverage_potential()
        sensitive_files = self.find_security_sensitive_files()

        report = f"""# Project Analysis Report

## Project: {self.project_path.name}

### Overview
- **Total Files**: {structure['total_files']}
- **Total Lines of Code**: {structure['total_lines']:,}
- **Directories**: {len(structure['directories'])}

### Project Type
**Languages**: {', '.join(project_type['languages']) if project_type['languages'] else 'Unknown'}
**Frameworks**: {', '.join(project_type['frameworks']) if project_type['frameworks'] else 'None detected'}

### File Distribution

"""

        for ext, data in sorted(
            structure['files_by_type'].items(), key=lambda x: x[1]['count'], reverse=True
        )[:10]:
            report += f"- **{ext}**: {data['count']} files, {data['total_lines']:,} lines\n"

        report += f"""

### Test Coverage Analysis
- **Source Files**: {test_coverage['source_files']}
- **Test Files**: {test_coverage['test_files']}
- **Files Without Tests**: {test_coverage['files_without_tests']}
- **Coverage Ratio**: {test_coverage['coverage_ratio']:.1%}

"""

        if sensitive_files:
            report += f"""
### Security Notes
⚠️ Found {len(sensitive_files)} potentially sensitive files:
"""
            for f in sensitive_files[:10]:
                report += f"- {f.relative_to(self.project_path)}\n"

        return report

    def export_analysis(self, output_file: Path):
        """Export analysis to JSON file."""
        analysis = {
            "structure": self.get_project_structure(),
            "project_type": self.identify_project_type(),
            "test_coverage": self.calculate_test_coverage_potential(),
            "sensitive_files": [str(f) for f in self.find_security_sensitive_files()],
        }

        with open(output_file, "w") as f:
            json.dump(analysis, f, indent=2)

        logger.info(f"Analysis exported to {output_file}")

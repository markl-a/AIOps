"""Main CLI application for AIOps framework."""

import asyncio
import sys
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

from aiops.core.config import get_config
from aiops.core.logger import setup_logger
from aiops.agents.code_reviewer import CodeReviewAgent
from aiops.agents.test_generator import TestGeneratorAgent
from aiops.agents.log_analyzer import LogAnalyzerAgent
from aiops.agents.cicd_optimizer import CICDOptimizerAgent
from aiops.agents.doc_generator import DocGeneratorAgent
from aiops.agents.performance_analyzer import PerformanceAnalyzerAgent
from aiops.agents.anomaly_detector import AnomalyDetectorAgent
from aiops.agents.auto_fixer import AutoFixerAgent
from aiops.agents.intelligent_monitor import IntelligentMonitorAgent

app = typer.Typer(
    name="aiops",
    help="AI-powered DevOps automation framework",
    add_completion=False,
)
console = Console()


def read_file(file_path: str) -> str:
    """Read file contents."""
    try:
        return Path(file_path).read_text()
    except Exception as e:
        console.print(f"[red]Error reading file {file_path}: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def review(
    file_path: str = typer.Argument(..., help="Path to code file to review"),
    language: str = typer.Option("python", help="Programming language"),
    provider: Optional[str] = typer.Option(None, help="LLM provider (openai/anthropic)"),
):
    """Review code for issues and provide feedback."""
    console.print(f"[cyan]Reviewing {file_path}...[/cyan]")

    code = read_file(file_path)
    agent = CodeReviewAgent(llm_provider=provider)

    result = asyncio.run(agent.execute(code=code, language=language))

    # Display results
    console.print(Panel(f"[bold]Code Review Results[/bold]\n\n{result.summary}"))
    console.print(f"\n[bold]Overall Score:[/bold] {result.overall_score}/100\n")

    if result.issues:
        table = Table(title="Issues Found")
        table.add_column("Severity", style="cyan")
        table.add_column("Category", style="magenta")
        table.add_column("Description", style="white")

        for issue in result.issues:
            table.add_row(issue.severity, issue.category, issue.description[:80])

        console.print(table)

    if result.strengths:
        console.print("\n[bold green]Strengths:[/bold green]")
        for strength in result.strengths:
            console.print(f"  ✓ {strength}")

    if result.recommendations:
        console.print("\n[bold yellow]Recommendations:[/bold yellow]")
        for rec in result.recommendations:
            console.print(f"  • {rec}")


@app.command()
def generate_tests(
    file_path: str = typer.Argument(..., help="Path to code file"),
    language: str = typer.Option("python", help="Programming language"),
    framework: Optional[str] = typer.Option(None, help="Test framework"),
    output: Optional[str] = typer.Option(None, help="Output file path"),
    provider: Optional[str] = typer.Option(None, help="LLM provider"),
):
    """Generate tests for code."""
    console.print(f"[cyan]Generating tests for {file_path}...[/cyan]")

    code = read_file(file_path)
    agent = TestGeneratorAgent(llm_provider=provider)

    result = asyncio.run(
        agent.execute(code=code, language=language, test_framework=framework)
    )

    console.print(f"\n[bold]Generated {len(result.test_cases)} test cases[/bold]\n")

    # Display test cases
    for i, test in enumerate(result.test_cases, 1):
        console.print(f"\n[cyan]Test {i}: {test.name}[/cyan]")
        console.print(f"Type: {test.test_type} | Priority: {test.priority}")
        console.print(f"Description: {test.description}")
        console.print(f"\n```{language}\n{test.test_code}\n```")

    if output:
        with open(output, "w") as f:
            if result.setup_code:
                f.write(f"{result.setup_code}\n\n")
            for test in result.test_cases:
                f.write(f"# {test.name}\n")
                f.write(f"{test.test_code}\n\n")
        console.print(f"\n[green]Tests saved to {output}[/green]")


@app.command()
def analyze_logs(
    file_path: str = typer.Argument(..., help="Path to log file"),
    focus: Optional[str] = typer.Option(None, help="Focus areas (comma-separated)"),
    provider: Optional[str] = typer.Option(None, help="LLM provider"),
):
    """Analyze logs and provide insights."""
    console.print(f"[cyan]Analyzing logs from {file_path}...[/cyan]")

    logs = read_file(file_path)
    agent = LogAnalyzerAgent(llm_provider=provider)

    focus_areas = focus.split(",") if focus else None
    result = asyncio.run(agent.execute(logs=logs, focus_areas=focus_areas))

    console.print(Panel(f"[bold]Log Analysis[/bold]\n\n{result.summary}"))

    if result.insights:
        table = Table(title="Key Insights")
        table.add_column("Severity", style="cyan")
        table.add_column("Category", style="magenta")
        table.add_column("Message", style="white")

        for insight in result.insights:
            table.add_row(insight.severity, insight.category, insight.message[:60])

        console.print(table)

    if result.root_causes:
        console.print("\n[bold red]Root Causes:[/bold red]")
        for rc in result.root_causes:
            console.print(f"\n  • {rc.root_cause} (confidence: {rc.confidence}%)")
            console.print(f"    Evidence: {', '.join(rc.evidence[:2])}")

    if result.recommendations:
        console.print("\n[bold yellow]Recommendations:[/bold yellow]")
        for rec in result.recommendations:
            console.print(f"  • {rec}")


@app.command()
def optimize_pipeline(
    config_path: str = typer.Argument(..., help="Path to pipeline config"),
    logs_path: Optional[str] = typer.Option(None, help="Path to pipeline logs"),
    provider: Optional[str] = typer.Option(None, help="LLM provider"),
):
    """Optimize CI/CD pipeline."""
    console.print(f"[cyan]Optimizing pipeline {config_path}...[/cyan]")

    config = read_file(config_path)
    logs = read_file(logs_path) if logs_path else None

    agent = CICDOptimizerAgent(llm_provider=provider)
    result = asyncio.run(agent.execute(pipeline_config=config, pipeline_logs=logs))

    if result.current_duration and result.estimated_duration:
        improvement = (
            (result.current_duration - result.estimated_duration)
            / result.current_duration
            * 100
        )
        console.print(
            f"\n[bold]Estimated Improvement:[/bold] {improvement:.1f}% faster "
            f"({result.current_duration:.1f}m → {result.estimated_duration:.1f}m)\n"
        )

    if result.issues:
        console.print("[bold red]Issues:[/bold red]")
        for issue in result.issues:
            console.print(f"\n  [{issue.severity}] {issue.stage}: {issue.description}")
            console.print(f"  Solution: {issue.solution}")

    if result.optimizations:
        console.print("\n[bold green]Optimizations:[/bold green]")
        for opt in result.optimizations:
            console.print(f"  • {opt}")


@app.command()
def generate_docs(
    file_path: str = typer.Argument(..., help="Path to code file"),
    doc_type: str = typer.Option("function", help="Documentation type"),
    language: str = typer.Option("python", help="Programming language"),
    output: Optional[str] = typer.Option(None, help="Output file path"),
    provider: Optional[str] = typer.Option(None, help="LLM provider"),
):
    """Generate documentation for code."""
    console.print(f"[cyan]Generating {doc_type} documentation for {file_path}...[/cyan]")

    code = read_file(file_path)
    agent = DocGeneratorAgent(llm_provider=provider)

    result = asyncio.run(
        agent.execute(code=code, doc_type=doc_type, language=language)
    )

    console.print("\n[bold]Generated Documentation:[/bold]\n")
    console.print(result)

    if output:
        with open(output, "w") as f:
            f.write(result)
        console.print(f"\n[green]Documentation saved to {output}[/green]")


@app.command()
def analyze_performance(
    file_path: str = typer.Argument(..., help="Path to code file"),
    language: str = typer.Option("python", help="Programming language"),
    provider: Optional[str] = typer.Option(None, help="LLM provider"),
):
    """Analyze code performance."""
    console.print(f"[cyan]Analyzing performance of {file_path}...[/cyan]")

    code = read_file(file_path)
    agent = PerformanceAnalyzerAgent(llm_provider=provider)

    result = asyncio.run(agent.execute(code=code, language=language))

    console.print(
        f"\n[bold]Performance Score:[/bold] {result.overall_score}/100\n"
    )
    console.print(Panel(result.summary))

    if result.issues:
        table = Table(title="Performance Issues")
        table.add_column("Severity", style="cyan")
        table.add_column("Category", style="magenta")
        table.add_column("Issue", style="white")

        for issue in result.issues:
            table.add_row(issue.severity, issue.category, issue.description[:60])

        console.print(table)

    if result.optimizations:
        console.print("\n[bold green]Priority Optimizations:[/bold green]")
        for opt in result.optimizations:
            console.print(f"  • {opt}")


@app.command()
def version():
    """Show version information."""
    from aiops import __version__

    console.print(f"[bold cyan]AIOps Framework[/bold cyan] version {__version__}")


def main():
    """Main entry point."""
    setup_logger()
    app()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import argparse
import os
import sys
import time
import subprocess
import questionary
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from rich import print as rprint
from termcolor import colored

# Import Interceptor and Map
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src.interceptor import ReasoningInterceptor, AGENT_MAP
from src.visualization import get_visualizer

console = Console()
client = ReasoningInterceptor()

MODEL_NAME = "gemma3:latest"

def get_ollama_models():
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
        lines = result.stdout.strip().split('\n')[1:] # Skip header
        models = [line.split()[0] for line in lines if line.strip()]
        return models
    except:
        return ["gemma3:latest", "gemma3:270m", "llama3"]

def select_model_panel():
    global MODEL_NAME
    models = get_ollama_models()
    
    selected = questionary.select(
        "Select AI Model:",
        choices=models,
        default=MODEL_NAME
    ).ask()
    
    if selected:
        MODEL_NAME = selected
        console.print(f"[green]Model set to: {MODEL_NAME}[/green]")


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    clear_screen()
    console.print(Panel.fit(
        "[bold cyan]AGENT REASONING CLI[/bold cyan]\n[dim]Advanced Cognitive Architectures (Gemma 3)[/dim]",
        border_style="cyan"
    ))
    console.print(f"[dim]Working Directory: {os.getcwd()}[/dim]\n")

from rich.live import Live
from rich.markdown import Markdown

def run_agent_chat(strategy):
    print_header()
    console.print(f"[bold yellow]Chat Mode: {strategy.upper()}[/bold yellow]")
    console.print("Type 'exit' or '0' to return.")

    while True:
        query = Prompt.ask("\n[bold green]Query[/bold green]")
        if query.lower() in ['exit', 'quit', '0']:
            break

        full_model_name = f"{MODEL_NAME}+{strategy}"
        console.print(f"[dim]Using model: {full_model_name}[/dim]")
        console.print(f"[bold cyan]--- {strategy.upper()} Thinking ---[/bold cyan]")

        # Check if visualizer exists for this strategy
        visualizer = get_visualizer(strategy)

        if visualizer:
            # Use structured event streaming with visualizer
            run_with_visualizer(strategy, query, visualizer)
        else:
            # Fallback to legacy text streaming
            run_with_markdown(strategy, query)


def run_with_visualizer(strategy, query, visualizer):
    """Run agent with rich visualization using structured events."""
    # Get agent directly from map
    agent_class = AGENT_MAP.get(strategy)
    if not agent_class:
        console.print(f"[red]Unknown strategy: {strategy}[/red]")
        return

    agent = agent_class(model=MODEL_NAME)

    # Check if agent has stream_structured method
    if not hasattr(agent, 'stream_structured'):
        console.print("[dim]Agent does not support structured streaming, falling back to text mode.[/dim]")
        run_with_markdown(strategy, query)
        return

    try:
        with Live(visualizer.render(), refresh_per_second=10) as live:
            for event in agent.stream_structured(query):
                visualizer.update(event)
                live.update(visualizer.render())
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")


def run_with_markdown(strategy, query):
    """Fallback: Run agent with simple markdown rendering."""
    full_model_name = f"{MODEL_NAME}+{strategy}"
    full_response = ""

    with Live("", refresh_per_second=10) as live:
        try:
            for chunk_dict in client.generate(model=full_model_name, prompt=query, stream=True):
                chunk = chunk_dict.get("response", "")
                full_response += chunk
                live.update(Markdown(full_response))
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")


def run_arena_mode():
    print_header()
    console.print("[bold yellow]⚔️  ARENA MODE ⚔️[/bold yellow]")
    console.print("Run the same query across ALL agents to compare reasoning styles.")
    
    query = Prompt.ask("\n[bold green]Enter Test Query[/bold green]")
    if not query:
        return

    # Filter unique strategies roughly
    strategies = ["standard", "cot", "tot", "react", "recursive", "reflection", "refinement", "complex_refinement", "decomposed", "least_to_most", "consistency"]
    
    results = {}
    
    for strategy in strategies:
        console.print(f"\n[bold magenta]Running {strategy.upper()}...[/bold magenta]")
        full_model_name = f"{MODEL_NAME}+{strategy}"
        
        start_time = time.time()
        response_text = ""
        
        console.rule(f"[bold]{strategy}[/bold]")
        
        try:
             # Streaming with Live Display
             with Live("", refresh_per_second=10) as live:
                for chunk_dict in client.generate(model=full_model_name, prompt=query, stream=True):
                     chunk = chunk_dict.get("response", "")
                     response_text += chunk
                     live.update(Markdown(response_text))
                     
        except Exception as e:
            response_text = f"Error: {e}"
            console.print(f"[red]{e}[/red]")
            
        duration = time.time() - start_time
        # For the table, we might want just the final answer if parsing is possible,
        # but for now, raw text is fine.
        results[strategy] = (response_text, duration)
        console.print(f"\n[green]Done in {duration:.2f}s[/green]")

    # Summary Table
    console.print("\n\n")
    console.rule("[bold red]Comparison Results[/bold red]")
    
    table = Table(title="Arena Results")
    table.add_column("Strategy", style="cyan")
    table.add_column("Time", style="green")
    table.add_column("Response Length", style="magenta")
    
    for strat, (resp, dur) in results.items():
        table.add_row(strat, f"{dur:.2f}s", str(len(resp)))
        
    console.print(table)
    
    # Save Report Option
    if Confirm.ask("Save Arena Report?"):
        with open("arena_report.md", "w") as f:
            f.write(f"# Arena Report\n**Model**: {MODEL_NAME}\n**Query**: {query}\n\n")
            for strat, (resp, dur) in results.items():
                f.write(f"## {strat.upper()} ({dur:.2f}s)\n{resp}\n\n")
        console.print("[green]Saved to arena_report.md[/green]")

def run_refinement_demo(interactive=False):
    """
    Demo showcasing the Refinement Loop agent.
    Writes an article and iteratively improves it to be more technical.
    Runs for 5 iterations to demonstrate score-based refinement.

    Args:
        interactive: If True, asks user for a query. If False, uses the default demo query.
    """
    print_header()
    console.print("[bold yellow]🔄 REFINEMENT LOOP AGENT[/bold yellow]")
    console.print("This agent iteratively improves content using score-based feedback.")
    console.print("Generator → Critic (score 0.0-1.0) → Refiner → Loop until threshold met\n")

    # Import the agent directly for custom configuration
    from src.agents.refinement_loop import RefinementLoopAgent

    if interactive:
        # Ask user for query
        query = Prompt.ask("\n[bold green]Query (or press Enter for demo)[/bold green]")
        if not query.strip():
            interactive = False  # Fall back to demo

    if not interactive:
        # Use default demo query
        query = """Write a brief technical article (2-3 paragraphs) explaining how neural networks learn.
The article should be suitable for a technical blog and include specific details about:
- Backpropagation algorithm
- Gradient descent optimization
- Loss functions

Make it technically accurate and precise."""

        console.print(Panel(query, title="[bold cyan]Demo Query: Technical Article on Neural Networks[/bold cyan]", border_style="cyan"))
        console.print()

    # Create agent with 5 iterations for demo, high threshold to ensure multiple refinements
    agent = RefinementLoopAgent(model=MODEL_NAME, score_threshold=0.99, max_iterations=5)

    console.print(f"[dim]Using model: {MODEL_NAME}+refinement (max 5 iterations, threshold=0.99)[/dim]")
    console.print(f"[bold cyan]--- REFINEMENT LOOP Running ---[/bold cyan]\n")

    # Check if visualizer is available
    visualizer = get_visualizer("refinement")

    if visualizer and hasattr(agent, 'stream_structured'):
        try:
            with Live(visualizer.render(), refresh_per_second=10) as live:
                for event in agent.stream_structured(query):
                    visualizer.update(event)
                    live.update(visualizer.render())
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
    else:
        # Fallback to text streaming
        full_response = ""
        with Live("", refresh_per_second=10) as live:
            try:
                for chunk in agent.stream(query):
                    full_response += chunk
                    live.update(Markdown(full_response))
            except Exception as e:
                console.print(f"[bold red]Error:[/bold red] {e}")

    console.print("\n[bold green]Demo Complete![/bold green]")
    console.print("[dim]This demonstrates how iterative refinement improves content quality through score-based feedback.[/dim]")
    input("\nPress Enter to return...")


def run_complex_refinement_demo():
    """
    Demo showcasing the Complex Refinement Pipeline agent.
    Runs an article through a 5-stage optimization pipeline:
    1. Technical Accuracy
    2. Structure & Clarity
    3. Technical Depth
    4. Examples & Analogies
    5. Professional Polish
    """
    print_header()
    console.print("[bold magenta]🔄 COMPLEX REFINEMENT PIPELINE[/bold magenta]")
    console.print("This agent runs content through a 5-stage optimization pipeline.")
    console.print("Each stage has its own critic that evaluates and refines until threshold is met.\n")

    console.print("[bold]Pipeline Stages:[/bold]")
    console.print("  1. [cyan]Technical Accuracy[/cyan] - Ensure all facts are correct")
    console.print("  2. [cyan]Structure & Clarity[/cyan] - Improve organization and flow")
    console.print("  3. [cyan]Technical Depth[/cyan] - Add more details and formulas")
    console.print("  4. [cyan]Examples & Analogies[/cyan] - Add concrete illustrations")
    console.print("  5. [cyan]Professional Polish[/cyan] - Final editing pass\n")

    # Import the agent directly for custom configuration
    from src.agents.complex_refinement import ComplexRefinementLoopAgent

    # Use default demo query
    query = """Write a brief technical article (2-3 paragraphs) explaining how neural networks learn.
The article should be suitable for a technical blog and include specific details about:
- Backpropagation algorithm
- Gradient descent optimization
- Loss functions

Make it technically accurate and precise."""

    console.print(Panel(query, title="[bold cyan]Demo Query: Technical Article on Neural Networks[/bold cyan]", border_style="cyan"))
    console.print()

    # Create agent with threshold 0.9, max 3 iterations per stage
    agent = ComplexRefinementLoopAgent(model=MODEL_NAME, score_threshold=0.9, max_iterations_per_stage=3)

    console.print(f"[dim]Using model: {MODEL_NAME}+complex_refinement (5 stages, threshold=0.9, max 3 iter/stage)[/dim]")
    console.print(f"[bold magenta]--- COMPLEX REFINEMENT PIPELINE Running ---[/bold magenta]\n")

    # Text streaming (complex refinement uses rich text output)
    full_response = ""
    with Live("", refresh_per_second=10) as live:
        try:
            for chunk in agent.stream(query):
                full_response += chunk
                live.update(Markdown(full_response))
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")

    console.print("\n[bold green]Pipeline Complete![/bold green]")
    console.print("[dim]This demonstrates how multi-stage refinement progressively improves content through specialized critics.[/dim]")
    input("\nPress Enter to return...")


def run_benchmark_menu():
    """Benchmark submenu for running various benchmarks."""
    while True:
        print_header()
        console.print("[bold cyan]📊 BENCHMARK SUITE[/bold cyan]")
        console.print("Run performance benchmarks and generate reports.\n")

        choices = [
            questionary.Choice("🧠 Agent Reasoning Benchmark (All Strategies)", value="agent_all"),
            questionary.Choice("🧠 Agent Reasoning Benchmark (Select Tasks)", value="agent_select"),
            questionary.Choice("⚡ Inference Speed Benchmark (Ollama)", value="inference"),
            questionary.Choice("☁️  OCI vs Ollama Comparison", value="oci_comparison"),
            questionary.Choice("📈 View Last Report", value="view_report"),
            questionary.Choice("💾 Export Results to JSON", value="export"),
            questionary.Separator(),
            questionary.Choice("← Back to Main Menu", value="back"),
        ]

        choice = questionary.select(
            "Select Benchmark:",
            choices=choices,
            use_arrow_keys=True
        ).ask()

        if not choice or choice == "back":
            return
        elif choice == "agent_all":
            run_agent_benchmark(select_tasks=False)
        elif choice == "agent_select":
            run_agent_benchmark(select_tasks=True)
        elif choice == "inference":
            run_inference_benchmark()
        elif choice == "oci_comparison":
            run_oci_comparison_benchmark()
        elif choice == "view_report":
            view_benchmark_report()
        elif choice == "export":
            export_benchmark_results()


def run_agent_benchmark(select_tasks=False):
    """Run agent reasoning benchmarks with real-time output."""
    from src.benchmarks.runner import BenchmarkRunner, AGENT_BENCHMARK_TASKS

    print_header()
    console.print("[bold cyan]🧠 AGENT REASONING BENCHMARK[/bold cyan]\n")

    # Task selection
    if select_tasks:
        task_choices = [
            questionary.Choice(f"{t.name} ({t.category}) - {t.recommended_strategy}", value=t.id)
            for t in AGENT_BENCHMARK_TASKS
        ]
        selected_ids = questionary.checkbox(
            "Select tasks to run:",
            choices=task_choices,
        ).ask()

        if not selected_ids:
            console.print("[yellow]No tasks selected.[/yellow]")
            input("\nPress Enter to return...")
            return

        tasks = [t for t in AGENT_BENCHMARK_TASKS if t.id in selected_ids]
    else:
        tasks = AGENT_BENCHMARK_TASKS

    console.print(f"[dim]Running {len(tasks)} benchmark tasks with model: {MODEL_NAME}[/dim]\n")

    # Show task list
    task_table = Table(title="Benchmark Tasks", show_lines=True)
    task_table.add_column("Task", style="cyan")
    task_table.add_column("Category", style="green")
    task_table.add_column("Strategy", style="yellow")
    task_table.add_column("Status", style="white")

    task_status = {t.id: "⏳ Pending" for t in tasks}

    def render_task_table():
        table = Table(title="Benchmark Progress", show_lines=True)
        table.add_column("Task", style="cyan", width=25)
        table.add_column("Category", style="green", width=12)
        table.add_column("Strategy", style="yellow", width=15)
        table.add_column("Time (ms)", style="magenta", width=10)
        table.add_column("Status", style="white", width=15)

        for t in tasks:
            status = task_status.get(t.id, "⏳ Pending")
            time_str = "-"
            if isinstance(status, tuple):
                time_str = f"{status[1]:.0f}"
                status = status[0]
            table.add_row(t.name[:24], t.category, t.recommended_strategy, time_str, status)
        return table

    # Initialize runner
    runner = BenchmarkRunner(model=MODEL_NAME)

    # Run benchmarks with live updates
    with Live(render_task_table(), refresh_per_second=4) as live:
        def on_task_start(task, strategy):
            task_status[task.id] = "🔄 Running..."
            live.update(render_task_table())

        def on_task_complete(result):
            if result.success:
                task_status[result.task_id] = (f"✅ Done", result.total_ms)
            else:
                task_status[result.task_id] = (f"❌ Failed", 0)
            live.update(render_task_table())

        results = list(runner.run_agent_benchmark(
            tasks=tasks,
            on_task_start=on_task_start,
            on_task_complete=on_task_complete
        ))

    # Generate and display report
    report = runner.generate_report()

    console.print("\n" + "="*60)
    console.print("[bold green]BENCHMARK COMPLETE[/bold green]\n")

    summary_table = Table(title="Summary")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="green")
    summary_table.add_row("Total Tasks", str(report.total_tasks))
    summary_table.add_row("Successful", str(report.successful_tasks))
    summary_table.add_row("Failed", str(report.failed_tasks))
    summary_table.add_row("Avg Latency", f"{report.avg_latency_ms:.2f} ms")
    summary_table.add_row("Avg TTFT", f"{report.avg_ttft_ms:.2f} ms")
    summary_table.add_row("Avg TPS", f"{report.avg_tps:.2f}")
    console.print(summary_table)

    # Save report
    if Confirm.ask("\nSave report to file?"):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = f"benchmarks/agent_benchmark_{timestamp}.md"
        runner.save_report(filepath, format="markdown")
        console.print(f"[green]Report saved to {filepath}[/green]")

    input("\nPress Enter to return...")


def run_inference_benchmark():
    """Run raw inference speed benchmarks."""
    from src.benchmarks.runner import BenchmarkRunner, INFERENCE_BENCHMARK_PROMPTS

    print_header()
    console.print("[bold cyan]⚡ INFERENCE SPEED BENCHMARK[/bold cyan]\n")

    iterations = int(Prompt.ask("Iterations per prompt", default="3"))

    console.print(f"\n[dim]Running {len(INFERENCE_BENCHMARK_PROMPTS)} prompts x {iterations} iterations with model: {MODEL_NAME}[/dim]\n")

    runner = BenchmarkRunner(model=MODEL_NAME)
    results = []

    total = len(INFERENCE_BENCHMARK_PROMPTS) * iterations

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Running benchmarks...", total=total)

        def on_progress(current, total, prompt):
            progress.update(task, completed=current, description=f"[cyan]{prompt}...")

        for result in runner.run_inference_benchmark(iterations=iterations, on_progress=on_progress):
            results.append(result)

    # Calculate stats
    successful = [r for r in results if r.get("success")]
    if successful:
        avg_ttft = sum(r["ttft_ms"] for r in successful) / len(successful)
        avg_latency = sum(r["total_ms"] for r in successful) / len(successful)
        avg_tps = sum(r["tps"] for r in successful) / len(successful)
    else:
        avg_ttft = avg_latency = avg_tps = 0

    console.print("\n" + "="*60)
    console.print("[bold green]INFERENCE BENCHMARK COMPLETE[/bold green]\n")

    summary_table = Table(title="Inference Performance")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="green")
    summary_table.add_row("Model", MODEL_NAME)
    summary_table.add_row("Total Runs", str(len(results)))
    summary_table.add_row("Successful", str(len(successful)))
    summary_table.add_row("Avg TTFT", f"{avg_ttft:.2f} ms")
    summary_table.add_row("Avg Latency", f"{avg_latency:.2f} ms")
    summary_table.add_row("Avg TPS", f"{avg_tps:.2f}")
    console.print(summary_table)

    # Detailed results
    if Confirm.ask("\nShow detailed results?"):
        detail_table = Table(title="Detailed Results")
        detail_table.add_column("Prompt", style="cyan", width=40)
        detail_table.add_column("Iter", style="white")
        detail_table.add_column("TTFT (ms)", style="yellow")
        detail_table.add_column("Total (ms)", style="magenta")
        detail_table.add_column("TPS", style="green")

        for r in results[:20]:  # Show first 20
            if r.get("success"):
                detail_table.add_row(
                    r["prompt"][:38],
                    str(r["iteration"]),
                    f"{r['ttft_ms']:.0f}",
                    f"{r['total_ms']:.0f}",
                    f"{r['tps']:.1f}"
                )
        console.print(detail_table)

    # Save results
    if Confirm.ask("\nSave results to JSON?"):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = f"benchmarks/inference_benchmark_{timestamp}.json"
        import json
        with open(filepath, "w") as f:
            json.dump(results, f, indent=2)
        console.print(f"[green]Results saved to {filepath}[/green]")

    input("\nPress Enter to return...")


def run_oci_comparison_benchmark():
    """Run OCI vs Ollama comparison benchmark with live results display."""
    from src.benchmarks.runner import BenchmarkRunner, INFERENCE_BENCHMARK_PROMPTS, InferenceResult, ComparisonResult
    from dataclasses import asdict

    print_header()
    console.print("[bold cyan]☁️  MULTI-MODEL COMPARISON BENCHMARK[/bold cyan]\n")
    console.print("Compare inference performance: Ollama (7B) vs OCI GenAI vs Ollama (270M).\n")

    # Configuration
    iterations = int(Prompt.ask("Iterations per prompt", default="3"))

    # OCI Configuration
    console.print("\n[bold yellow]OCI Configuration:[/bold yellow]")

    oci_models = [
        questionary.Choice("Meta Llama 3.3 70B (Recommended)", value="meta.llama-3.3-70b-instruct"),
        questionary.Choice("Meta Llama 3.1 70B", value="meta.llama-3.1-70b-instruct"),
        questionary.Choice("Cohere Command R+ 08-2024", value="cohere.command-r-plus-08-2024"),
        questionary.Choice("Cohere Command R 08-2024", value="cohere.command-r-08-2024"),
        questionary.Choice("Google Gemini 2.5 Flash", value="google.gemini-2.5-flash"),
        questionary.Choice("XAI Grok 3 Fast", value="xai.grok-3-fast"),
    ]

    oci_model = questionary.select(
        "Select OCI model:",
        choices=oci_models,
        use_arrow_keys=True
    ).ask()

    if not oci_model:
        return

    # Check for OCI credentials - try config file first
    dry_run = False
    compartment_id = None
    oci_config = None
    oci_profile = "DEFAULT"

    # Try to load from ~/.oci/config
    try:
        import oci

        # Select OCI profile
        try:
            # Read available profiles from config file
            import configparser
            config_parser = configparser.ConfigParser()
            config_parser.read(os.path.expanduser("~/.oci/config"))
            profiles = config_parser.sections()
            if "DEFAULT" in config_parser:
                profiles = ["DEFAULT"] + profiles

            if len(profiles) > 1:
                profile_choices = [questionary.Choice(p, value=p) for p in profiles]
                oci_profile = questionary.select(
                    "Select OCI profile:",
                    choices=profile_choices,
                    default="foosball" if "foosball" in profiles else profiles[0]
                ).ask()
                if not oci_profile:
                    return
        except Exception:
            pass

        oci_config = oci.config.from_file(profile_name=oci_profile)
        region = oci_config.get("region", "us-chicago-1")
        console.print(f"\n[green]✓ Loaded OCI config (profile: {oci_profile}, region: {region})[/green]")

        # Try to find oci_generative_ai compartment
        try:
            identity_client = oci.identity.IdentityClient(oci_config)
            compartments = identity_client.list_compartments(
                oci_config.get("tenancy"),
                compartment_id_in_subtree=True
            )
            for c in compartments.data:
                if c.name == "oci_generative_ai" and c.lifecycle_state == "ACTIVE":
                    compartment_id = c.id
                    console.print(f"[green]✓ Found oci_generative_ai compartment[/green]")
                    break
        except Exception as e:
            console.print(f"[yellow]Could not search for compartments: {e}[/yellow]")

        # Fall back to config compartment_id or tenancy
        if not compartment_id:
            compartment_id = oci_config.get("compartment_id") or oci_config.get("tenancy")

    except ImportError:
        console.print("\n[yellow]⚠️  OCI SDK not installed. Run 'pip install oci'[/yellow]")
    except Exception as e:
        console.print(f"\n[yellow]⚠️  Could not load ~/.oci/config: {e}[/yellow]")

    # Fall back to environment variable
    if not compartment_id:
        compartment_id = os.environ.get("OCI_COMPARTMENT_ID", "")

    if not compartment_id:
        console.print("[yellow]⚠️  No compartment found[/yellow]")

        if Confirm.ask("Run in dry-run mode (simulated OCI results)?", default=True):
            dry_run = True
        else:
            console.print("[yellow]Skipping OCI comparison.[/yellow]")
            input("\nPress Enter to return...")
            return

    # Set endpoint based on region
    region = oci_config.get("region", "us-chicago-1") if oci_config else "us-chicago-1"
    endpoint = os.environ.get(
        "OCI_GENAI_ENDPOINT",
        f"https://inference.generativeai.{region}.oci.oraclecloud.com"
    )

    # Default Ollama models for three-way comparison
    ollama_models = ["gemma3:latest", "gemma3:270m"]

    console.print(f"\n[dim]Ollama Models: {', '.join(ollama_models)}[/dim]")
    console.print(f"[dim]OCI Model: {oci_model}[/dim]")
    console.print(f"[dim]Dry Run: {dry_run}[/dim]")
    console.print(f"[dim]Prompts: {len(INFERENCE_BENCHMARK_PROMPTS)} x {iterations} iterations[/dim]\n")

    runner = BenchmarkRunner(model=MODEL_NAME)

    # Create live display tables - one list per model
    ollama_results = {model: [] for model in ollama_models}
    oci_results = []
    comparisons = []

    def render_live_display():
        """Render the live comparison display."""
        from rich.layout import Layout
        from rich.panel import Panel
        from rich.columns import Columns

        # Create a table for each Ollama model
        model_tables = []
        for model in ollama_models:
            short_name = model.split(":")[0] if ":" in model else model
            size_hint = "(7B)" if model == "gemma3:latest" else "(270M)" if "270m" in model.lower() else ""

            table = Table(title=f"🦙 {short_name} {size_hint}", show_lines=False, expand=True)
            table.add_column("Prompt", style="cyan", width=18)
            table.add_column("Lat", style="yellow", justify="right")
            table.add_column("TTFT", style="green", justify="right")
            table.add_column("Tok", style="blue", justify="right")
            table.add_column("TPS", style="magenta", justify="right")

            for r in ollama_results[model][-4:]:  # Show last 4
                table.add_row(
                    f"{r.prompt[:15]}...",
                    f"{r.latency_ms:.0f}" if r.success else "ERR",
                    f"{r.ttft_ms:.0f}" if r.success else "-",
                    f"{r.token_count}" if r.success else "-",
                    f"{r.tps:.1f}" if r.success else "-",
                )
            model_tables.append(table)

        # OCI Results Table
        oci_table = Table(title="☁️ OCI GenAI", show_lines=False, expand=True)
        oci_table.add_column("Prompt", style="cyan", width=18)
        oci_table.add_column("Lat", style="yellow", justify="right")
        oci_table.add_column("TTFT", style="green", justify="right")
        oci_table.add_column("Tok", style="blue", justify="right")
        oci_table.add_column("TPS", style="magenta", justify="right")

        for r in oci_results[-4:]:  # Show last 4
            oci_table.add_row(
                f"{r.prompt[:15]}...",
                f"{r.latency_ms:.0f}" if r.success else "ERR",
                f"{r.ttft_ms:.0f}" if r.success else "-",
                f"{r.token_count}" if r.success else "-",
                f"{r.tps:.1f}" if r.success else "-",
            )

        # Comparison Table (three-way)
        comparison_table = Table(title="⚔️ Three-Way Comparison", show_lines=True, expand=True)
        comparison_table.add_column("Prompt", style="cyan", width=18)
        for model in ollama_models:
            short = "(7B)" if model == "gemma3:latest" else "(270M)" if "270m" in model.lower() else model
            comparison_table.add_column(short, style="yellow", justify="right")
        comparison_table.add_column("OCI", style="blue", justify="right")
        comparison_table.add_column("Winner", justify="center")

        for item in comparisons[-4:]:
            row = [f"{item['prompt'][:15]}..."]
            all_models = item.get("all_models", {})

            # Add latency for each Ollama model
            for model in ollama_models:
                if model in all_models:
                    row.append(f"{all_models[model]['latency']:.0f}ms")
                else:
                    row.append("-")

            # Add OCI latency
            if "oci" in all_models:
                row.append(f"{all_models['oci']['latency']:.0f}ms")
            else:
                row.append("-")

            # Winner emoji
            winner = item.get("winner", "")
            if winner == "oci":
                row.append("☁️")
            elif "270m" in winner.lower():
                row.append("🦙S")
            elif winner.startswith("gemma"):
                row.append("🦙L")
            else:
                row.append("🦙")

            comparison_table.add_row(*row)

        # Progress info
        total_expected = len(INFERENCE_BENCHMARK_PROMPTS) * iterations * (len(ollama_models) + 1)
        completed = sum(len(ollama_results[m]) for m in ollama_models) + len(oci_results)
        progress_text = f"Progress: {completed}/{total_expected} runs"

        # Combine into layout - three columns on top
        top_row = Columns(model_tables + [oci_table], equal=True, expand=True)

        layout = Table.grid(expand=True)
        layout.add_row(Panel(top_row, title="Live Results"))
        layout.add_row(Panel(comparison_table, title="Head-to-Head Comparison"))
        layout.add_row(f"[dim]{progress_text}[/dim]")

        return layout

    # Run the comparison benchmark
    with Live(render_live_display(), console=console, refresh_per_second=4, vertical_overflow="crop") as live:
        for item in runner.run_comparison_benchmark(
            prompts=INFERENCE_BENCHMARK_PROMPTS,
            iterations=iterations,
            ollama_models=ollama_models,
            oci_model_id=oci_model,
            compartment_id=compartment_id if not dry_run else None,
            endpoint=endpoint,
            profile_name=oci_profile,
            dry_run=dry_run,
        ):
            if item["type"] == "ollama":
                model_name = item.get("model", ollama_models[0])
                if model_name in ollama_results:
                    ollama_results[model_name].append(item["result"])
            elif item["type"] == "oci":
                oci_results.append(item["result"])
            elif item["type"] == "comparison":
                # Store the full item (includes all_models and winner)
                comparisons.append(item)

            live.update(render_live_display())

    # Final Summary
    console.print("\n" + "=" * 70)
    console.print("[bold green]BENCHMARK COMPLETE[/bold green]\n")

    # Calculate summary stats per model
    model_stats = {}

    for model in ollama_models:
        success = [r for r in ollama_results[model] if r.success]
        total = ollama_results[model]
        if success:
            model_stats[model] = {
                "avg_latency": sum(r.latency_ms for r in success) / len(success),
                "avg_ttft": sum(r.ttft_ms for r in success) / len(success),
                "avg_tps": sum(r.tps for r in success) / len(success),
                "avg_tokens": sum(r.token_count for r in success) / len(success),
                "total_tokens": sum(r.token_count for r in success),
                "avg_cost": sum(r.cost_estimate for r in success) / len(success),
                "success_count": len(success),
                "total_count": len(total),
            }
        else:
            model_stats[model] = {
                "avg_latency": 0, "avg_ttft": 0, "avg_tps": 0,
                "avg_tokens": 0, "total_tokens": 0, "avg_cost": 0,
                "success_count": 0, "total_count": len(total)
            }

    oci_success = [r for r in oci_results if r.success]
    if oci_success:
        model_stats["oci"] = {
            "avg_latency": sum(r.latency_ms for r in oci_success) / len(oci_success),
            "avg_ttft": sum(r.ttft_ms for r in oci_success) / len(oci_success),
            "avg_tps": sum(r.tps for r in oci_success) / len(oci_success),
            "avg_tokens": sum(r.token_count for r in oci_success) / len(oci_success),
            "total_tokens": sum(r.token_count for r in oci_success),
            "avg_cost": sum(r.cost_estimate for r in oci_success) / len(oci_success),
            "success_count": len(oci_success),
            "total_count": len(oci_results),
        }
    else:
        model_stats["oci"] = {
            "avg_latency": 0, "avg_ttft": 0, "avg_tps": 0, "avg_tokens": 0,
            "total_tokens": 0, "avg_cost": 0, "success_count": 0, "total_count": len(oci_results)
        }

    # Build summary table with all models
    summary_table = Table(title="Summary Statistics", show_lines=True)
    summary_table.add_column("Metric", style="cyan")

    # Add column headers for each model
    for model in ollama_models:
        short = "(7B)" if model == "gemma3:latest" else "(270M)" if "270m" in model.lower() else model
        summary_table.add_column(f"🦙 {short}", style="yellow", justify="right")
    summary_table.add_column("☁️ OCI", style="blue", justify="right")

    # Add rows
    def get_val(model, key, fmt=":.0f"):
        val = model_stats.get(model, {}).get(key, 0)
        if fmt == ":.0f":
            return f"{val:.0f}"
        elif fmt == ":.1f":
            return f"{val:.1f}"
        elif fmt == ":.6f":
            return f"${val:.6f}"
        return str(val)

    # Avg Latency row
    row = ["Avg Latency (ms)"]
    for model in ollama_models:
        row.append(get_val(model, "avg_latency"))
    row.append(get_val("oci", "avg_latency"))
    summary_table.add_row(*row)

    # Avg TTFT row
    row = ["Avg TTFT (ms)"]
    for model in ollama_models:
        row.append(get_val(model, "avg_ttft"))
    row.append(get_val("oci", "avg_ttft"))
    summary_table.add_row(*row)

    # Avg TPS row
    row = ["Avg TPS"]
    for model in ollama_models:
        row.append(get_val(model, "avg_tps", ":.1f"))
    row.append(get_val("oci", "avg_tps", ":.1f"))
    summary_table.add_row(*row)

    # Avg Tokens row
    row = ["Avg Tokens"]
    for model in ollama_models:
        row.append(get_val(model, "avg_tokens"))
    row.append(get_val("oci", "avg_tokens"))
    summary_table.add_row(*row)

    # Total Tokens row
    row = ["Total Tokens"]
    for model in ollama_models:
        row.append(str(model_stats.get(model, {}).get("total_tokens", 0)))
    row.append(str(model_stats.get("oci", {}).get("total_tokens", 0)))
    summary_table.add_row(*row)

    # Cost row (Ollama cost based on A10 GPU hourly rental: $1.28/hr)
    row = ["Avg Cost (A10)"]
    for model in ollama_models:
        row.append(get_val(model, "avg_cost", ":.6f"))
    row.append(get_val("oci", "avg_cost", ":.6f"))
    summary_table.add_row(*row)

    # Success Rate row
    row = ["Success Rate"]
    for model in ollama_models:
        s = model_stats.get(model, {})
        row.append(f"{s.get('success_count', 0)}/{s.get('total_count', 0)}")
    s = model_stats.get("oci", {})
    row.append(f"{s.get('success_count', 0)}/{s.get('total_count', 0)}")
    summary_table.add_row(*row)

    console.print(summary_table)
    console.print("[dim]* Ollama cost based on OCI A10 GPU rental: $1.28/hr ÷ processing seconds[/dim]")

    # Winner announcement (three-way)
    if comparisons:
        win_counts = {model: 0 for model in ollama_models}
        win_counts["oci"] = 0

        for c in comparisons:
            winner = c.get("winner", "")
            if winner in win_counts:
                win_counts[winner] += 1
            elif winner == "ollama":
                # Legacy fallback
                win_counts[ollama_models[0]] += 1

        console.print(f"\n[bold]Head-to-Head Results:[/bold]")
        for model in ollama_models:
            short = "(7B)" if model == "gemma3:latest" else "(270M)" if "270m" in model.lower() else model
            console.print(f"  🦙 {short} wins: {win_counts[model]}")
        console.print(f"  ☁️  OCI wins: {win_counts['oci']}")

        # Find overall winner
        all_contestants = list(ollama_models) + ["oci"]
        overall_winner = max(all_contestants, key=lambda m: win_counts.get(m, 0))
        max_wins = win_counts[overall_winner]

        # Check for ties
        tied = [m for m in all_contestants if win_counts.get(m, 0) == max_wins]

        if len(tied) > 1:
            console.print(f"\n[bold yellow]🏆 TIE between {len(tied)} models![/bold yellow]")
        elif overall_winner == "oci":
            console.print(f"\n[bold blue]🏆 WINNER: OCI GenAI ({oci_model})[/bold blue]")
        else:
            short = "(7B)" if overall_winner == "gemma3:latest" else "(270M)" if "270m" in overall_winner.lower() else overall_winner
            console.print(f"\n[bold green]🏆 WINNER: Ollama {short} ({overall_winner})[/bold green]")

    if dry_run:
        console.print("\n[dim]Note: OCI results were simulated (dry-run mode)[/dim]")

    input("\nPress Enter to return...")


def view_benchmark_report():
    """View the most recent benchmark report."""
    import glob

    print_header()
    console.print("[bold cyan]📈 VIEW BENCHMARK REPORTS[/bold cyan]\n")

    # Find recent reports
    md_files = glob.glob("benchmarks/*.md")
    json_files = glob.glob("benchmarks/*.json")
    all_files = md_files + json_files

    if not all_files:
        console.print("[yellow]No benchmark reports found.[/yellow]")
        input("\nPress Enter to return...")
        return

    # Sort by modification time
    all_files.sort(key=os.path.getmtime, reverse=True)

    choices = [
        questionary.Choice(f"{os.path.basename(f)} ({time.ctime(os.path.getmtime(f))})", value=f)
        for f in all_files[:10]
    ]
    choices.append(questionary.Choice("← Cancel", value=None))

    selected = questionary.select(
        "Select report to view:",
        choices=choices
    ).ask()

    if not selected:
        return

    with open(selected, "r") as f:
        content = f.read()

    console.print(Panel(content[:3000] + ("..." if len(content) > 3000 else ""),
                       title=f"[bold]{os.path.basename(selected)}[/bold]"))

    input("\nPress Enter to return...")


def export_benchmark_results():
    """Export benchmark results."""
    print_header()
    console.print("[bold cyan]💾 EXPORT RESULTS[/bold cyan]\n")
    console.print("[dim]Run a benchmark first, then results will be auto-saved.[/dim]")
    input("\nPress Enter to return...")


def main_menu():
    while True:
        clear_screen()
        print_header()

        choices = [
            questionary.Choice("Chat with Standard Agent", value="1"),
            questionary.Choice("Chain of Thought (CoT)", value="2"),
            questionary.Choice("Tree of Thoughts (ToT)", value="3"),
            questionary.Choice("ReAct (Tools + Web)", value="4"),
            questionary.Choice("Recursive (RLM)", value="5"),
            questionary.Choice("Self-Reflection", value="6"),
            questionary.Choice("Decomposed Prompting", value="7"),
            questionary.Choice("Least-to-Most", value="8"),
            questionary.Choice("Self-Consistency", value="9"),
            questionary.Separator(),
            questionary.Choice("🔄 Refinement Loop [Auto Demo]", value="r"),
            questionary.Choice("🔄 Complex Pipeline [5 Stages]", value="c"),
            questionary.Separator(),
            questionary.Choice("⚔️  ARENA: Run All Compare", value="a"),
            questionary.Choice("📊 BENCHMARKS: Performance Testing", value="b"),
            questionary.Separator(),
            questionary.Choice(f"⚙️  Select AI Model (Current: {MODEL_NAME})", value="m"),
            questionary.Separator(),
            questionary.Choice("Exit", value="0")
        ]

        choice = questionary.select(
            "Select an Activity:",
            choices=choices,
            use_arrow_keys=True
        ).ask()

        if not choice or choice == "0":
            sys.exit(0)
        elif choice == "m":
            select_model_panel()
        elif choice == "1":
            run_agent_chat("standard")
        elif choice == "2":
            run_agent_chat("cot")
        elif choice == "3":
            run_agent_chat("tot")
        elif choice == "4":
            run_agent_chat("react")
        elif choice == "5":
            run_agent_chat("recursive")
        elif choice == "6":
            run_agent_chat("reflection")
        elif choice == "7":
            run_agent_chat("decomposed")
        elif choice == "8":
            run_agent_chat("least_to_most")
        elif choice == "9":
            run_agent_chat("consistency")
        elif choice == "r":
            run_refinement_demo(interactive=False)  # Auto-run demo without user input
        elif choice == "c":
            run_complex_refinement_demo()  # Auto-run 5-stage pipeline demo
        elif choice == "a":
            run_arena_mode()
        elif choice == "b":
            run_benchmark_menu()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agent Reasoning CLI")
    parser.add_argument("--benchmark", action="store_true", help="Launch benchmark menu directly")
    parser.add_argument("--arena", action="store_true", help="Launch arena mode directly")
    parser.add_argument("--refinement-demo", action="store_true", help="Run refinement loop demo")
    parser.add_argument("--pipeline-demo", action="store_true", help="Run 5-stage pipeline demo")
    args = parser.parse_args()

    try:
        if args.benchmark:
            run_benchmark_menu()
        elif args.arena:
            run_arena_mode()
        elif args.refinement_demo:
            run_refinement_demo(interactive=False)
        elif args.pipeline_demo:
            run_complex_refinement_demo()
        else:
            main_menu()
    except KeyboardInterrupt:
        sys.exit(0)

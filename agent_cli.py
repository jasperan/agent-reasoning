#!/usr/bin/env python3
import os
import sys
import time
import subprocess
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint
from termcolor import colored

# Import Interceptor and Map
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src.interceptor import ReasoningInterceptor, AGENT_MAP

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
    title = """
    ╔════════════════════════════════════════════════════════════════╗
    ║                 AGENT REASONING CLI                            ║
    ║         Advanced Cognitive Architectures (Gemma 3)             ║
    ╚════════════════════════════════════════════════════════════════╝
    """
    console.print(Panel(title, style="bold purple", subtitle="Reasoning Layer"))
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
        
        full_response = ""
        
        # Use Live to update the output in place or just print stream
        # Since agents behave differently (ToT yields newlines, CoT yields tokens),
        # a simple print end="" is safest for raw text, 
        # but rich Live is nicer if we can accumulate Markdown.
        # Let's use a dynamic Text object or Markdown.
        
        with Live("", refresh_per_second=10, vertical_overflow="visible") as live:
            try:
                for chunk_dict in client.generate(model=full_model_name, prompt=query, stream=True):
                     chunk = chunk_dict.get("response", "")
                     full_response += chunk
                     # Update live display. 
                     # Using Markdown(full_response) might be heavy if very long, 
                     # but good for rendering formatting.
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
    strategies = ["standard", "cot", "tot", "react", "recursive", "reflection", "decomposed", "least_to_most", "consistency"]
    
    results = {}
    
    for strategy in strategies:
        console.print(f"\n[bold magenta]Running {strategy.upper()}...[/bold magenta]")
        full_model_name = f"{MODEL_NAME}+{strategy}"
        
        start_time = time.time()
        response_text = ""
        
        console.rule(f"[bold]{strategy}[/bold]")
        
        try:
             # Streaming with Live Display
             with Live("", refresh_per_second=10, vertical_overflow="visible") as live:
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

def main_menu():
    while True:
        clear_screen()
        print_header()
        console.print("[bold]Select an Activity:[/bold]")
        
        table = Table(show_header=False, box=None)
        table.add_column("Option", style="bold cyan")
        table.add_column("Description")
        
        table.add_row("[1]", "Chat with Standard Agent", style="cyan")
        table.add_row("[2]", "Chain of Thought (CoT)", style="magenta")
        table.add_row("[3]", "Tree of Thoughts (ToT)", style="magenta")
        table.add_row("[4]", "ReAct (Tools + Web)", style="blue")
        table.add_row("[5]", "Recursive (RLM) [NEW]", style="yellow")
        table.add_row("[6]", "Self-Reflection", style="blue")
        table.add_row("[7]", "Decomposed Prompting", style="green")
        table.add_row("[8]", "Least-to-Most", style="green")
        table.add_row("[9]", "Self-Consistency", style="green")
        table.add_row("[a]", "⚔️  ARENA: Run All Compare", style="red bold")
        table.add_row("[m]", "Select AI Model (Current: " + MODEL_NAME + ")", style="white")
        table.add_row("[t]", "Run Logic Benchmark", style="green")
        table.add_row("[0]", "Exit", style="dim")
        
        console.print(table)
        
        choice = Prompt.ask("\nEnter choice")
        
        if choice == "0":
            sys.exit(0)
        elif choice.lower() == "m":
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
        elif choice.lower() == "a":
            run_arena_mode()
        elif choice.lower() == "t":
             # Run existing main.py logic
             subprocess.run(["python", "main.py"], check=False)
             input("\nPress Enter to return...")
        else:
            console.print("[red]Invalid choice[/red]")
            time.sleep(1)

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        sys.exit(0)

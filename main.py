import json
import os
from pathlib import Path

import httpx
import typer

from config.config import get_active_provider, get_model_prices
from config.providers import ENV_KEYS, PRESETS

app = typer.Typer(help="CostAgent CLI — sends tasks to the CostAgent API server.")
API_BASE = "http://localhost:8000"


@app.command()
def run_task(
    prompt:      str          = typer.Option(None,  "--prompt",      "-p", help="Inline prompt text"),
    input_file:  Path | None  = typer.Option(None,  "--input-file",  "-f", help="Read prompt from file"),
    output_file: Path | None  = typer.Option(None,  "--output-file", "-o", help="Save result JSON to file"),
    tokens:      int          = typer.Option(100,   "--tokens",      "-t", help="Expected output tokens"),
    level:       int          = typer.Option(1,     "--level",       "-l", help="Task complexity (1-3)"),
    model:       str | None   = typer.Option(None,  "--model",       "-m", help="Override router model"),
    budget:      float | None = typer.Option(None,  "--budget",      "-b", help="Per-call budget override"),
    execute:     bool         = typer.Option(False, "--execute",      "-e", help="Actually call the LLM API (costs money)"),
):
    """Route and estimate a task. Use --execute to make a real API call."""
    if input_file:
        text = input_file.read_text(encoding="utf-8")
    elif prompt:
        text = prompt
    else:
        typer.echo("Error: provide --prompt or --input-file", err=True)
        raise typer.Exit(1)

    body: dict = {"input_text": text, "level": level, "tokens": tokens, "execute": execute}
    if model is not None:
        body["model"] = model
    if budget is not None:
        body["budget"] = budget

    try:
        r = httpx.post(f"{API_BASE}/api/run", json=body, timeout=30.0)
        r.raise_for_status()
    except httpx.ConnectError:
        typer.echo("Error: cannot connect to API server. Start it with: python3 api_server.py", err=True)
        raise typer.Exit(1)
    except httpx.HTTPStatusError as e:
        typer.echo(f"Error {e.response.status_code}: {e.response.text}", err=True)
        raise typer.Exit(1)

    result = r.json()
    typer.echo(result.get("summary", json.dumps(result, indent=2)))

    if output_file:
        output_file.write_text(json.dumps(result, indent=2), encoding="utf-8")
        typer.echo(f"Result saved to {output_file}")


@app.command()
def history(
    limit: int = typer.Option(10, "--limit", "-n", help="Number of recent runs to show"),
):
    """Show recent task runs from the log."""
    try:
        r = httpx.get(f"{API_BASE}/api/runs", params={"limit": limit}, timeout=10.0)
        r.raise_for_status()
    except httpx.ConnectError:
        typer.echo("Error: cannot connect to API server.", err=True)
        raise typer.Exit(1)
    except httpx.HTTPStatusError as e:
        typer.echo(f"Error {e.response.status_code}: {e.response.text}", err=True)
        raise typer.Exit(1)

    runs = r.json().get("runs", [])
    if not runs:
        typer.echo("No runs logged yet.")
        return
    for run in runs:
        actual = run.get("actual_cost")
        cost_str = f"actual=${actual:.5f}" if actual else f"est=${run['total_cost']:.5f}"
        typer.echo(
            f"[{run['timestamp']}] {run['model']} | "
            f"level={run['task_level']} | {cost_str}"
        )


@app.command()
def budget_check():
    """Show cumulative cost across all logged runs."""
    try:
        r = httpx.get(f"{API_BASE}/api/runs", params={"limit": 10000}, timeout=10.0)
        r.raise_for_status()
    except httpx.ConnectError:
        typer.echo("Error: cannot connect to API server.", err=True)
        raise typer.Exit(1)
    except httpx.HTTPStatusError as e:
        typer.echo(f"Error {e.response.status_code}: {e.response.text}", err=True)
        raise typer.Exit(1)

    runs = r.json().get("runs", [])
    estimated = sum(run["total_cost"] for run in runs)
    actual = sum(run["actual_cost"] for run in runs if run.get("actual_cost"))
    executed = sum(1 for run in runs if run.get("actual_cost"))
    typer.echo(f"Total runs:       {len(runs)} ({executed} executed)")
    typer.echo(f"Estimated total:  ${estimated:.5f}")
    typer.echo(f"Actual spent:     ${actual:.5f}")


@app.command()
def providers(
    list_all: bool = typer.Option(False, "--list", "-l", help="List all available provider presets"),
):
    """Show current provider or list all available presets."""
    if list_all:
        for name, models in PRESETS.items():
            env_var = ENV_KEYS[name]
            has_key = bool(os.getenv(env_var, "")) and not os.getenv(env_var, "").startswith("your_")
            status = "ready" if has_key else "no key"
            typer.echo(f"\n[{name}] ({env_var}) — {status}")
            for model_id, info in models.items():
                typer.echo(f"  L{info['level']}: {info['display_name']} ({model_id})")
        return

    active = get_active_provider()
    if not active:
        typer.echo("No provider configured. Set PROVIDER or add an API key to .env")
        typer.echo("Run: python3 main.py providers --list")
        raise typer.Exit(1)

    models = get_model_prices()
    if active == "auto":
        typer.echo("Provider: auto (cross-provider mixed routing)")
    else:
        typer.echo(f"Provider: {active} ({ENV_KEYS.get(active, 'N/A')})")
    for model_id, info in models.items():
        src = info.get("provider", active)
        typer.echo(f"  L{info['level']}: {info['display_name']} ({model_id}) — {src}")


if __name__ == "__main__":
    app()

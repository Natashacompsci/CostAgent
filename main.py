import json
from pathlib import Path

import httpx
import typer

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

    runs = r.json().get("runs", [])
    if not runs:
        typer.echo("No runs logged yet.")
        return
    for run in runs:
        typer.echo(
            f"[{run['timestamp']}] {run['model']} | "
            f"level={run['task_level']} | ${run['total_cost']:.5f}"
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

    runs = r.json().get("runs", [])
    total = sum(run["total_cost"] for run in runs)
    typer.echo(f"Total runs:      {len(runs)}")
    typer.echo(f"Cumulative cost: ${total:.5f}")


if __name__ == "__main__":
    app()

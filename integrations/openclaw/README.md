# CostAgent OpenClaw Skill

Integrate CostAgent as an [OpenClaw](https://github.com/openclaw/openclaw) skill to give your personal AI assistant cost-aware LLM routing.

## Installation

1. Start CostAgent server:

```bash
cd /path/to/CostAgent
python api_server.py
```

2. Copy the skill to OpenClaw's skills directory:

```bash
mkdir -p ~/.openclaw/skills/costagent
cp SKILL.md ~/.openclaw/skills/costagent/SKILL.md
```

3. Set the environment variable in your OpenClaw config (`~/.openclaw/openclaw.json` or shell):

```bash
export COSTAGENT_URL=http://localhost:8000
```

4. Restart OpenClaw. The agent will now have access to CostAgent's cost estimation and routing capabilities.

## Usage examples

In any OpenClaw channel (WhatsApp, Telegram, Slack, etc.):

- "How much would it cost to send this 2000-word prompt to GPT-4o?"
- "Which model should I use for a simple translation task?"
- "Run this prompt through the cheapest model: [your prompt]"

## Security note

This skill only uses `curl` to call your locally-running CostAgent server. No data is sent to third parties beyond the LLM provider you configure in CostAgent.

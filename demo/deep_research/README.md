# Deep Research Demo

A simplified version of [GPT Researcher](https://github.com/assafelovic/gpt-researcher)
(Apache 2.0) used as a demo project for **pixie-qa** evaluation.

## What Is Included

| Component | Description |
|-----------|-------------|
| `gpt_researcher/` | Core research agent, LLM orchestration, and report generation |
| `run.py` | Programmatic entry point – pass a query string, get a report back |

## What Was Removed

The following parts of the original GPT Researcher project were stripped out
to keep the demo focused on the core agent workflow:

* All UI (frontend, backend server, WebSocket streaming)
* Deep Research mode
* Image generation
* MCP (Model Context Protocol) integrations and retrievers
* All search retrievers **except DuckDuckGo**
* Tavily, Firecrawl, and other paid search/scrape providers
* PDF/DOCX export, Terraform, Docker, multi-agent orchestration

## Quick Start

```bash
# 1. Install dependencies (from the demo/deep_research directory)
pip install -e .

# 2. Set your OpenAI API key
export OPENAI_API_KEY="sk-..."

# 3. Run a research query
python run.py "What are the latest advances in quantum computing?"
```

### Programmatic Usage

```python
import asyncio
from run import research

report = asyncio.run(research("Benefits of remote work"))
print(report)
```

## Configuration

The researcher uses OpenAI models by default. You can override settings via
environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | *(required)* | OpenAI API key |
| `FAST_LLM` | `openai:gpt-4o-mini` | Fast LLM for sub-queries |
| `SMART_LLM` | `openai:gpt-4.1` | Smart LLM for report writing |
| `RETRIEVER` | `duckduckgo` | Search retriever (only `duckduckgo` available) |
| `MAX_SEARCH_RESULTS_PER_QUERY` | `5` | Results per search query |
| `MAX_ITERATIONS` | `3` | Number of search iterations |

## License

This project is a derivative work of GPT Researcher, licensed under the
[Apache License 2.0](LICENSE). See [NOTICE](NOTICE) for attribution details.

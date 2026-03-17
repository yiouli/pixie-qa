# Deep Research Demo Project

## What Changed

Added a simplified demo project under `demo/deep_research/` based on the
[GPT Researcher](https://github.com/assafelovic/gpt-researcher) project
(commit `7c32174`, Apache 2.0 license).

The demo serves as a real-world AI application that the **pixie-qa** skill
can be tested against.

### Simplifications from the original

| Removed | Reason |
|---------|--------|
| UI (frontend + backend server) | Not needed for programmatic evaluation |
| Deep Research mode | Complex multi-agent workflow, out of scope |
| Image generation | Not needed for text-based evaluation |
| MCP integrations | External tool integrations, not needed |
| All retrievers except DuckDuckGo | Simplifies dependencies, avoids paid APIs |
| Tavily / Firecrawl scrapers | Paid service dependencies |
| PDF / DOCX export | Not needed for evaluation |
| Docker / Terraform / multi-agent | Infrastructure, not needed |

### What remains

- Programmatic entry point (`run.py`) to run research with a string query
- Full agent workflow: query → sub-queries → web search → scrape → summarize → report
- DuckDuckGo as the sole search retriever (free, no API key needed for search)
- OpenAI as the LLM provider (requires `OPENAI_API_KEY`)

## Files Affected

- `demo/deep_research/` — entire new directory
- `demo/deep_research/gpt_researcher/` — simplified core library
- `demo/deep_research/run.py` — entry point
- `demo/deep_research/pyproject.toml` — dependencies
- `demo/deep_research/LICENSE` — Apache 2.0 (from upstream)
- `demo/deep_research/NOTICE` — attribution notice

## Migration Notes

This is a new addition — no migration required.

"""Simplified entry point for running a GPT Researcher query.

Usage:
    python run.py "What are the latest advances in quantum computing?"

Requires OPENAI_API_KEY to be set in the environment or in a .env file.
"""

import asyncio
import sys

from dotenv import load_dotenv

from gpt_researcher import GPTResearcher


async def research(query: str) -> str:
    """Run a research query and return the report as a string.

    Args:
        query: The research question to investigate.

    Returns:
        The generated research report in markdown format.
    """
    researcher = GPTResearcher(
        query=query,
        report_type="research_report",
        verbose=True,
    )
    await researcher.conduct_research()
    report = await researcher.write_report()
    return report


async def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python run.py <query>")
        sys.exit(1)

    query = sys.argv[1]
    print(f"\n🔍 Researching: {query}\n")
    report = await research(query)
    print("\n" + "=" * 80)
    print(report)
    print("=" * 80 + "\n")


if __name__ == "__main__":
    load_dotenv()
    asyncio.run(main())

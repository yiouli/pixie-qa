"""Retriever factory and utilities for GPT Researcher.

This module provides functions to instantiate and manage various
search retriever implementations.
"""


def get_retriever(retriever: str):
    """Get a retriever class by name.

    Args:
        retriever: The name of the retriever to get (e.g., 'duckduckgo').

    Returns:
        The retriever class if found, None otherwise.

    Supported retrievers:
        - duckduckgo: DuckDuckGo search
    """
    match retriever:
        case "duckduckgo":
            from gpt_researcher.retrievers import Duckduckgo

            return Duckduckgo

        case _:
            from gpt_researcher.retrievers import Duckduckgo

            return Duckduckgo


def get_retrievers(headers: dict[str, str], cfg):
    """
    Determine which retriever(s) to use based on headers, config, or default.

    Args:
        headers (dict): The headers dictionary
        cfg: The configuration object

    Returns:
        list: A list of retriever classes to be used for searching.
    """
    # Check headers first for multiple retrievers
    if headers.get("retrievers"):
        retrievers = headers.get("retrievers").split(",")
    # If not found, check headers for a single retriever
    elif headers.get("retriever"):
        retrievers = [headers.get("retriever")]
    # If not in headers, check config for multiple retrievers
    elif cfg.retrievers:
        # Handle both list and string formats for config retrievers
        if isinstance(cfg.retrievers, str):
            retrievers = cfg.retrievers.split(",")
        else:
            retrievers = cfg.retrievers
        # Strip whitespace from each retriever name
        retrievers = [r.strip() for r in retrievers]
    # If not found, check config for a single retriever
    elif cfg.retriever:
        retrievers = [cfg.retriever]
    # If still not set, use default retriever
    else:
        retrievers = [get_default_retriever().__name__]

    # Convert retriever names to actual retriever classes
    # Use get_default_retriever() as a fallback for any invalid retriever names
    retriever_classes = [get_retriever(r) or get_default_retriever() for r in retrievers]
    
    return retriever_classes


def get_default_retriever():
    """Get the default retriever class.

    Returns:
        The Duckduckgo retriever class as the default search provider.
    """
    from gpt_researcher.retrievers import Duckduckgo

    return Duckduckgo
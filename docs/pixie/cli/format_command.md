Module pixie.cli.format_command
===============================
``pixie format`` CLI command — convert trace logs into dataset entries.

Usage::

    pixie format --input trace.jsonl --output dataset_entry.json

Reads a JSONL trace file produced by ``pixie trace`` and converts it
into a valid dataset entry JSON object suitable for inclusion in a
dataset file.

Functions
---------

`def format_trace_to_entry(input_path: Path, output_path: Path) ‑> None`
:   Convert a trace log file into a dataset entry JSON file.
    
    The output is guaranteed to be a valid :class:`DatasetEntry` because
    it is constructed as a pydantic model and serialised with
    ``model_dump``.
    
    Args:
        input_path: Path to the JSONL trace file.
        output_path: Path to write the dataset entry JSON.
    
    Raises:
        FileNotFoundError: If the input file does not exist.
        ValueError: If the trace log has no usable data.

`def main(argv: list[str] | None = None) ‑> int`
:   Entry point for ``pixie format`` command.
    
    Args:
        argv: Command-line arguments. Defaults to ``sys.argv[1:]``.
    
    Returns:
        Exit code: 0 on success, 1 on error.
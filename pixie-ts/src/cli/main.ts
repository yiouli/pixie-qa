#!/usr/bin/env node
/**
 * pixie-qa CLI entry point — top-level command with subcommand routing.
 *
 * Usage:
 *   npx pixie-qa test [path] [-v] [--no-open]
 *   npx pixie-qa init [root]
 *   npx pixie-qa start [root]
 *   npx pixie-qa stop [root]
 *   npx pixie-qa trace --runnable <ref> --input <file> --output <file>
 *   npx pixie-qa format --input <file> --output <file>
 */

import { Command } from "commander";
import { config as loadDotenv } from "dotenv";

const program = new Command();

program
  .name("pixie-qa")
  .description("Pixie — automated quality assurance for AI applications")
  .version("0.8.0");

// -- pixie-qa test -----------------------------------------------------------
program
  .command("test")
  .description("Run pixie eval tests")
  .argument("[test-path]", "Dataset file or directory")
  .option("-v, --verbose", "Show detailed evaluation results", false)
  .option("--no-open", "Do not open the scorecard HTML in a browser")
  .action(
    async (
      testPath: string | undefined,
      opts: { verbose: boolean; open: boolean },
    ) => {
      loadDotenv();
      const { runTest } = await import("./testCommand.js");
      const exitCode = await runTest({
        testPath: testPath ?? null,
        verbose: opts.verbose,
        noOpen: !opts.open,
      });
      process.exit(exitCode);
    },
  );

// -- pixie-qa init -----------------------------------------------------------
program
  .command("init")
  .description("Scaffold the pixie_qa working directory")
  .argument("[root]", "Root directory to create")
  .action(async (root: string | undefined) => {
    loadDotenv();
    const { initPixieDir } = await import("./initCommand.js");
    const resultPath = initPixieDir(root ?? null);
    console.log(`Initialized pixie directory at ${resultPath}`);
  });

// -- pixie-qa start ----------------------------------------------------------
program
  .command("start")
  .description("Launch the web UI for browsing eval artifacts")
  .argument("[root]", "Artifact root directory")
  .action(async (root: string | undefined) => {
    loadDotenv();
    const { start } = await import("./startCommand.js");
    start(root ?? null);
  });

// -- pixie-qa stop -----------------------------------------------------------
program
  .command("stop")
  .description("Stop the running web UI server")
  .argument("[root]", "Artifact root directory")
  .action(async (root: string | undefined) => {
    loadDotenv();
    const { stop } = await import("./stopCommand.js");
    const exitCode = stop(root ?? null);
    process.exit(exitCode);
  });

// -- pixie-qa trace ----------------------------------------------------------
program
  .command("trace")
  .description("Run a Runnable and capture trace output to a JSONL file")
  .requiredOption(
    "--runnable <ref>",
    "Runnable reference in filepath:name format",
  )
  .requiredOption("--input <file>", "Path to JSON file containing kwargs")
  .requiredOption("--output <file>", "Path for the JSONL trace output file")
  .action(async (opts: { runnable: string; input: string; output: string }) => {
    loadDotenv();
    const { runTrace } = await import("./traceCommand.js");
    const exitCode = await runTrace({
      runnable: opts.runnable,
      inputPath: opts.input,
      outputPath: opts.output,
    });
    process.exit(exitCode);
  });

// -- pixie-qa format ---------------------------------------------------------
program
  .command("format")
  .description("Convert a trace log into a dataset entry JSON object")
  .requiredOption("--input <file>", "Path to the JSONL trace file")
  .requiredOption(
    "--output <file>",
    "Path for the output dataset entry JSON file",
  )
  .action(async (opts: { input: string; output: string }) => {
    loadDotenv();
    const { formatTraceToEntry } = await import("./formatCommand.js");
    formatTraceToEntry(opts.input, opts.output);
  });

program.parse();

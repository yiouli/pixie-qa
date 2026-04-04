#!/usr/bin/env node
/**
 * `pixie-qa` CLI entry point — top-level command with subcommand routing.
 *
 * Usage:
 *   pixie-qa dataset create|list|save|validate
 *   pixie-qa trace list|show|last|verify
 *   pixie-qa test [path] [-v] [--no-open]
 *   pixie-qa analyze <test_run_id>
 *   pixie-qa init [root]
 *   pixie-qa start [root]
 *   pixie-qa evaluators list
 *   pixie-qa dag validate|check-trace
 */

import { Command } from "commander";
import dotenv from "dotenv";

dotenv.config();

const program = new Command();
program
  .name("pixie-qa")
  .description("Pixie — automated quality assurance for AI applications")
  .version("0.3.0");

// ── pixie-qa dataset ────────────────────────────────────────────────────────

const datasetCmd = program
  .command("dataset")
  .description("Dataset management commands");

datasetCmd
  .command("create <name>")
  .description("Create a new empty dataset")
  .action((name: string) => {
    const { datasetCreate } = require("./datasetCommand");
    try {
      const dataset = datasetCreate(name);
      console.log(`Created dataset '${dataset.name}'.`);
    } catch (exc) {
      console.error(`Error: ${(exc as Error).message}`);
      process.exit(1);
    }
  });

datasetCmd
  .command("list")
  .description("List all datasets")
  .action(() => {
    const { datasetList, formatDatasetTable } = require("./datasetCommand");
    const rows = datasetList();
    console.log(formatDatasetTable(rows));
  });

datasetCmd
  .command("save <name>")
  .description("Save a span from the latest trace to a dataset")
  .option(
    "--select <mode>",
    "How to select the span (root, last_llm_call, by_name)",
    "root"
  )
  .option("--span-name <name>", "Span name to match (for --select=by_name)")
  .option("--expected-output", "Read expected output JSON from stdin", false)
  .option("--notes <text>", "Optional notes to attach")
  .action(
    (
      name: string,
      options: {
        select: string;
        spanName?: string;
        expectedOutput: boolean;
        notes?: string;
      }
    ) => {
      const { datasetSave } = require("./datasetCommand");
      const { UNSET } = require("../storage/evaluable");

      let expectedOutput = UNSET;
      if (options.expectedOutput) {
        const fs = require("fs");
        const fd = fs.openSync(0, "r"); // fd 0 = stdin
        const raw = fs.readFileSync(fd, "utf-8").trim();
        if (!raw) {
          console.error(
            "--expected-output flag set but no JSON provided on stdin."
          );
          process.exit(1);
        }
        expectedOutput = JSON.parse(raw);
      }

      try {
        const dataset = datasetSave({
          name,
          select: options.select,
          spanName: options.spanName,
          expectedOutput,
          notes: options.notes,
        });
        console.log(
          `Saved to dataset '${dataset.name}' — now ${dataset.items.length} item(s).`
        );
      } catch (exc) {
        console.error(`Error: ${(exc as Error).message}`);
        process.exit(1);
      }
    }
  );

datasetCmd
  .command("validate [path]")
  .description("Validate dataset JSON files")
  .action((searchPath?: string) => {
    const { getConfig } = require("../config");
    const {
      discoverDatasetFiles,
      validateDatasetFile,
    } = require("../evals/datasetRunner");

    const target = searchPath ?? getConfig().datasetDir;
    const datasetFiles = discoverDatasetFiles(target) as string[];
    if (datasetFiles.length === 0) {
      console.log("No dataset files found.");
      process.exit(1);
    }

    let totalErrors = 0;
    let filesWithErrors = 0;
    for (const datasetFile of datasetFiles) {
      const errors = validateDatasetFile(datasetFile) as string[];
      if (errors.length > 0) {
        filesWithErrors++;
        totalErrors += errors.length;
        console.log(`\n${datasetFile}:`);
        for (const error of errors) {
          console.log(`  - ${error}`);
        }
      } else {
        console.log(`${datasetFile}: OK`);
      }
    }

    if (totalErrors > 0) {
      console.log(
        `\nValidation failed: ${totalErrors} error(s) in ${filesWithErrors} dataset file(s).`
      );
      process.exit(1);
    }

    console.log("\nAll datasets are valid.");
  });

// ── pixie-qa trace ──────────────────────────────────────────────────────────

const traceCmd = program
  .command("trace")
  .description("Inspect captured traces");

traceCmd
  .command("list")
  .description("List recent traces")
  .option("--limit <n>", "Maximum number of traces", "10")
  .option("--errors", "Show only traces with errors", false)
  .action((options: { limit: string; errors: boolean }) => {
    const { traceList } = require("./traceCommand");
    const exitCode = traceList(parseInt(options.limit, 10), options.errors);
    if (exitCode !== 0) process.exit(exitCode);
  });

traceCmd
  .command("show <trace_id>")
  .description("Show span tree for a trace")
  .option("-v, --verbose", "Show full input/output data", false)
  .option("--json", "Output as JSON", false)
  .action(
    (traceId: string, options: { verbose: boolean; json: boolean }) => {
      const { traceShow } = require("./traceCommand");
      const exitCode = traceShow(traceId, options.verbose, options.json);
      if (exitCode !== 0) process.exit(exitCode);
    }
  );

traceCmd
  .command("last")
  .description("Show the most recent trace (verbose)")
  .option("--json", "Output as JSON", false)
  .action((options: { json: boolean }) => {
    const { traceLast } = require("./traceCommand");
    const exitCode = traceLast(options.json);
    if (exitCode !== 0) process.exit(exitCode);
  });

traceCmd
  .command("verify")
  .description("Verify the most recent trace for common issues")
  .action(() => {
    const { traceVerify } = require("./traceCommand");
    const exitCode = traceVerify();
    if (exitCode !== 0) process.exit(exitCode);
  });

// ── pixie-qa test ───────────────────────────────────────────────────────────

program
  .command("test [path]")
  .description("Run pixie eval tests")
  .option("-v, --verbose", "Show detailed evaluation results", false)
  .option("--no-open", "Do not open the scorecard HTML")
  .action(
    async (
      testPath: string | undefined,
      options: { verbose: boolean; open: boolean }
    ) => {
      const { testMain } = require("./testCommand");
      const exitCode = await testMain({
        path: testPath,
        verbose: options.verbose,
        noOpen: !options.open,
      });
      process.exit(exitCode);
    }
  );

// ── pixie-qa analyze ────────────────────────────────────────────────────────

program
  .command("analyze <test_run_id>")
  .description("Generate analysis and recommendations for a test run")
  .action(async (testRunId: string) => {
    const { analyze } = require("./analyzeCommand");
    const exitCode = await analyze(testRunId);
    process.exit(exitCode);
  });

// ── pixie-qa init ───────────────────────────────────────────────────────────

program
  .command("init [root]")
  .description("Scaffold the pixie_qa working directory")
  .action((root?: string) => {
    const { initPixieDir } = require("./initCommand");
    const resultPath = initPixieDir(root);
    console.log(`Initialized pixie directory at ${resultPath}`);
  });

// ── pixie-qa start ──────────────────────────────────────────────────────────

program
  .command("start [root]")
  .description("Launch the web UI for browsing eval artifacts")
  .action(async (root?: string) => {
    const { start } = require("./startCommand");
    const exitCode = await start(root);
    process.exit(exitCode);
  });

// ── pixie-qa evaluators ─────────────────────────────────────────────────────

const evaluatorsCmd = program
  .command("evaluators")
  .description("Evaluator management commands");

evaluatorsCmd
  .command("list")
  .description("List all available built-in evaluator names")
  .action(() => {
    const { listAvailableEvaluators } = require("../evals/datasetRunner");
    for (const name of listAvailableEvaluators()) {
      console.log(name);
    }
  });

// ── pixie-qa dag ────────────────────────────────────────────────────────────

const dagCmd = program
  .command("dag")
  .description("Data-flow DAG validation and trace checking");

dagCmd
  .command("validate <json_file>")
  .description("Validate a DAG JSON file and generate Mermaid diagram")
  .option("--project-root <path>", "Project root for resolving code pointers")
  .action((jsonFile: string, options: { projectRoot?: string }) => {
    const { dagValidate } = require("./dagCommand");
    const exitCode = dagValidate(jsonFile, options.projectRoot);
    if (exitCode !== 0) process.exit(exitCode);
  });

dagCmd
  .command("check-trace <json_file>")
  .description("Check the last trace against a DAG JSON file")
  .action(async (jsonFile: string) => {
    const { dagCheckTrace } = require("./dagCommand");
    const exitCode = await dagCheckTrace(jsonFile);
    process.exit(exitCode);
  });

// ── Run ─────────────────────────────────────────────────────────────────────

program.parse();

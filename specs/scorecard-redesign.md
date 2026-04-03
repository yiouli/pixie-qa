# Scorecard redesign

The goal is to redesign the content and display of the test scorecard so it's more actionable.

For a scorecard to be actionable, it needs to:

1. show user what are the scenarios (entries in dataset) + evaluation dimension (aka evaluator) that are failing, and how/why they are failing.
2. show user a high level summary of the test result and provide recommendations
3. hide details about test with click(s) away to not cluster/distract user from key information in 1&2.

With these objectives, here're the changes that needs to be made:

## Test overview

Still show at the top of the scorecard page, with:

- command (unchanged)
- time: change to show local-time, and both the start time, end time, and duration
- datasets result table: replaces the x/n tests passed and the current table. The new table should have two columns, dataset name (relative path to pixie root folder with .json extension removed), and the result column showing "x/n passed" for each dataset; n being the number of data entries in the dataset, while x is the number of entries with ALL evaluators passed

## per-dataset scorecard

This scorecard replace the current per-test/dataset scorecard.

For each scorecard, the header is the dataset name (same name as in test overview). There's no more pass/fail per dataset, instead it's x/n passed (same as in test overview).

Then an analysis & recommendation section should follow. The content of this would be loaded from agent-generated markdown content (more details below).

After that, it should be a table with 3 columns: scenario, result, evaluations & detail.

- one data entry in the dataset per row.
- the scenario column should display the _description_ value of the entry (this is a new column to be added to dataset json file)
- the result column should show the pass/fail pill for the row, Pass only when all evaluators for the row pass.
- the evaluations column should be a list of pills, with the text being the evaluator name (aka the item value in the dataset's evaluators column), while green/red representing pass/fail for each evaluator. The pills should be sorted asc by the score.
- details column should just be the "details" hyperlink to open the details modal.

## Description column in dataset

A new `description` column should be added to the dataset. It should be a one concise sentence to describe the scenario-being-evaluated for the row, and it should convey both what the input is and what the expectations are. e.g. "Reroute to human agent on account lookup difficulties".

## Test report generation change

Currently the `pixie test ...` command directly generate a html document, but that makes it difficult to use the test result for other processing. And because we need to further analyse the test result, we need to change `pixie test ...` to produce a JSON file, and move the html rendering logic into frontend.

The result json should look like this:

```json
[
    {
        "dataset": "${datasetName}",
        "entries": [
            {
                "input": ...,
                "output": ...,
                "expectedOutput": ..., // optional
                "evaluations": [
                    {
                        "evaluator": "${evaluatorName}",
                        "score": ...
                        "reasoning": ...,
                    },
                    ...
                ]
            },
            ...
        ]
    },
    ...
]
```

And the json file should be placed at `<pixie_root>/results/<test_id>/result.json`. No more scorecards folder or generated scorecard html files.

## Test result analysis and recommendations

A new command `pixie analyze <test_run_id>` need to be added to generate analysis and recommendations for a test run result.

The command should load the test run result json, and launch an agent to generate the analysis & recommendations for each dataset result. For now let's use a DSPy chain-of-thought agent for the implementation.

The analysis agents should run concurrently similar to how evaluators are ran. Re-use the same concurrency management code and same configuration.

The analysis result content should be write to `<pixie_root>/results/<test_id>/dataset-<dataset-index-in-result>.md`.

## Scorecard rendering change

Instead of loading the scorecard html in iframe, now the frontend should now incorperate the separate build of scorecard in the main frontend build, and change the component to load the result from server. The server should combine the result json with available dataset analysis content (read dataset-\*.md files, and add "analysis" property to dataset objects in json), and return the combined data to frontend.

SSE should also send notification from server to client on any content change in the results folder, and make the client to switch tab/item selection to the latest updated test-id.

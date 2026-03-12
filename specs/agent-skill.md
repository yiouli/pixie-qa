A skill for developing llm-powered python software with eval-driven-development.

instrument application, build golden datasets, build evals-based tests, run those tests and root-cause test failures during development cycle,

use whenever user is developing a python-based and llm-powered software project, or whenever user want to evaluate, verify, test, qa, or benchmark such project.

At a high level, the process of practicing eval-driven-development goes like this:

- develop a mental understanding of how the in-development software runs, what it's aiming to do, and what the expected behaviors are.
- decide how to evaluate the quality of the llm-powered software, what are the aspects to evaluate on, what's the granularity of evaluation, and what's the criteria to consider the quality as good/bad.
- decide what data need to be captured for proper evaluation
- decide scenarios that the software need to be evaluated and tested against
- build the datasets containing the test scenarios with proper data for evaluation
- run eval-based tests on the corresponding datasets whenever changes related to llm usage is made during development, and/or test cases/data for evaluation/evaluation criteria changes
- investigate and root cause evaluation-test failures, and apply the learning to change implementation/test cases/data/evaluation criteria
- repeat until satisfied

# detailed tactics

## develop mental understanding

- mainly based on exploring the codebase
- end goal is to figure out
  - how the software can be run for evaluation/test
  - what are the "inputs" to run the llm-powered software, this is not limited to user input; anything that the software get from external sources and eventually fed into LLM should be considered input
  - what are the use cases/user stories, what are the expected outcome & behavior
- document your understanding and keep it up-to-date
- clarify with user for things you are unsure about

## decide on data for evaluation

- depending on evaluation criteria, some internal & intermiediate data from the software might be needed to evaluate it
- read the code and understand all the "inputs", intermiediate "outputs" and final outputs.
- document your understanding, with code pointers in code for the data that's needed for evaluations, and keep it up-to-date
- clarify with user for things you are unsure about

## build datasets

- use `pixie dataset create/list/save` commands to manage datasets
- all datasets, tests, scripts, and the observation DB live in `.pixie/` directory
- there are two ways to add to dataset, either saving traces from actually running the software, or generating synthetic data
- for saving to dataset from actual runs, first properly instrument the software by calling `enable_storage()` inside the app's startup function (not at module level), then add `@observe` or `start_observation` to the proper places in the code to capture data for evaluation; then after a run, use `pixie dataset save ...` command to save captured data to dataset
- for generating synthetic data, you'd need to at least save one item from an actual run, then you can understand the data format of the actual inputs. Then you should generate the "inputs" portion of the data for various evaluation/test scenarios, write scripts (in `.pixie/scripts/`) to run the software with proper input piping and potential mocking, capture the traces, and save them to dataset using `pixie` provided APIs to read traces/convert to evaluable/save to dataset

### the expected output

depending on the evaluation criteria, expected outputs might be needed. If so, they need to be generated, based on the actual outputs from the run, your judgement, and optionally user feedback. You should generate them first then ask user to review optionally if you're unsure.

## define & run eval-based tests

- define "tests" based on the evaluation criteria, and how "inputs" should be piped/mocked when running the software, using `pixie.assert_dataset_pass`
- depending on the complexity of the criteria, multiple tests with different evaluators, datasets and/or pass criteria might be needed
- test files live in `.pixie/tests/` (e.g. `.pixie/tests/test_customer_service.py`)
- run them with `pixie test .pixie/tests/` or `pixie test .pixie/tests/test_customer_service.py`
- the test runner automatically adds the test file's parent and grandparent directories to `sys.path`, so project-root imports work out of the box (like pytest)
- use `-v` for verbose output and `-k <pattern>` to filter tests by name

## investigate and learn

- for each failed test case, look up the full trace (the trace_id is saved in the evaluation result metadata)
- examine the captured spans — inputs, outputs, LLM invocations, latencies — and analyse where the software went wrong
- document findings with actual trace data, evaluator scores/reasoning, and root cause analysis in `.pixie/MEMORY.md`
- do additional debug runs with the same inputs for further debugging if needed
- make changes and re-run the same evaluations to compare; iterate until satisfied

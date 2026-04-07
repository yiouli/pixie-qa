# Runnable interface

The current dataset runner takes a runnable property and would directly run the function with the kwargs from dataset entry.

However, the contract between the test harness, the custom runnable function and the dataset are unclear, leading to unexpected usages. Additionally, for certain applications (e.g. fastapi server + request), setup & teardown are needed, and it's unclear whether those should be implemented as part of the runnable function.

The task now is to create a Protocol for runnable, and have the dataset, dataset runner and custom runnable all work around that protocol.

## The Runnable Protocol

```python

T = TypeVar("T", bound=BaseModel, contravariant=True)

class Runnable(Protocol[T]):

    @classmethod
    def create(cls) -> None:
        ...

    async def setup(self) -> None:
        """Optional"""
        pass

    async def teardown(self) -> None:
        """Optional"""
        pass

    async def run(cls, args: T) -> None:
        """Only accept kwargs"""
        ...
```

With this, the runnable property in dataset should be pointed to the runnable class instead; the dataset runner would properly create the runnable instance, properly setup and teardown for the dataset run, and call run(...) with the kwargs-turned-pydantic-object for each dataset entry.

```python
# demonstration for a dataset

runnable_cls = _resolve_runnable(dataset.runnable)
runnable_args_type = _get_runnable_args_type(runnable_cls)  # type of pydantic model
runnable = runnable_cls.create()

try:
    await runnable.setup()
    for entry in dataset.entries:
        ...
        args = runnable_args_type.model_validate(dataset.kwargs)
        await runnable.run(args)
        ...
finally:
    ...
    await runnable.teardown()

```

## `pixie trace ...` command

We also need to add a new trace command to run the application and save the kwargs, all `wrap` events and LLM call spans via trace writer, so later we can reference create dataset entries according to the trace log's format.

The `pixie trace` command should take an `runnable` argument for the runnable location (same str format as in dataset), `input` argument for the (pixie-root-relative) file path that contains the kwargs json, `output` argument for (pixie-root-relative) file path to store the trace logs. It's implementation should reuse the same code (extract into utility function) above to run the runnable.

The command should properly enable tracing/configure otel handler to capture the OTel emitted event/span.

Currently the `wrap` event and llm call span are already properly emitted, but we're still missing the logging for the kwargs. So that should be emitted by the new utility function that runs the runnable, at the `runnable.run(...)` call time, and it should be picked up and logged by the trace writer. The logged kwargs format should be like this:

```json
{
    "type": "kwargs",
    "value": ...
}
```

## `pixie format ...` command

Separately a `pixie format ...` command is needed to create a valid dataset entry json object from the trace log created by `pixie trace`. This further helps us create valid dataset entries.

The `format` command should take an argument for `input` - relative path for the log file, and `output`, relative file path to save the converted dataset entry json. Its implementation should be straight forward:

- load the log and parse each line into a WrappedData, LLM span, or kwargs
- create DatasetEntry with proper mapping:
  - entry_kwargs <= kwargs
  - test case
    - eval_input <= filtered list[WrappedData] with purpose = 'input', transformed to list[NamedData]
    - expectation <= filtered list[WrappedData] with purpose = 'output' or 'state', transformed to list[NamedData], and LLM call spans with metadata-like values removed. Keep the combined list in the same ordering as in the log
    - description <= "transformed from <inputfile_path>"
  - evaluators <= hardcoded ['Factuality']
- save the pydantic model dump json to target file

## Verification

After implementation, update the manual testing fixture (under tests/manual/) to verify that all parts work together:

- add a runnable class implementation for the app
- for the verification script the workflow should be:
  - trace an app run (pixie trace)
  - format the trace log into dataset entry (pixie format)
  - turn the dataset entry into a dataset with minimal wrapping, while update the evaluators list for the entry to include the mock evaluators
  - run test on the dataset (pixie test)

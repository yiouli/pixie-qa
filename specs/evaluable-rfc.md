# Evaluable refactoring

The Evaluable interface and usage is bloated and unncessarily complicated. Let's do a refactoring on that.

Conceptually there are actually two different type of objects:

1. the scenario + expectation + metadata without the actual output, name this TestCase
2. 1 + actual output => the real evaluable object (Evaluable, a subclass of TestCase)

So for things that's current using evaluable outside the evaluate(), evaluator part of code, it should actually use the TestCase class because there's no real output (from running app) involved.

Also The captured... fields should be removed, they are only used by dataset runner, and they are really the `eval_output`. The `evaluators` field should also be removed - that's not part of testcase/evaluable itself, rather it's configured separated by dataset.

The expected_output field name is confusing because it could be a desription of what's expected in the actual eval_output, it should be renamed to `expectation`

The format of eval_input and eval_output should be narrowed down, too. Right now they are effectively list[WrappedData], but the purpose in `WrappedData` has no meaning in the evaluation thus it's only confusing to force that. So instead a new NamedData type should be introduced that only has the name and jsonpickled value, and both eval_input and eval_ouput would be type of list[NamedData], non-nullable & non-empty.

## Updates to dataset data structure

Because evaluable would no longer carry "purpose", the dataset data structure would need change to carry that information to keep dataset_runner working. So the update should now have a structured type for each entry. The `LoadedDataset` dataclass should be replaced with pydantic model as well:

```python
class Dataset(BaseModel):
    name: str
    runnable: str
    entries: list[DatasetEntry]

class DatasetEntry(BaseModel):
  entry_kargs: dict[str, JsonValue]
  test_case: TestCase
  evaluators: list[str]
```

This way, the `entry_kargs` would be fed to runnable to start the run, while the eval_input in test case would be used for dependency input injection.

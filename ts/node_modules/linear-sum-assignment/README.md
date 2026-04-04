# linear sum assignment

<p align="center">
  Package to perform a linear sum assignment even if the cost matrix is rectangular.
</p>
<p align="center">
  <img alt="NMReDATA" src="images/linear_assignment.svg">
</p>

This package is the implementation of Jonker-Volgenant shortest
augmenting path algorithm based on the publication [On implementing 2D rectangular assignment algorithms](https://doi.org/10.1109/TAES.2016.140952)

If the number of rows is <= the number of columns, then every row is assigned to one column; otherwise every column is assigned to one row. The assignment minimizes the sum of the assigned elements.

## Instalation

`$ npm i linear-sum-assignment`

## Usage

```js
import linearSumAssignment from 'linear-sum-assignment';
import { xCostMatrix } from 'ml-spectra-processing';

/**
 * there is one more value in the experimental values, so one of
 * them will be not assigned.
 **/
const experimental = [1, 2, 3, 4, 5, 7];
const predicted = [3.1, 1.1, 1.9, 3.99, 5.2];

/**
 * We will compute a cost matrix where experimental are
 * rows and predicted in columns.
 * In this case we will look for the closest peak for each experimental peak value.
 **/

const diff = xCostMatrix(experimental, predicted, {
  fct: (a, b) => Math.abs(a - b),
});
const result = linearSumAssignment(diff, { maximaze: false });
console.log(result);
/**
{
  rowAssignments: Float64Array(6) [ 1, 2, 0, 3, 4, -1 ],
  columnAssignments: Float64Array(5) [ 2, 0, 1, 3, 4 ],
  gain: 0.5100000000000002,
  dualVariableForColumns: Float64Array(5) [
    0.0900000000000003,
    0.0900000000000003,
    0.0900000000000003,
    0,
    0.1900000000000004
  ],
  dualVariableForRows: Float64Array(6) [ 0, 0, 0, 0, 0, 0 ]
}
*/
```

`rowAssignments` contains the index of the column assigned to each element in the rows (experimental).

`columnAssignments` contains the index of the row assigned to each element in the columns. So the first element in predicted is assigned to third element in experimental.
`dualVariableForColumns` and `dualVariableForRows` are the Lagrange multipliers or dual variables.
`gain` the sum of the elements in the cost matrix.

## License

[MIT](./LICENSE)

[npm-image]: https://img.shields.io/npm/v/linearSumAssignment.svg
[npm-url]: https://www.npmjs.com/package/linearSumAssignment
[ci-image]: https://github.com/mljs/linear-sum-assignment/workflows/Node.js%20CI/badge.svg?branch=main
[ci-url]: https://github.com/mljs/linear-sum-assignment/actions?query=workflow%3A%22Node.js+CI%22
[codecov-image]: https://img.shields.io/codecov/c/github/mljs/linear-sum-assignment.svg
[codecov-url]: https://codecov.io/gh/mljs/linear-sum-assignment
[download-image]: https://img.shields.io/npm/dm/linearSumAssignment.svg
[download-url]: https://www.npmjs.com/package/linearSumAssignment

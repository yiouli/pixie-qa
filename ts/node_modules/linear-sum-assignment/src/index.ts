import type { DoubleArray } from 'cheminfo-types';
import { Matrix } from 'ml-matrix';

import { getShortestPath } from './getShortestPath.ts';

export interface LinearSumAssignmentOptions {
  /**
   * if true it will generate the assignment by the maximization of the cost.
   * @default true
   */
  maximaze?: boolean;
}

/**
 * Implementation of Jonker-Volgenant shortest augmenting path algorithm based
 * on the publication [On implementing 2D rectangular assignment algorithms](https://doi.org/10.1109/TAES.2016.140952)
 */

export function linearSumAssignment(
  /**
   * Cost matrix
   */
  input: DoubleArray[] | Matrix,
  options: LinearSumAssignmentOptions = {},
) {
  const { maximaze = true } = options;

  let matrix = Matrix.checkMatrix(input);
  let didFlip = false;
  if (matrix.columns > matrix.rows) {
    didFlip = true;
    matrix = matrix.transpose();
  }

  const nbRows = matrix.rows;
  const nbColumns = matrix.columns;

  const matrixDelta = maximaze ? matrix.max() : matrix.min();
  matrix = matrix.subtract(matrixDelta);
  if (maximaze) matrix = matrix.mul(-1);

  let rowAssignments: DoubleArray = new Float64Array(nbRows).fill(-1);
  let columnAssignments: DoubleArray = new Float64Array(nbColumns).fill(-1);
  let dualVariableForColumns: DoubleArray = new Float64Array(nbColumns);
  let dualVariableForRows: DoubleArray = new Float64Array(nbRows);

  for (let currUnAssCol = 0; currUnAssCol < nbColumns; currUnAssCol++) {
    const currentAugmenting = getShortestPath({
      matrix,
      currUnAssCol,
      dualVariableForColumns,
      dualVariableForRows,
      rowAssignments,
      columnAssignments,
    });
    const { sink, pred } = currentAugmenting;

    if (sink === -1) {
      return {
        rowAssignments,
        columnAssignments,
        gain: -1,
        dualVariableForColumns,
        dualVariableForRows,
      };
    }

    dualVariableForColumns = currentAugmenting.dualVariableForColumns;
    dualVariableForRows = currentAugmenting.dualVariableForRows;
    let j = sink;
    for (let i = pred[j]; true; i = pred[j]) {
      rowAssignments[j] = i;
      const h = columnAssignments[i];
      columnAssignments[i] = j;
      j = h;
      if (i === currUnAssCol) break;
    }
  }

  let gain = 0;
  for (let curCol = 0; curCol < nbColumns; curCol++) {
    gain += matrix.get(columnAssignments[curCol], curCol);
  }

  gain = (maximaze ? -1 : 1) * gain + matrixDelta * nbColumns;

  if (didFlip) {
    [columnAssignments, rowAssignments] = [rowAssignments, columnAssignments];
    [dualVariableForColumns, dualVariableForRows] = [
      dualVariableForRows,
      dualVariableForColumns,
    ];
  }

  return {
    rowAssignments,
    columnAssignments,
    gain,
    dualVariableForColumns,
    dualVariableForRows,
  };
}

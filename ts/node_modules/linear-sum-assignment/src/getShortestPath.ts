import type { DoubleArray } from 'cheminfo-types';
import type { Matrix } from 'ml-matrix';
import { xSequentialFillFromTo } from 'ml-spectra-processing';

export interface GetShortestPathOptions {
  currUnAssCol: number;
  dualVariableForColumns: DoubleArray;
  dualVariableForRows: DoubleArray;
  rowAssignments: DoubleArray;
  columnAssignments: DoubleArray;
  matrix: Matrix;
}

export function getShortestPath(options: GetShortestPathOptions) {
  const {
    currUnAssCol,
    dualVariableForColumns,
    dualVariableForRows,
    rowAssignments,
    columnAssignments,
    matrix,
  } = options;

  const nbRows = matrix.rows;
  const nbColumns = matrix.columns;

  const pred = new Float64Array(nbRows);
  const scannedColumns = new Float64Array(nbColumns);
  const scannedRows = new Float64Array(nbRows);

  const rows2Scan = Array.from(
    xSequentialFillFromTo({ from: 0, to: nbRows - 1, size: nbRows }),
  );
  let numRows2Scan = nbRows;

  let sink = -1;
  let delta = 0;
  let curColumn = currUnAssCol;
  const shortestPathCost = new Array(nbRows).fill(Number.POSITIVE_INFINITY);
  while (sink === -1) {
    scannedColumns[curColumn] = 1;
    let minVal = Number.POSITIVE_INFINITY;
    let closestRowScan = -1;
    for (let curRowScan = 0; curRowScan < numRows2Scan; curRowScan++) {
      const curRow = rows2Scan[curRowScan];

      const reducedCost =
        delta +
        matrix.get(curRow, curColumn) -
        dualVariableForColumns[curColumn] -
        dualVariableForRows[curRow];
      if (reducedCost < shortestPathCost[curRow]) {
        pred[curRow] = curColumn;
        shortestPathCost[curRow] = reducedCost;
      }

      if (shortestPathCost[curRow] < minVal) {
        minVal = shortestPathCost[curRow];
        closestRowScan = curRowScan;
      }
    }
    if (!Number.isFinite(minVal)) {
      return { dualVariableForColumns, dualVariableForRows, sink, pred };
    }
    const closestRow = rows2Scan[closestRowScan];
    scannedRows[closestRow] = 1;
    numRows2Scan -= 1;
    rows2Scan.splice(closestRowScan, 1);
    delta = shortestPathCost[closestRow];

    if (rowAssignments[closestRow] === -1) {
      sink = closestRow;
    } else {
      curColumn = rowAssignments[closestRow];
    }
  }
  dualVariableForColumns[currUnAssCol] += delta;

  for (let sel = 0; sel < nbColumns; sel++) {
    if (scannedColumns[sel] === 0) continue;
    if (sel === currUnAssCol) continue;
    dualVariableForColumns[sel] +=
      delta - shortestPathCost[columnAssignments[sel]];
  }
  for (let sel = 0; sel < nbRows; sel++) {
    if (scannedRows[sel] === 0) continue;
    dualVariableForRows[sel] -= delta - shortestPathCost[sel];
  }

  return {
    sink,
    pred,
    dualVariableForColumns,
    dualVariableForRows,
  };
}

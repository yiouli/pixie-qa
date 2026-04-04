/**
 * Dataset model — a named collection of Evaluable items.
 */

import type { Evaluable } from "../storage/evaluable";

/**
 * A named, ordered collection of evaluable entries.
 */
export interface Dataset {
  readonly name: string;
  readonly items: readonly Evaluable[];
}

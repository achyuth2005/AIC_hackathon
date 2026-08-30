// Re-exported under the deliverable name requested by the design spec. `QueueRow` stays the
// canonical implementation/filename since `QueueTable` and existing tests already import it by
// that name — this file just gives the same component a second, spec-matching entry point.
export { QueueRow as QueueTableRow } from './QueueRow';
export type { QueueRowProps as QueueTableRowProps } from './QueueRow';

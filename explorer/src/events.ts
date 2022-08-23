/*
* Update this file for dataset-specific implementations.
*/

// to operate on raw JSON, set AnyEvent = any
export type AnyEvent = any;

// change this implementation for your event schema
export function getEventId(event: AnyEvent): string | null {
    return null;
}

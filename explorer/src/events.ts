/*
* Update this file for dataset-specific implementations.
*/
import type {
    AliasResolutionEvent,
    AutomationRunEvent,
    ButtonPressEvent,
    CombatStateEvent,
    CommandEvent,
    MessageEvent,
    SnippetResolutionEvent
} from "@/avrae/events";

// to operate on raw JSON, set AnyEvent = any
export type AnyEvent =
    MessageEvent
    | AliasResolutionEvent
    | SnippetResolutionEvent
    | CommandEvent
    | ButtonPressEvent
    | AutomationRunEvent
    | CombatStateEvent;

// change this implementation for your event schema
export function getEventId(event: AnyEvent): string | null {
    return null;
}

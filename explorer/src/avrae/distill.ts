import type {MessageEvent} from "@/avrae/events";
import type {AnyEvent} from "@/events";

export interface RPToCommandDistill {
    utterances: MessageEvent[];
    commands: AnyEvent[];
}

export interface StateToNarrationDistill {
    state: AnyEvent[];
    utterances: MessageEvent[];
}

export interface TimeBasedDistill {
    before: MessageEvent[];
    commands: AnyEvent[];
    after: MessageEvent[];
}
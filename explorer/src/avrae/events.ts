/*
 * Models implemented from https://github.com/avrae/avrae/blob/master/cogs5e/initiative/upenn_nlp.py
 */

import type {BigNumber} from 'bignumber.js';

export interface Event {
    combat_id: string;
    event_type: string;
    timestamp: number;
}

export interface MessageEvent extends Event {
    event_type: 'message' | 'command';  // interface extension weirdness
    message_id: BigNumber;
    author_id: string;
    author_name: string;
    created_at: number;
    content: string;
    embeds: any[];
    components: any[];
    referenced_message_id?: BigNumber;
}

export interface AliasResolutionEvent extends Event {
    event_type: 'alias_resolution';
    message_id: BigNumber;
    alias_name: string;
    alias_body: string;
    content_before: string;
    content_after: string;
    prefix: string;
}

export interface SnippetResolutionEvent extends Event {
    event_type: 'snippet_resolution';
    message_id: BigNumber;
    snippet_name: string;
    snippet_body: string;
    content_after: string;
}

export interface CommandEvent extends MessageEvent {
    event_type: 'command';
    prefix: string;
    command_name: string;
    called_by_alias: boolean;
    caster?: any;
    targets?: any[];
}

export interface ButtonPressEvent extends Event {
    event_type: 'button_press';
    interaction_id: BigNumber;
    interaction_message_id: BigNumber;
    author_id: string;
    author_name: string;
    button_id: string;
    button_label: string;
}

export interface AutomationRunEvent extends Event {
    event_type: 'automation_run';
    interaction_id: BigNumber;
    automation: any;
    automation_result: any;
    caster?: any;
    targets?: any[];
}

export interface CombatStateEvent extends Event {
    event_type: 'combat_state_update';
    probable_interaction_id: BigNumber;
    data: any;
    human_readable: string;
}

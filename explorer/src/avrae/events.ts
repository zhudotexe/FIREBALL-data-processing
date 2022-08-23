/*
 * Models implemented from https://github.com/avrae/avrae/blob/master/cogs5e/initiative/upenn_nlp.py
 */

export interface Event {
    combat_id: string;
    event_type: string;
    timestamp: number;
}

export interface MessageEvent extends Event {
    event_type: 'message';
    message_id: number;
    author_id: string;
    author_name: string;
    created_at: number;
    content: string;
    embeds: any[];
    components: any[];
    referenced_message_id?: number;
}

export interface AliasResolutionEvent extends Event {
    event_type: 'alias_resolution';
    message_id: number;
    alias_name: string;
    alias_body: string;
    content_before: string;
    content_after: string;
    prefix: string;
}

export interface SnippetResolutionEvent extends Event {
    event_type: 'snippet_resolution';
    message_id: number;
    snippet_name: string;
    snippet_body: string;
    content_after: string;
}

export interface CommandEvent extends Event {
    event_type: 'command';
    prefix: string;
    command_name: string;
    called_by_alias: boolean;
    caster?: any;
    targets?: any[];
}

// class RecordedButtonInteraction(RecordedEvent):
// """
// A button was clicked in a recorded channel.
//     Causality: This is the first event in an interaction context.
// """
//
// event_type = "button_press"
// interaction_id: int
// interaction_message_id: int
// author_id: str
// author_name: str
// button_id: str
// button_label: str
//
// @classmethod
// def from_interaction(cls, combat_id: str, interaction: disnake.MessageInteraction):
// return cls(
//     combat_id=combat_id,
//     interaction_id=interaction.id,
//     interaction_message_id=interaction.message.id,
//     author_id=interaction.author.id,
//     author_name=interaction.author.display_name,
//     button_id=interaction.data.custom_id,
//     button_label=interaction.component.label,
// )
//
//
// class RecordedAutomation(RecordedEvent):
// """
// An Automation document finished executing in a recorded channel.
//     Causality:
// - Must occur after a RecordedMessage or RecordedButtonInteraction with the same ``message_id`` or ``interaction_id``
// - If message, must occur before RecordedCommandInvocation with the same ``message_id``
// - Must occur before a RecordedCombatState which *may* have the same ``interaction_id``
// """
//
// event_type = "automation_run"
// interaction_id: int
// automation: Any
// automation_result: Any
// caster: Optional[dict]  # this is a StatBlock, typed as dict since StatBlock does not inherit from BaseModel
// targets: Optional[List[dict]]
//
// @classmethod
// def new(
//     cls,
//         ctx: Union["AvraeContext", disnake.Interaction],
//     combat: "Combat",
//     automation: "Automation",
//     automation_result: "AutomationResult",
//     caster: "StatBlock",
//     targets: List[Union["StatBlock", str]],
// ):
// return cls(
//     combat_id=combat.nlp_record_session_id,
//     interaction_id=interaction_id(ctx),
//     automation=automation.to_dict(),
//     automation_result=automation_result.to_dict(),
//     caster=caster.to_dict(),
//     targets=[t.to_dict() if hasattr(t, "to_dict") else t for t in targets],
// )
//
//
// class RecordedCombatState(RecordedEvent):
// """
// The recorded combat has been committed.
//     Causality:
// - Must occur after a RecordedMessage or RecordedButtonInteraction which *may* have the same ``message_id`` or
//     ``interaction_id``
// - Must occur before RecordedCommandInvocation which *may* have the same ``message_id`` or ``interaction_id``
// """
//
// event_type = "combat_state_update"
// # due to caching this might not actually be the interaction this state update is tied to
// probable_interaction_id: int
// data: Any
// human_readable: str
//
// @classmethod
// def from_combat(cls, combat: "Combat", ctx: Union["AvraeContext", disnake.Interaction]):
// return cls(
//     combat_id=combat.nlp_record_session_id,
//     probable_interaction_id=interaction_id(ctx),
//     data=combat.to_dict(),
//     human_readable=combat.get_summary(private=True),
// )
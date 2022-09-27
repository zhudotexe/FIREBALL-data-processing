<script setup lang="ts">
import type {MessageEvent} from "@/avrae/events";
import {
  DiscordButton,
  DiscordButtons,
  DiscordEmbed,
  DiscordEmbedField,
  DiscordEmbedFields,
  DiscordMarkdown,
  DiscordMessage,
  DiscordMessages,
} from '@discord-message-components/vue'

const props = defineProps<{ event: MessageEvent }>();

function computeMessageButtons(components: any[]) {
  const out: any[] = [];
  const recurse = (components: any[]) => {
    for (const component of components) {
      switch (component.type) {
        case 1:  // actionrow
          recurse(component.components);
          break;
        case 2:  // button
          out.push(component);
          break;
      }
    }
  }
  recurse(components ?? []);
  return out;
}

const allMessageButtons = computeMessageButtons(props.event.components);
</script>

<template>
  <div>
    <DiscordMessages light-theme>
      <DiscordMessage :author="event.author_name" :timestamp="new Date(event.created_at * 1000)">
        <DiscordMarkdown>
          {{ event.content }}
        </DiscordMarkdown>

        <!-- embeds -->
        <DiscordEmbed v-for="embed in event.embeds"
                      :author-icon="embed.author?.icon_url"
                      :author-name="embed.author?.name"
                      :border-color="embed.color"
                      :embed-title="embed.title"
                      :footer-icon="embed.footer?.icon_url"
                      :image="embed.image?.url"
                      :thumbnail="embed.thumbnail?.url">
          <DiscordMarkdown>
            {{ embed.description }}
          </DiscordMarkdown>

          <DiscordEmbedFields v-if="embed.fields?.length">
            <DiscordEmbedField v-for="field in embed.fields" :field-title="field.name" :inline="field.inline">
              <DiscordMarkdown>
                {{ field.value }}
              </DiscordMarkdown>
            </DiscordEmbedField>
          </DiscordEmbedFields>
        </DiscordEmbed>

        <!-- buttons -->
        <DiscordButtons v-if="allMessageButtons.length">
          <DiscordButton v-for="button in allMessageButtons">
            {{ button.label }}
          </DiscordButton>
        </DiscordButtons>
      </DiscordMessage>
    </DiscordMessages>

    <details>
      <summary>
        message
      </summary>
      <pre>{{ event }}</pre>
    </details>
  </div>
</template>

<style scoped>
:deep(.discord-embed-title) {
  color: #0a0a0a !important;
}

:deep(.discord-markdown-content > pre) {
  padding: 0;
}

:deep(.d-emoji) {
  height: 1.5em;
}
</style>

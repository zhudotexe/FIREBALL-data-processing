<script setup lang="ts">
import type {MessageEvent} from "@/avrae/events";

defineProps<{ event: MessageEvent }>();
</script>

<template>
  <div>
    {{ event.author_name }}: {{ event.content }}
    <details>
      <summary>
        message
      </summary>
      <pre>{{ event }}</pre>
    </details>
  </div>
</template>

<style scoped>
/* css goes here */
</style>

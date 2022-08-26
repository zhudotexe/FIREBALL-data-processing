<script setup lang="ts">
import type {AnyEvent} from "@/events";

defineProps<{ event: AnyEvent }>();
</script>

<template>
  <details>
    <summary>
      {{ event.event_type }}
    </summary>
    <pre>{{ event }}</pre>
  </details>
</template>

<style scoped>
/* css goes here */
</style>

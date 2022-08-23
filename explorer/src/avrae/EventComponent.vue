<script setup lang="ts">
import type {AnyEvent} from "@/events";

defineProps<{ event: AnyEvent }>();
</script>

<template>
  <!-- by default, this displays the event as JSON - update the template to your liking -->
  <pre>
    {{ event }}
  </pre>
</template>

<style scoped>
/* css goes here */
</style>

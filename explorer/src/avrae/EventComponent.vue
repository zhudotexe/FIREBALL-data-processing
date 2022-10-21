<script setup lang="ts">
import DefaultEventComponent from "@/avrae/DefaultEventComponent.vue";
import MessageEventComponent from "@/avrae/MessageEventComponent.vue";
import type {AnyEvent} from "@/events";

defineProps<{
  event: AnyEvent;
  displayCommandAsMessage?: boolean;
}>();
</script>

<template>
  <div class="block">
    <MessageEventComponent :event="event"
                           v-if="event.event_type === 'message' || (displayCommandAsMessage && event.event_type === 'command')"/>
    <DefaultEventComponent :event="event" v-else/>
  </div>
</template>

<style scoped>
/* css goes here */
</style>

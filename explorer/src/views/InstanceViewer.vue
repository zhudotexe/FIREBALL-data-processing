<script setup lang="ts">
import {DatasetClient} from "@/client";
import {onMounted, reactive} from "vue";

// component setup
const props = defineProps<{
  client: DatasetClient;
  instanceId: string;
}>();

// data
const events = reactive<any[]>([]);

// hooks
onMounted(async () => {
  for await (const event of props.client.loadEventsForInstance(props.instanceId)) {
    events.push(event);
  }
});
</script>

<template>
  you are viewing {{ instanceId }}<br>
  {{ events.length }}<br>
  <!--<div v-for="event in events">-->
  <!--  <pre>{{ event }}</pre>-->
  <!--</div>-->
</template>

<style scoped>

</style>
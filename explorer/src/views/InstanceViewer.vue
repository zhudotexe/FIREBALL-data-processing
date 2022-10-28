<script setup lang="ts">
import type {RPToCommandDistill, StateToNarrationDistill, TimeBasedDistill} from "@/avrae/distill";
import type {DatasetClient} from "@/client";
import type {AnyEvent} from "@/events";
import DistillExperiment1Tab from "@/views/DistillExperiment1Tab.vue";
import DistillNarrationTab from "@/views/DistillNarrationTab.vue";
import DistillRPTab from "@/views/DistillRPTab.vue";
import EventsTab from "@/views/EventsTab.vue";
import {onMounted, reactive, ref} from "vue";

// component setup
const props = defineProps<{
  client: DatasetClient;
  instanceId: string;
}>();

const activeTab = ref(0);

// data
const events = reactive<AnyEvent[]>([]);
const rpDistill = reactive<RPToCommandDistill[]>([]);
const narrationDistill = reactive<StateToNarrationDistill[]>([]);
const experiment1Distill = reactive<TimeBasedDistill[]>([]);
const isLoading = ref(true);

// hooks
onMounted(async () => {
  for await (const event of props.client.loadEventsForInstance(props.instanceId)) {
    events.push(event);
  }
  isLoading.value = false;
});
onMounted(async () => {
  for await (const event of props.client.loadRPCommandDistill(props.instanceId)) {
    rpDistill.push(event);
  }
});
onMounted(async () => {
  for await (const event of props.client.loadStateNarrationDistill(props.instanceId)) {
    narrationDistill.push(event);
  }
});
onMounted(async () => {
  for await (const event of props.client.loadTimeBasedDistill(props.instanceId)) {
    experiment1Distill.push(event);
  }
});
</script>

<template>
  <div class="container">
    <section class="section">
      <h1 class="title">Instance Viewer</h1>
      <p class="subtitle mb-1">Instance <i>{{ instanceId }}</i></p>
      <p class="content is-small">
        <RouterLink to="/">Back to Instances</RouterLink>
      </p>

      <div class="content">
        <ul>
          <li>Events loaded: {{ events.length }} <span v-if="isLoading">(loading...)</span></li>
          <li v-for="heuristic in client.heuristicIds">
            {{ heuristic }}: {{ client.heuristicsByInstance[instanceId][heuristic] }}
          </li>
        </ul>
      </div>
    </section>

    <div class="tabs">
      <ul>
        <li :class="{ 'is-active': activeTab === 0 }">
          <a @click="activeTab = 0">Events ({{ events.length }})</a>
        </li>
        <li :class="{ 'is-active': activeTab === 1 }" v-if="rpDistill.length > 0">
          <a @click="activeTab = 1">Distilled: RP to Command ({{ rpDistill.length }})</a>
        </li>
        <li :class="{ 'is-active': activeTab === 2 }" v-if="narrationDistill.length > 0">
          <a @click="activeTab = 2">Distilled: State to Narration ({{ narrationDistill.length }})</a>
        </li>
        <li :class="{ 'is-active': activeTab === 3 }" v-if="experiment1Distill.length > 0">
          <a @click="activeTab = 3">Distilled: By Time ({{ experiment1Distill.length }})</a>
        </li>
      </ul>
    </div>

    <!-- events -->
    <div v-if="activeTab === 0">
      <EventsTab :events="events"/>
    </div>

    <!-- distill: rp -->
    <div v-if="activeTab === 1">
      <DistillRPTab :events="rpDistill"/>
    </div>

    <!-- distill: narration -->
    <div v-if="activeTab === 2">
      <DistillNarrationTab :events="narrationDistill"/>
    </div>

    <!-- distill: group by time -->
    <div v-if="activeTab === 3">
      <DistillExperiment1Tab :events="experiment1Distill"/>
    </div>

  </div>
</template>

<style scoped>

</style>
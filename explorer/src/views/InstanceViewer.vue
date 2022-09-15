<script setup lang="ts">
import EventComponent from "@/avrae/EventComponent.vue";
import type {DatasetClient} from "@/client";
import Paginator from "@/components/Paginator.vue";
import type {AnyEvent} from "@/events";
import {computed, onMounted, reactive, ref} from "vue";

// component setup
const props = defineProps<{
  client: DatasetClient;
  instanceId: string;
}>();


// data
const events = reactive<AnyEvent[]>([]);
const isLoading = ref(true);
const pagination = reactive({
  currentPage: 0,
  numPerPage: 250
});

// computed
const numPages = computed(() => Math.ceil(events.length / pagination.numPerPage));
const currentPageEvents = computed(() => events.slice(pagination.currentPage * pagination.numPerPage, (pagination.currentPage + 1) * pagination.numPerPage));

// hooks
onMounted(async () => {
  for await (const event of props.client.loadEventsForInstance(props.instanceId)) {
    events.push(event);
  }
  isLoading.value = false;
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

    <section class="section">
      <EventComponent v-for="event in currentPageEvents" :event="event"/>

      <Paginator :current-page="pagination.currentPage"
                 :num-pages="numPages"
                 @previous-page="pagination.currentPage--"
                 @next-page="pagination.currentPage++"/>
    </section>
  </div>
</template>

<style scoped>

</style>
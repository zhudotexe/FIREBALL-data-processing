<script setup lang="ts">
import EventComponent from "@/avrae/EventComponent.vue";
import Paginator from "@/components/Paginator.vue";
import type {AnyEvent} from "@/events";
import {computed, reactive} from "vue";

// component setup
const props = defineProps<{
  events: AnyEvent[];
}>();

// data
const pagination = reactive({
  currentPage: 0,
  numPerPage: 250
});

// computed
const numPages = computed(() => Math.ceil(props.events.length / pagination.numPerPage));
const currentPageEvents = computed(() => props.events.slice(pagination.currentPage * pagination.numPerPage, (pagination.currentPage + 1) * pagination.numPerPage));
</script>

<template>
  <EventComponent v-for="event in currentPageEvents" :event="event"/>

  <Paginator :current-page="pagination.currentPage"
             :num-pages="numPages"
             @previous-page="pagination.currentPage--"
             @next-page="pagination.currentPage++"/>
</template>

<style scoped>

</style>
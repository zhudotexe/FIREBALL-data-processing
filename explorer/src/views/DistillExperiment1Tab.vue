<script setup lang="ts">
import type {TimeBasedDistill} from "@/avrae/distill";
import EventComponent from "@/avrae/EventComponent.vue";
import Paginator from "@/components/Paginator.vue";
import {computed, reactive} from "vue";

// component setup
const props = defineProps<{
  events: TimeBasedDistill[];
}>();

// data
const pagination = reactive({
  currentPage: 0,
  numPerPage: 10
});

// computed
const numPages = computed(() => Math.ceil(props.events.length / pagination.numPerPage));
const currentPageEvents = computed(() => props.events.slice(pagination.currentPage * pagination.numPerPage, (pagination.currentPage + 1) * pagination.numPerPage));
</script>

<template>
  <div class="box" v-for="distill in currentPageEvents">
    <EventComponent v-for="event in distill.before" :event="event"/>
    <hr>
    <div class="the-commands">
      <EventComponent v-for="event in distill.commands" :event="event"/>
    </div>
    <hr>
    <EventComponent v-for="event in distill.after" :event="event"/>
  </div>


  <Paginator :current-page="pagination.currentPage"
             :num-pages="numPages"
             @previous-page="pagination.currentPage--"
             @next-page="pagination.currentPage++"/>
</template>

<style scoped>
.the-commands {
  background: #f4f4f4;
  margin: -0.5em;
  padding: 0.5em;
}
</style>
<script setup lang="ts">
import type {RPToCommandDistill} from "@/avrae/distill";
import EventComponent from "@/avrae/EventComponent.vue";
import Paginator from "@/components/Paginator.vue";
import {computed, reactive} from "vue";

// component setup
const props = defineProps<{
  events: RPToCommandDistill[];
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
    <div class="the-rp">
      <EventComponent v-for="event in distill.utterances" :event="event"/>
    </div>
    <hr>
    <EventComponent v-for="event in distill.commands" :event="event" display-command-as-message/>
  </div>


  <Paginator :current-page="pagination.currentPage"
             :num-pages="numPages"
             @previous-page="pagination.currentPage--"
             @next-page="pagination.currentPage++"/>
</template>

<style scoped>
.the-rp {
  background: #f4f4f4;
  margin: -0.5em;
  padding: 0.5em;
}
</style>
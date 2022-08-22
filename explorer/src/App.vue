<script setup lang="ts">
import {DatasetClient} from "@/client";
import {onMounted, reactive} from "vue";
import {RouterView} from 'vue-router';

// app setup
const client = reactive(new DatasetClient());

// hooks
onMounted(() => {
  client.init();
});
</script>

<template>
  <RouterView :client="client"/>
</template>

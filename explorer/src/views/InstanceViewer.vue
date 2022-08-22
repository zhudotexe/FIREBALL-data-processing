<script setup lang="ts">
import {DatasetClient} from "@/client";

// component setup
const props = defineProps<{
  client: DatasetClient;
  instanceId: string;
}>();
</script>

<template>
  you are viewing {{ instanceId }}
</template>

<style scoped>

</style>
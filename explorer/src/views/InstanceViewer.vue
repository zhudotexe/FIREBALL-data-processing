<script setup lang="ts">
import EventComponent from "@/avrae/EventComponent.vue";
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
  <div class="container">
    <section class="section">
      <p>
        you are viewing {{ instanceId }}
      </p>
      <p>
        {{ events.length }}
      </p>
    </section>
  </div>
</template>

<style scoped>

</style>
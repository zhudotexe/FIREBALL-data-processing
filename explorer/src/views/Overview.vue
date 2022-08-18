<script setup lang="ts">
import {DatasetClient} from "@/client";
import DatasetTable from "@/components/DatasetTable.vue";
import {onMounted, reactive, ref} from "vue";

// data
const client = reactive(new DatasetClient());
const viewInstanceId = ref("");
const viewInstanceIdError = ref("");

// methods
function onViewInstanceId() {
  if (client.instanceIds.includes(viewInstanceId.value)) {
    viewInstanceIdError.value = "This instance is not in the dataset.";
    return;
  }
  // todo route to instance view
}

// hooks
onMounted(() => {
  client.init();
});
</script>

<template>
  <div class="container">
    <section class="section">
      <h1 class="title">Dataset Overview</h1>
      <p v-if="!client.indexLoaded">
        Loading...
      </p>
      <div v-else>
        <p>
          Welcome to AWS Kinesis Dataset Exploration Tool. {{ client.instanceIds.length }} instances loaded for dataset
          {{ client.checksum }}.
        </p>
        <p>
          Select an instance below to view its events, or enter an instance ID here to view it:
        </p>
        <div class="field has-addons">
          <div class="control is-expanded">
            <input class="input" type="text" placeholder="Instance ID" v-model="viewInstanceId">
            <p class="help is-danger" v-if="viewInstanceIdError">{{ viewInstanceIdError }}</p>
          </div>
          <div class="control">
            <a class="button is-info" @click="onViewInstanceId()">
              Go
            </a>
          </div>
        </div>
      </div>
    </section>

    <section class="section" v-if="client.heuristicsLoaded">
      <DatasetTable :client="client"/>
    </section>
  </div>
</template>

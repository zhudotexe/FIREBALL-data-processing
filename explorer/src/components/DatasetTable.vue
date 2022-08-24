<script setup lang="ts">
import type {DatasetClient} from "@/client";
import Paginator from "@/components/Paginator.vue";
import SortIcon from "@/components/SortIcon.vue";
import {SortOrder} from "@/utils";
import {computed, reactive} from "vue";

// component setup
const props = defineProps<{ client: DatasetClient }>();

// state
const pagination = reactive({
  currentPage: 0,
  numPerPage: 250
});
const sortOrders = reactive(new Map<string, SortOrder>());  // heuristic id to sort order

// computed
const sortedInstances = computed(() => {
  let instances = Object.entries(props.client.heuristicsByInstance);
  // sort: return first non-zero sort
  return instances.sort(([instanceIdA, a], [instanceIdB, b]) => {
    for (const [heuristicId, direction] of sortOrders) {
      let val = 0;
      if (heuristicId === '_id') {
        val = instanceIdA.localeCompare(instanceIdB);
      } else {
        val = a[heuristicId] - b[heuristicId]
      }
      if (direction === SortOrder.DESC) {
        val = -val;
      }
      if (val) return val;
    }
    return instanceIdA.localeCompare(instanceIdB);
  });
});
const numPages = computed(() => Math.ceil(props.client.instanceIds.length / pagination.numPerPage));
const currentPageInstances = computed(() => sortedInstances.value.slice(pagination.currentPage * pagination.numPerPage, (pagination.currentPage + 1) * pagination.numPerPage));

// methods
function getSortIndex(sorterKey: string): number | null {
  const idx = Array.from(sortOrders.keys()).indexOf(sorterKey);
  return idx === -1 ? null : idx;
}

function getSortDirection(sorterKey: string): SortOrder {
  return sortOrders.get(sorterKey) ?? SortOrder.NONE;
}

function onSortDirectionChange(sorterKey: string, direction: SortOrder) {
  if (direction === SortOrder.NONE) {
    sortOrders.delete(sorterKey);
  } else {
    sortOrders.set(sorterKey, direction);
  }
}
</script>

<template>
  <div class="table-container mt-4">
    <table class="table is-striped is-fullwidth is-hoverable">
      <thead>
      <tr>
        <th>
          <span class="icon-text">
            <span>Instance ID</span>
            <SortIcon class="ml-1"
                      :index="getSortIndex('_id')"
                      :direction="getSortDirection('_id')"
                      @directionChanged="onSortDirectionChange('_id', $event)"/>
          </span>
        </th>
        <!-- dynamic cols by heuristics -->
        <th v-for="heuristic in client.heuristicIds">
          <span class="icon-text">
            <span>{{ heuristic }}</span>
            <SortIcon class="ml-1"
                      :index="getSortIndex(heuristic)"
                      :direction="getSortDirection(heuristic)"
                      @directionChanged="onSortDirectionChange(heuristic, $event)"/>
          </span>
        </th>
      </tr>
      </thead>

      <tbody>
      <tr v-for="[instanceId, instanceHeuristics] in currentPageInstances">
        <td>
          <RouterLink :to="`/instances/${instanceId}`">{{ instanceId }}</RouterLink>
        </td>
        <td v-for="heuristicId in client.heuristicIds">
          {{ instanceHeuristics[heuristicId] }}
        </td>
      </tr>
      </tbody>
    </table>

    <Paginator :current-page="pagination.currentPage"
               :num-pages="numPages"
               @previous-page="pagination.currentPage--"
               @next-page="pagination.currentPage++"/>
  </div>
</template>

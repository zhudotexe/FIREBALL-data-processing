<script setup lang="ts">
defineProps<{
  numPages: number;
  currentPage: number;
}>();

const emit = defineEmits<{
  (e: 'previousPage'): void,
  (e: 'nextPage'): void
}>();

function onPreviousPageClicked() {
  emit('previousPage');
}

function onNextPageClicked() {
  emit('nextPage');
}
</script>

<template>
  <div class="level" v-if="numPages > 1">
    <p class="level-item">
      <button class="button mr-2" v-if="currentPage > 0" @click="onPreviousPageClicked">
        <span class="icon is-small">
          <font-awesome-icon :icon="['fas', 'angle-left']"/>
        </span>
      </button>
      <span>Page {{ currentPage + 1 }} / {{ numPages }}</span>
      <button class="button ml-2" v-if="currentPage < numPages - 1" @click="onNextPageClicked">
        <span class="icon is-small">
          <font-awesome-icon :icon="['fas', 'angle-right']"/>
        </span>
      </button>
    </p>
  </div>
</template>

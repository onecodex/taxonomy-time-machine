<script setup lang="ts">
const apiBase = import.meta.env.VITE_API_BASE || `${window.location.origin}/api`

import TaxonomyTimeMachine from "./components/TaxonomyTimeMachine.vue";
</script>

<template>
  <TaxonomyTimeMachine :api-base="apiBase" />
</template>

<style scoped></style>

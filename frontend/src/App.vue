<script setup lang="ts">
const apiBase =
  import.meta.env.VITE_API_BASE || `${window.location.origin}/api`;
</script>

<template>
  <router-view v-slot="{ Component }">
    <component :is="Component" :api-base="apiBase" />
  </router-view>
</template>

<style scoped></style>

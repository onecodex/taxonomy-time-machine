<script lang="ts">
import { defineComponent, ref, watch } from 'vue';

export default defineComponent({
  name: 'SearchComponent',
  setup() {
    // Defining the reactive properties with appropriate types
    const taxId = ref<string>('498019');
    const results = ref<object[]>([]);
    const lineage = ref<object[]>([]);
    const version = ref<string>('');

    const error = ref<string | null>(null);
    let timeout: ReturnType<typeof setTimeout> | null = null;

    // Debounced input handler
    const onInput = () => {
      if (timeout) clearTimeout(timeout);
      timeout = setTimeout(() => {
        fetchLineage();
        fetchHistory();
      }, 300);
    };

    // this takes two parameters:
    // tax ID and version
    const fetchLineage = async() => {
      if (!taxId.value.toString().trim()) {
        lineage.value = [];
        return
      }

      const response = await fetch(`http://localhost:5000/lineage?tax_id=${encodeURIComponent(taxId.value)}&version=${encodeURIComponent(version.value)}`);

      if (!response.ok) {
        throw new Error('API request failed');
      }

      const data = await response.json()
      lineage.value = data || [];
    };

    // Fetch function with types for API handling
    const fetchHistory = async () => {
      if (!taxId.value.toString().trim()) {
        results.value = [];
        return;
      }

      const response = await fetch(`http://localhost:5000/search?tax_id=${encodeURIComponent(taxId.value)}`);
      if (!response.ok) {
        throw new Error('API request failed');
      }

      const data = await response.json()
      results.value = data || [];
    };

    const updateTaxId = (argTaxId: string) => {
      taxId.value = argTaxId;
      onInput();
    };

    const updateVersion = (argVersion: string) => {
      version.value = argVersion;
      onInput();
    };

    // Watcher to reset error state on taxId change
    watch(taxId, () => {
      error.value = null;
    });

    return {
      taxId,
      lineage,
      results,
      error,
      onInput,
      updateTaxId,
      updateVersion,
    };
  },
});
</script>

<template>
  <h1>Taxonomy</h1>
  <div class="card">
    <input 
      type="text" 
      v-model="taxId" 
      placeholder="Type to search..." 
      @input="onInput" />

    <div v-if="error" class="error">{{ error }}</div>

    <!-- lineage table -->

    <div v-if="lineage">
      <h2>Lineage</h2>

      <table>
        <tr>
          <th>tax_id</th>
          <th>name</th>
          <th>rank</th>
        </tr>
        <tr v-for="node in lineage">
          <td>{{ node.tax_id }}</td>
          <td>{{ node.name }}</td>
          <td>{{ node.rank }}</td>
        </tr>
      </table>
    </div>

    <!-- version table -->
    <h2>History</h2>
    <table>
      <tr>
        <th>event</th>
        <th>date</th>
        <th>tax_id</th>
        <th>parent_id</th>
        <th>name</th>
        <th>rank</th>
      </tr>
      <tr v-if="results" v-for="event in results">
        <td>{{ event.event_name }}</td>
        <td>
          <a href="#" @click.prevent="updateVersion(event.version_date)">{{ event.version_date }}</a>
        </td>
        <td>
          <a href="#" @click.prevent="updateTaxId(event.tax_id)">{{ event.tax_id }}</a>
        </td>
        <td>{{ event.parent_id }}</td>
        <td>{{ event.name }}</td>
        <td>{{ event.rank }}</td>
      </tr>
    </table>

  </div>
</template>

<style scoped>
.read-the-docs {
  color: #888;
}
</style>

<script lang="ts">
import { defineComponent, ref, watch } from 'vue';

export default defineComponent({
  name: 'SearchComponent',
  setup() {
    // Defining the reactive properties with appropriate types
    const query = ref<string>('');
    const results = ref<object[]>([]);
    const error = ref<string | null>(null);
    let timeout: ReturnType<typeof setTimeout> | null = null;

    // Debounced input handler
    const onInput = () => {
      if (timeout) clearTimeout(timeout);
      timeout = setTimeout(() => {
        fetchResults();
      }, 300);
    };

    // Fetch function with types for API handling
    const fetchResults = async () => {
      if (!query.value.trim()) {
        results.value = [];
        return;
      }

      try {
        const response = await fetch(`http://localhost:5000/search?tax_id=${encodeURIComponent(query.value)}`);
        if (!response.ok) {
          throw new Error('API request failed');
        }

        const data = await response.json()
        results.value = data || [];
      } catch (err: unknown) {
        error.value = err instanceof Error ? err.message : 'Unknown error';
      }
    };

    // Watcher to reset error state on query change
    watch(query, () => {
      error.value = null;
    });

    return {
      query,
      results,
      error,
      onInput,
    };
  },
});
</script>

<template>
  <h1>Taxonomy</h1>
  <div class="card">
    <input 
      type="text" 
      v-model="query" 
      placeholder="Type to search..." 
      @input="onInput" />

    <div v-if="error" class="error">{{ error }}</div>
    <table>
      <tr>
        <th>event</th>
        <th>date</th>
        <th>tax_id</th>
        <th>parent_id</th>
        <th>name</th>
      </tr>
      <tr v-if="results" v-for="event in results">
        <td>{{ event.event_name }}</td>
        <td>{{ event.version_date }}</td>
        <td>{{ event.tax_id }}</td>
        <td>{{ event.parent_id }}</td>
        <td>{{ event.name }}</td>
      </tr>
    </table>
  </div>
</template>

<style scoped>
.read-the-docs {
  color: #888;
}
</style>

<script lang="ts">
import { defineComponent, ref, watch, computed } from 'vue';

export default defineComponent({
  name: 'SearchComponent',
  setup() {
    const formatDate = (isoDate: string): string => {
      const date = new Date(isoDate);
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0'); // Months are zero-based, so add 1
      const day = String(date.getDate()).padStart(2, '0');
      return `${year}-${month}-${day}`;
    };

    // ~~~~~~~~~~~~~~~~~~~
    // reactive properties
    // ~~~~~~~~~~~~~~~~~~~

    // query parameters
    const taxId = ref<string>('');
    const version = ref<string>('');
    const query = ref<string>('');

    // results
    const versions = ref<object[]>([]);
    const lineage = ref<object[]>([]);
    const children = ref<object[]>([]);

    // typeahead stuff
    const suggestions = ref<object[]>([]);
    const loading = ref<boolean>(false);
    const highlightedIndex = ref<number>(-1);
    const showSuggestions = computed(() => suggestions.value.length > 0);

    const emoji = ref<string>('🌳');

    // a common place to store errors
    const error = ref<string | null>(null);

    let debounceTimeout: ReturnType<typeof setTimeout> | null = null;

    const isNumeric = (value) => !isNaN(value) && value !== null && value !== '' && !isNaN(parseFloat(value));

    // Watcher to reset error state on query change
    watch(query, () => {
      error.value = null;
    });

    watch(taxId, () => {
        fetchLineage();
        fetchVersions();
        fetchChildren();
      }
    );

    watch(version, () => {
        fetchLineage();
        fetchVersions();
        fetchChildren();
      }
    );

    // Input handler with debounce
    const onInput = () => {
      if (debounceTimeout) clearTimeout(debounceTimeout);
      debounceTimeout = setTimeout(() => {
        fetchSuggestions();
      }, 300);
    };

    // Fetch suggestions dynamically
    const fetchSuggestions = async () => {
      if (!query.value.trim()) {
        suggestions.value = [];
        version.value = null;
        taxId.value = null;
        return;
      }

      loading.value = true;
      error.value = null;

      try {
        const response = await fetch(
          `http://localhost:5000/search?query=${encodeURIComponent(query.value)}`
        );
        if (!response.ok) throw new Error(`API error: ${response.statusText}`);

        const data = await response.json();
        suggestions.value = data;
      } catch (err) {
        console.error(err);
        error.value = 'Failed to fetch suggestions.';
      } finally {
        loading.value = false;
      }
    };

    // Manage selection
    const selectSuggestion = (suggestion: object) => {
      query.value = suggestion.name; // Use the `name` field
      taxId.value = suggestion.tax_id; // Update `taxId` from selected suggestion
      version.value = suggestion.version_date; // Update version if available
      suggestions.value = []; // Clear suggestions
    };

    // Navigation with keyboard
    const highlightNext = () => {
      if (highlightedIndex.value < suggestions.value.length - 1) {
        highlightedIndex.value++;
      }
    };

    const highlightPrev = () => {
      if (highlightedIndex.value > 0) {
        highlightedIndex.value--;
      }
    };

    const selectHighlighted = () => {
      if (highlightedIndex.value >= 0 && highlightedIndex.value < suggestions.value.length) {
        selectSuggestion(suggestions.value[highlightedIndex.value]);
      }
    };

    const highlightIndex = (index: number) => {
      highlightedIndex.value = index;
    };

    // this sets taxId
    const setTaxId = async() => {
      version.value = null;
      if (isNumeric(query.value)) {
        taxId.value = query.value
      } else {
        findTaxId();
      }
    };

    const findTaxId = async() => {
      if (query.value == null || !query.value.toString().trim()) {
        taxId.value = null;
        return;
      }

      const response = await fetch(`http://localhost:5000/search?query=${encodeURIComponent(query.value)}`);

      if (!response.ok) {
        throw new Error('API request failed');
      }

      const data = await response.json();

      if (data.length == 0) {
        taxId.value = null;
        version.value = null;
      } else {
        taxId.value = data[0]['tax_id'];
        version.value = data[0]["version_date"];
      }
    };

    const fetchChildren = async() => {
      if (taxId.value == null || !taxId.value.toString().trim()) {
        children.value = [];
        return
      }

      const response = await fetch(`http://localhost:5000/children?tax_id=${encodeURIComponent(taxId.value)}&version_date=${encodeURIComponent(version.value)}`);

      if (!response.ok) {
        throw new Error('API request failed');
      }

      const data = await response.json()
      children.value = data || [];
    };


    // this takes two parameters:
    // tax ID and version
    const fetchLineage = async() => {
      if (taxId.value == null || !taxId.value.toString().trim()) {
        lineage.value = [];
        return
      }

      const response = await fetch(`http://localhost:5000/lineage?tax_id=${encodeURIComponent(taxId.value)}&version_date=${encodeURIComponent(version.value)}`);

      if (!response.ok) {
        throw new Error('API request failed');
      }

      const data = await response.json();

      lineage.value = data || [];

      if (lineage.value.some(item => item.name === "Fungi")) {
          emoji.value = "🍄";
      } else if (lineage.value.some(item => item.name === "Bacteria")) {
          emoji.value = "🦠";
      } else if (lineage.value.some(item => item.name === "Archaea")) {
          emoji.value = "🦠";
      } else if (lineage.value.some(item => item.name === "Viruses")) {
          emoji.value = "😷";
      } else if (lineage.value.some(item => item.name === "Homo sapiens")) {
          emoji.value = "🧑‍🔬";
      } else if (lineage.value.some(item => item.name === "Canis lupus")) {
          emoji.value = "🐕";
      } else if (lineage.value.some(item => item.name === "Felis catus")) {
          emoji.value = "🐈";
      } else if (lineage.value.some(item => item.name === "Gallus gallus")) {
          emoji.value = "🐔";
      } else if (lineage.value.some(item => item.name === "Bos taurus")) {
          emoji.value = "🐄";
      } else if (lineage.value.some(item => item.name === "Serpentes")) {
          emoji.value = "🐍";
      } else if (lineage.value.some(item => item.name === "Diptera")) {
          emoji.value = "🪰";
      } else if (lineage.value.some(item => item.name === "Dinosauria")) {
          emoji.value = "🦖";
      } else {
          emoji.value = "🌳";
      }
    };

    // Fetch function with types for API handling
    const fetchVersions = async () => {
      if (taxId.value == null || !taxId.value.toString().trim()) {
        lineage.value = [];
        versions.value = [];
        return;
      }

      const response = await fetch(`http://localhost:5000/versions?tax_id=${encodeURIComponent(taxId.value)}`);
      if (!response.ok) {
        throw new Error('API request failed');
      }

      const data = await response.json();
      versions.value = data || [];
    };

    const updateTaxId = (argTaxId: string) => {
      taxId.value = argTaxId;
    };

    const updateVersion = (argVersion: string) => {
      version.value = argVersion;
    };

    return {
      emoji,
      taxId,
      version,
      lineage,
      children,
      versions,
      query,
      error,
      onInput,
      updateTaxId,
      updateVersion,
      setTaxId,
      formatDate,
      suggestions,
      loading,
      fetchSuggestions,
      selectSuggestion,
      showSuggestions,
      highlightIndex,
      highlightNext,
      highlightPrev,
      selectHighlighted,
      highlightedIndex,
    };
  },
});
</script>

<template>
  <!-- Header -->
  <div class="container">
    <p class="title">{{ emoji }} Taxonomy Time Machine</p>
  </div>

  <!-- Search -->


  <section class="section">
    <div class="container">
      <div class="field">
        <div
            class="control is-expanded is-large"
            :class="{ 'is-loading': loading === true }"
        >
          <div class="search-component">
            <input
              class="input has-text-success is-primary is-large"
              type="text"
              v-model="query"
              @input="onInput"
              @keydown.down.prevent="highlightNext"
              @keydown.up.prevent="highlightPrev"
              @keydown.enter.prevent="selectHighlighted"
              placeholder="Search for a name or tax ID..."
            />
          </div>

          <!-- Suggestions Dropdown -->

          <div class="dropdown" :class="{ 'is-active': showSuggestions }">
            <div class="dropdown-menu" role="menu">
              <div class="dropdown-content">
                <div v-if="error" class="dropdown-item has-text-danger">
                  Error fetching suggestions
                </div>
                <a
                  v-for="(suggestion, index) in suggestions"
                  :key="index"
                  class="dropdown-item is-large"
                  :class="{ 'is-active': index === highlightedIndex }"
                  @mousedown.prevent="selectSuggestion(suggestion)"
                  @mouseover="highlightIndex(index)"
                >
                  {{ suggestion.name }} ({{ suggestion.tax_id }})
                </a>
              </div>
            </div>
          </div>


        </div>
      </div>


      <nav class="breadcrumb is-centered has-succeeds-separator" aria-label="breadcrumbs">
        <ul>
          <li
            v-for="v in versions"
            :class="{ 'is-active': v.version_date === version }"
            >
            <a href="#" @click.prevent="updateVersion(v.version_date)" >
              {{ formatDate(v.version_date) }}
            </a>
          </li>
        </ul>
      </nav>


      <div class="columns">

        <!-- Lineage table -->
        <div class="column auto">
          <div v-if="!!lineage.length">
            <table class="table">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Name</th>
                  <th>Tax ID</th>
                </tr>
              </thead>
              <tr v-for="node in lineage">
                <td>{{ node.rank }}</td>
                <td>{{ node.name }}</td>
                <td>
                  <a href="#" @click.prevent="updateTaxId(node.tax_id)">
                    {{ node.tax_id }}
                  </a>
                </td>
              </tr>
            </table>
            <p>Showing lineage of Tax ID <code>{{ taxId }}</code> from <code>{{ version }}</code></p>
          </div>
        </div>

        <!-- Children table -->
        <div class="column auto">
          <div v-if="!!children.length">
            <h2>Children (n={{ children.length }})</h2>
            <table class="table">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Name</th>
                  <th>Tax ID</th>
                </tr>
              </thead>
              <tr v-for="node in children">
                <td>{{ node.rank }}</td>
                <td>{{ node.name }}</td>
                <td>
                  <a href="#" @click.prevent="updateTaxId(node.tax_id)">
                    {{ node.tax_id }}
                  </a>
                </td>
              </tr>
            </table>
          </div>
        </div>

      </div>
    </div>
  </section>

  <!-- TODO make the error look more error-y -->

  <!-- Results -->


</template>

<style scoped>
.read-the-docs {
  color: #888;
}
</style>

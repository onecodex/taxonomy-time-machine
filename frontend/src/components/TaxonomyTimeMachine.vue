<script lang="ts">
import { defineComponent, ref, watch, computed } from "vue";

interface TaxonVersion {
  tax_id: string;
  parent_id: string | null;
  name: string | null;
  rank: string | null;
  version_date: string | null;
}

export default defineComponent({
  name: "SearchComponent",
  // see vite.config.ts
  props: {
    apiBase: {
      type: String,
      required: true,
    }
  },
  setup(props) {

    const apiBase = props.apiBase || `${window.location.origin}/api`;

    const formatDate = (isoDate: string | null): string => {
      if (isoDate === null) {
        return '';
      }

      const date = new Date(isoDate);
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, "0"); // Months are zero-based, so add 1
      const day = String(date.getDate()).padStart(2, "0");
      return `${year}-${month}-${day}`;
    };

    // --- Format date for display in summary text ---
    const formatDisplayDate = (isoDate: string | null): string => {
      if (!isoDate) return '';
      const date = new Date(isoDate);
      return date.toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      });
    };

    // ~~~~~~~~~~~~~~~~~~~
    // reactive properties
    // ~~~~~~~~~~~~~~~~~~~

    // query parameters
    const taxId = ref<string | null>("");
    const version = ref<string | null>("");
    const query = ref<string | null>("");

    // results
    const versions = ref<TaxonVersion[]>([]);
    const lineage = ref<TaxonVersion[]>([]);
    const children = ref<TaxonVersion[]>([]);

    // typeahead stuff
    const suggestions = ref<TaxonVersion[]>([]);
    const loading = ref<boolean>(false);
    const highlightedIndex = ref<number>(-1);
    const showSuggestions = computed(() => suggestions.value.length > 0);

    const emoji = ref<string>("🌳");

    // a common place to store errors
    const error = ref<string | null>(null);

    let debounceTimeout: ReturnType<typeof setTimeout> | null = null;

    const isNumeric = (value: null | string | number) =>
      value !== null &&
      value !== "" &&
      !isNaN(Number(value));

    // Watcher to reset error state on query change
    watch(query, () => {
      error.value = null;
    });

    watch(taxId, () => {
      fetchLineage();
      fetchVersions();
      fetchChildren();
    });

    watch(version, () => {
      fetchLineage();
      fetchVersions();
      fetchChildren();
    });

    // Input handler with debounce
    const onInput = () => {
      if (debounceTimeout) clearTimeout(debounceTimeout);
      debounceTimeout = setTimeout(() => {
        fetchSuggestions();
      }, 300);
    };

    // Fetch suggestions dynamically
    const fetchSuggestions = async () => {
      if (!(query.value || '').trim()) {
        suggestions.value = [];
        version.value = null;
        taxId.value = null;
        return;
      }

      loading.value = true;
      error.value = null;

      try {
        const response = await fetch(
          `${apiBase}/search?query=${encodeURIComponent(query.value || '')}`,
        );
        if (!response.ok) throw new Error(`API error: ${response.statusText}`);

        const data = await response.json();
        suggestions.value = data;
      } catch (err) {
        console.error(err);
        error.value = "Failed to fetch suggestions.";
      } finally {
        loading.value = false;
      }
    };

    // Manage selection
    const selectSuggestion = (suggestion: TaxonVersion) => {
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
      if (
        highlightedIndex.value >= 0 &&
        highlightedIndex.value < suggestions.value.length
      ) {
        selectSuggestion(suggestions.value[highlightedIndex.value]);
      }
    };

    const highlightIndex = (index: number) => {
      highlightedIndex.value = index;
    };

    // this sets taxId
    const setTaxId = async () => {
      version.value = null;
      if (isNumeric(query.value)) {
        taxId.value = query.value;
      } else {
        findTaxId();
      }
    };

    const findTaxId = async () => {
      if (query.value == null || !query.value.toString().trim()) {
        taxId.value = null;
        return;
      }

      const response = await fetch(
        `${apiBase}/search?query=${encodeURIComponent(query.value || '')}`,
      );

      if (!response.ok) {
        throw new Error("API request failed");
      }

      const data = await response.json();

      if (data.length == 0) {
        taxId.value = null;
        version.value = null;
      } else {
        taxId.value = data[0]["tax_id"];
        version.value = data[0]["version_date"];
      }
    };

    const fetchChildren = async () => {
      if (taxId.value == null || !taxId.value.toString().trim()) {
        children.value = [];
        return;
      }

      const response = await fetch(
        `${apiBase}/children?tax_id=${encodeURIComponent(taxId.value)}&version_date=${encodeURIComponent(version.value || '')}`,
      );

      if (!response.ok) {
        throw new Error("API request failed");
      }

      const data = await response.json();
      children.value = data || [];
    };

    // this takes two parameters:
    // tax ID and version
    const fetchLineage = async () => {
      if (taxId.value == null || !taxId.value.toString().trim()) {
        lineage.value = [];
        return;
      }

      const response = await fetch(
        `${apiBase}/lineage?tax_id=${encodeURIComponent(taxId.value)}&version_date=${encodeURIComponent(version.value || '')}`,
      );

      if (!response.ok) {
        throw new Error("API request failed");
      }

      const data = await response.json();

      lineage.value = data || [];

      if (lineage.value.some((item) => item.name === "Fungi")) {
        emoji.value = "🍄";
      } else if (lineage.value.some((item) => item.name === "Bacteria")) {
        emoji.value = "🦠";
      } else if (lineage.value.some((item) => item.name === "Archaea")) {
        emoji.value = "🦠";
      } else if (lineage.value.some((item) => item.name === "Viruses")) {
        emoji.value = "😷";
      } else if (lineage.value.some((item) => item.name === "Homo sapiens")) {
        emoji.value = "🧑‍🔬";
      } else if (lineage.value.some((item) => item.name === "Canis lupus")) {
        emoji.value = "🐕";
      } else if (lineage.value.some((item) => item.name === "Felis catus")) {
        emoji.value = "🐈";
      } else if (lineage.value.some((item) => item.name === "Gallus gallus")) {
        emoji.value = "🐔";
      } else if (lineage.value.some((item) => item.name === "Bos taurus")) {
        emoji.value = "🐄";
      } else if (lineage.value.some((item) => item.name === "Serpentes")) {
        emoji.value = "🐍";
      } else if (lineage.value.some((item) => item.name === "Diptera")) {
        emoji.value = "🪰";
      } else if (lineage.value.some((item) => item.name === "Dinosauria")) {
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

      const response = await fetch(
        `${apiBase}/versions?tax_id=${encodeURIComponent(taxId.value)}`,
      );
      if (!response.ok) {
        throw new Error("API request failed");
      }

      const data = await response.json();
      versions.value = data || [];
    };

    const updateTaxId = (argTaxId: string) => {
      taxId.value = argTaxId;
    };

    const updateVersion = (argVersion: string | null) => {
      version.value = argVersion;
    };

    // --- Add this function to handle example clicks ---
    const handleExampleClick = async (example: string) => {
      query.value = example;
      await findTaxId();
    };

    // --- Fetch the current taxon for the given taxId ---
    const currentTaxon = ref<TaxonVersion | null>(null);

    const fetchCurrentTaxon = async () => {
      if (!taxId.value) {
        currentTaxon.value = null;
        return;
      }
      // Fetch without version to get the latest
      const response = await fetch(
        `${apiBase}/search?query=${encodeURIComponent(taxId.value)}`
      );
      if (!response.ok) {
        currentTaxon.value = null;
        return;
      }
      const data = await response.json();
      currentTaxon.value = data && data.length > 0 ? data[0] : null;
    };

    // Watch taxId to update currentTaxon
    watch(taxId, () => {
      fetchCurrentTaxon();
    });

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
      formatDisplayDate,
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
      handleExampleClick,
      currentTaxon,
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
      <!-- Example Taxa Buttons -->
      <div class="example-taxa-buttons" style="margin-bottom: 1em;">
        <span style="margin-right: 0.5em; font-weight: bold;">Examples:</span>
        <button v-for="example in [
          'Wuhan seafood market pneumonia virus',
          'Bacteroides dorei',
          'Lactobacillus reuteri',
          '[Candida] auris'
        ]" :key="example" class="button is-small is-info" style="margin-right: 0.5em; margin-bottom: 0.5em;"
          @click="() => handleExampleClick(example)">
          {{ example }}
        </button>
      </div>

      <div class="field">
        <div class="control is-expanded is-large" :class="{ 'is-loading': loading === true }">
          <div class="search-component">
            <input class="input has-text-success is-primary is-large" type="text" v-model="query" @input="onInput"
              @keydown.down.prevent="highlightNext" @keydown.up.prevent="highlightPrev"
              @keydown.enter.prevent="selectHighlighted" placeholder="Search for a name or tax ID..." />
          </div>

          <!-- Suggestions Dropdown -->

          <div class="dropdown" :class="{ 'is-active': showSuggestions }">
            <div class="dropdown-menu" role="menu">
              <div class="dropdown-content">
                <div v-if="error" class="dropdown-item has-text-danger">
                  Error fetching suggestions
                </div>
                <a v-for="(suggestion, index) in suggestions" :key="index" class="dropdown-item is-large"
                  :class="{ 'is-active': index === highlightedIndex }" @mousedown.prevent="selectSuggestion(suggestion)"
                  @mouseover="highlightIndex(index)">
                  {{ suggestion.name }} ({{ suggestion.tax_id }})
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>

      <nav class="breadcrumb is-centered has-succeeds-separator" aria-label="breadcrumbs">
        <ul>
          <li v-for="v in versions" :class="{ 'is-active': v.version_date === version }">
            <a href="#" @click.prevent="updateVersion(v.version_date)">
              {{ formatDate(v.version_date) }}
            </a>
          </li>
        </ul>
      </nav>

      <!-- Current Taxon Info (moved above columns for better visibility) -->
      <div v-if="taxId && version && lineage.length && currentTaxon" style="margin-bottom: 2em; margin-top: 1em;">
        <p class="current-taxon-summary">
          Currently viewing the NCBI taxonomy for
          <strong>{{ lineage[lineage.length - 1].name }}</strong>
          ({{ taxId }}) from {{ formatDisplayDate(version) }}.<br />
          The current name for this taxon is
          <strong>{{ currentTaxon.name }}</strong>.
        </p>
      </div>

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

      <div v-if="version">
        <p class="current-taxon-summary">
          Data retrieved from
          <code>{{ `https://ftp.ncbi.nlm.nih.gov/pub/taxonomy/taxdump_archive/taxdmp_${formatDate(version)}.zip` }}</code>
          <a :href="`https://ftp.ncbi.nlm.nih.gov/pub/taxonomy/taxdump_archive/taxdmp_${formatDate(version)}.zip`"
            target="_blank" rel="noopener noreferrer" style="margin-left: 0.5em; font-size: 0.95em;">
            [download]
          </a>
        </p>
      </div>
    </div>
  </section>

  <!-- TODO make the error look more error-y -->

  <!-- Results -->
</template>

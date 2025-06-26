<script lang="ts">
import { defineComponent, ref, watch, computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiFetchWithCache } from "../utils/apiCache";
import Timeline from "./TaxonomyTimeMachine/Timeline.vue";

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
  components: {
    Timeline,
  },
  props: {
    apiBase: {
      type: String,
      required: true,
    },
  },
  setup(props) {
    const route = useRoute();
    const router = useRouter();
    const apiBase = props.apiBase || `${window.location.origin}/api`;

    const formatDate = (isoDate: string | null): string => {
      if (isoDate === null) {
        return "";
      }

      const date = new Date(isoDate);
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, "0"); // Months are zero-based, so add 1
      const day = String(date.getDate()).padStart(2, "0");
      return `${year}-${month}-${day}`;
    };

    // --- Format date for display in summary text ---
    const formatDisplayDate = (isoDate: string | null): string => {
      if (!isoDate) return "";
      const date = new Date(isoDate);
      return date.toLocaleDateString(undefined, {
        year: "numeric",
        month: "long",
        day: "numeric",
      });
    };

    // ~~~~~~~~~~~~~~~~~~~
    // reactive properties
    // ~~~~~~~~~~~~~~~~~~~

    // query parameters
    const taxId = ref<string | null>("");
    const version = ref<string | null>("");
    // The input box value, always shows the current taxon's name if available
    const query = ref<string>("");

    // Track if the user is actively typing (to avoid overwriting input)
    const userIsTyping = ref(false);

    // Separate loading state for random species button
    const randomSpeciesLoading = ref(false);

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
      value !== null && value !== "" && !isNaN(Number(value));

    // Watcher to reset error state on query change
    watch(query, () => {
      error.value = null;
    });

    // --- URL Navigation Helpers ---
    const navigateToTaxon = (
      tax_id: string | null,
      version_date: string | null = null,
    ) => {
      if (!tax_id) {
        router.push("/");
        return;
      }

      if (version_date) {
        // Format version date for URL (remove time and special characters)
        const dateOnly = version_date.split("T")[0];
        router.push(`/taxon/${tax_id}/${dateOnly}`);
      } else {
        router.push(`/taxon/${tax_id}`);
      }
    };

    // --- Initialize from route parameters on mount ---
    onMounted(() => {
      if (route.params.taxId) {
        taxId.value = route.params.taxId as string;
      }
      if (route.params.version) {
        // Convert date back to full ISO format for API calls
        const versionParam = route.params.version as string;
        if (versionParam.includes("-") && !versionParam.includes("T")) {
          version.value = versionParam + "T00:00:00";
        } else {
          version.value = versionParam;
        }
      }
    });

    // --- Watch route changes ---
    watch(route, (newRoute) => {
      if (newRoute.params.taxId !== taxId.value) {
        taxId.value = (newRoute.params.taxId as string) || "";
      }
      if (newRoute.params.version !== version.value) {
        const versionParam = newRoute.params.version as string;
        if (
          versionParam &&
          versionParam.includes("-") &&
          !versionParam.includes("T")
        ) {
          version.value = versionParam + "T00:00:00";
        } else {
          version.value = versionParam || "";
        }
      }
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
      userIsTyping.value = true;
      if (debounceTimeout) clearTimeout(debounceTimeout);
      debounceTimeout = setTimeout(() => {
        fetchSuggestions();
      }, 150);
    };

    // Fetch suggestions dynamically
    const fetchSuggestions = async () => {
      if (!(query.value || "").trim()) {
        suggestions.value = [];
        version.value = null;
        taxId.value = null;
        return;
      }

      loading.value = true;
      error.value = null;

      try {
        const url = `${apiBase}/search?query=${encodeURIComponent(query.value || "")}`;
        const data = await apiFetchWithCache(url);
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
      query.value = suggestion.name || ""; // Use the `name` field
      taxId.value = suggestion.tax_id; // Update `taxId` from selected suggestion
      version.value = suggestion.version_date; // Update version if available
      suggestions.value = []; // Clear suggestions
      userIsTyping.value = false;
      navigateToTaxon(suggestion.tax_id, suggestion.version_date);
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
        navigateToTaxon(query.value);
      } else {
        findTaxId();
      }
    };

    const findTaxId = async () => {
      if (query.value == null || !query.value.toString().trim()) {
        taxId.value = null;
        router.push("/");
        return;
      }

      const url = `${apiBase}/search?query=${encodeURIComponent(query.value || "")}`;
      const data = await apiFetchWithCache(url);

      if (data.length == 0) {
        taxId.value = null;
        version.value = null;
        router.push("/");
      } else {
        taxId.value = data[0]["tax_id"];
        version.value = data[0]["version_date"];
        navigateToTaxon(data[0]["tax_id"], data[0]["version_date"]);
      }
    };

    const fetchChildren = async () => {
      if (taxId.value == null || !taxId.value.toString().trim()) {
        children.value = [];
        return;
      }

      const url = `${apiBase}/children?tax_id=${encodeURIComponent(taxId.value)}&version_date=${encodeURIComponent(version.value || "")}`;
      const data = await apiFetchWithCache(url);
      children.value = data || [];
    };

    // this takes two parameters:
    // tax ID and version
    const fetchLineage = async () => {
      if (taxId.value == null || !taxId.value.toString().trim()) {
        lineage.value = [];
        return;
      }

      const url = `${apiBase}/lineage?tax_id=${encodeURIComponent(taxId.value)}&version_date=${encodeURIComponent(version.value || "")}`;
      const data = await apiFetchWithCache(url);

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

      const url = `${apiBase}/versions?tax_id=${encodeURIComponent(taxId.value)}`;
      const data = await apiFetchWithCache(url);
      versions.value = data || [];
    };

    const updateTaxId = (argTaxId: string) => {
      taxId.value = argTaxId;
      navigateToTaxon(argTaxId, version.value);
    };

    const updateVersion = (argVersion: string | null) => {
      version.value = argVersion;
      navigateToTaxon(taxId.value, argVersion);
    };

    // --- Add this function to handle example clicks ---
    const handleExampleClick = async (example: string) => {
      query.value = example;
      await findTaxId();
    };

    // --- Add this function to handle random species ---
    const handleRandomSpecies = async () => {
      randomSpeciesLoading.value = true;
      try {
        const response = await fetch(`${apiBase}/random-species`, {
          method: "GET",
          headers: {
            "Accept": "application/json",
          }
        });

        if (!response.ok) {
          throw new Error(`API request failed: ${response.status} ${response.statusText}`);
        }

        const data = await response.json();

        if (data && data.tax_id) {
          query.value = data.name;
          navigateToTaxon(data.tax_id);
        }
      } catch (error) {
        console.error("Error fetching random species:", error);
      } finally {
        randomSpeciesLoading.value = false;
      }
    };

    // --- Fetch the current taxon for the given taxId ---
    const currentTaxon = ref<TaxonVersion | null>(null);

    const fetchCurrentTaxon = async () => {
      if (!taxId.value) {
        currentTaxon.value = null;
        return;
      }
      // Fetch without version to get the latest
      const url = `${apiBase}/search?query=${encodeURIComponent(taxId.value)}`;
      const data = await apiFetchWithCache(url);
      currentTaxon.value = data && data.length > 0 ? data[0] : null;
    };

    // Watch taxId to update currentTaxon
    watch(taxId, () => {
      fetchCurrentTaxon();
    });

    // When taxId changes due to URL or navigation, reset userIsTyping so input box updates
    watch([taxId, version], () => {
      userIsTyping.value = false;
    });

    // Function to get CSS class for rank badges
    const getRankClass = (rank: string | null): string => {
      if (!rank) return "rank-default";

      const normalizedRank = rank.toLowerCase().trim();

      const rankClassMap: Record<string, string> = {
        superkingdom: "rank-superkingdom",
        kingdom: "rank-kingdom",
        phylum: "rank-phylum",
        class: "rank-class",
        order: "rank-order",
        family: "rank-family",
        genus: "rank-genus",
        species: "rank-species",
        subspecies: "rank-subspecies",
        strain: "rank-strain",
      };

      return rankClassMap[normalizedRank] || "rank-default";
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
      handleRandomSpecies,
      randomSpeciesLoading,
      currentTaxon,
      getRankClass,
    };
  },
});
</script>

<template>
  <!-- Header -->
  <div class="container">
    <div class="header-container">
      <h1 class="title responsive-title">{{ emoji }} Taxonomy Time Machine</h1>
      <div class="documentation-links">
        <router-link to="/bulk-resolver" class="button is-small is-info">
          🔄 Bulk Resolver
        </router-link>
        <a
          href="https://github.com/onecodex/taxonomy-time-machine"
          target="_blank"
          class="button is-small"
          >Source Code</a
        >
        <a href="/swagger-ui" target="_blank" class="button is-small"
          >API Docs (Swagger)</a
        >
        <a href="/redoc" target="_blank" class="button is-small"
          >API Docs (Redoc)</a
        >
      </div>
    </div>
  </div>

  <!-- Search -->

  <section class="section">
    <div class="container">
      <!-- Example Taxa Buttons -->
      <div class="example-taxa-buttons" style="margin-bottom: 1em">
        <span style="margin-right: 0.5em; font-weight: bold">Examples:</span>
        <button
          v-for="example in [
            'SARS-related coronavirus',
            'Bacteroides dorei',
            'Lactobacillus reuteri',
            '[Candida] auris',
          ]"
          :key="example"
          class="button is-small is-info"
          style="margin-right: 0.5em; margin-bottom: 0.5em"
          @click="() => handleExampleClick(example)"
        >
          {{ example }}
        </button>
        <button
          class="button is-small is-warning"
          style="margin-right: 0.5em; margin-bottom: 0.5em"
          @click="handleRandomSpecies"
          :disabled="randomSpeciesLoading"
          :class="{ 'is-loading': randomSpeciesLoading }"
        >
          🎲 Random Species
        </button>
      </div>

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
              spellcheck="false"
              autocorrect="off"
              autocomplete="off"
              autocapitalize="off"
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

      <!-- Timeline Component -->
      <Timeline 
        :versions="versions" 
        :current-version="version"
        @update-version="updateVersion"
      />

      <!-- Current Taxon Info (moved above columns for better visibility) -->
      <div
        v-if="taxId && version && lineage.length && currentTaxon"
        style="margin-bottom: 2em; margin-top: 1em"
      >
        <p class="current-taxon-summary">
          Currently viewing the NCBI taxonomy for
          <strong>{{ lineage[lineage.length - 1].name }}</strong>
          ({{ taxId }}) from {{ formatDisplayDate(version) }}.<br />
          The current name for this taxon is
          <strong>{{ currentTaxon.name }}</strong
          >.
        </p>
      </div>

      <!-- Lineage table -->
      <div v-if="!!lineage.length" class="taxonomy-section">
        <h2 class="section-title">Taxonomic Lineage</h2>
        <div class="table-container">
          <table class="table is-fullwidth taxonomy-table">
            <thead>
              <tr>
                <th>Rank</th>
                <th>Name</th>
                <th>Tax ID</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="node in lineage" :key="node.tax_id">
                <td>
                  <span class="rank-badge" :class="getRankClass(node.rank)">
                    {{ node.rank }}
                  </span>
                </td>
                <td class="name-cell">{{ node.name }}</td>
                <td>
                  <a
                    href="#"
                    @click.prevent="updateTaxId(node.tax_id)"
                    class="tax-id-link"
                  >
                    {{ node.tax_id }}
                  </a>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Children table -->
      <div v-if="!!children.length" class="taxonomy-section">
        <h2 class="section-title">Children ({{ children.length }})</h2>
        <div class="table-container">
          <table class="table is-fullwidth taxonomy-table">
            <thead>
              <tr>
                <th>Rank</th>
                <th>Name</th>
                <th>Tax ID</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="node in children" :key="node.tax_id">
                <td>
                  <span class="rank-badge" :class="getRankClass(node.rank)">
                    {{ node.rank }}
                  </span>
                </td>
                <td class="name-cell">{{ node.name }}</td>
                <td>
                  <a
                    href="#"
                    @click.prevent="updateTaxId(node.tax_id)"
                    class="tax-id-link"
                  >
                    {{ node.tax_id }}
                  </a>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-if="version">
        <p class="current-taxon-summary">
          Data retrieved from
          <a
            :href="`https://ftp.ncbi.nlm.nih.gov/pub/taxonomy/taxdump_archive/taxdmp_${formatDate(version)}.zip`"
            target="_blank"
            rel="noopener noreferrer"
          >
            NCBI taxdump archive ({{ formatDate(version) }})
          </a>
        </p>
      </div>
    </div>
  </section>

  <!-- TODO make the error look more error-y -->

  <!-- Results -->
</template>

<style scoped>
.header-container {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.responsive-title {
  margin: 0;
  font-size: 2rem;
  line-height: 1.2;
  flex: 1;
  min-width: 0;
}

.documentation-links {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  flex-shrink: 0;
}

/* Mobile responsiveness */
@media screen and (max-width: 768px) {
  .header-container {
    flex-direction: column;
    align-items: stretch;
  }

  .responsive-title {
    font-size: 1.5rem;
    text-align: center;
    margin-bottom: 0.5rem;
  }

  .documentation-links {
    justify-content: center;
    align-self: center;
  }

  .documentation-links .button {
    font-size: 0.75rem;
  }
}

@media screen and (max-width: 480px) {
  .responsive-title {
    font-size: 1.25rem;
  }

  .documentation-links {
    flex-direction: column;
    width: 100%;
  }

  .documentation-links .button {
    width: 100%;
    justify-content: center;
  }
}

/* Taxonomy tables styling */
.taxonomy-section {
  margin-bottom: 2rem;
}

.section-title {
  font-size: 1.5rem;
  font-weight: bold;
  margin-bottom: 1rem;
  color: #363636;
  border-bottom: 2px solid #e0e0e0;
  padding-bottom: 0.5rem;
}

.table-container {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.taxonomy-table {
  margin-bottom: 0;
  border-radius: 0;
}

.taxonomy-table th {
  background-color: #f8f9fa;
  font-weight: bold;
  color: #495057;
  border-bottom: 2px solid #dee2e6;
  padding: 1rem 0.75rem;
}

.taxonomy-table td {
  padding: 0.875rem 0.75rem;
  vertical-align: middle;
  border-bottom: 1px solid #e9ecef;
}

.taxonomy-table tbody tr:hover {
  background-color: #f8f9fa;
}

.name-cell {
  font-weight: 500;
}

.tax-id-link {
  color: #007bff;
  text-decoration: none;
  font-weight: 500;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.tax-id-link:hover {
  background-color: #e7f3ff;
  color: #0056b3;
  text-decoration: none;
}

/* Rank badges */
.rank-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border: 1px solid;
  min-width: 70px;
  text-align: center;
}

.rank-superkingdom {
  background-color: #e3f2fd;
  color: #1565c0;
  border-color: #90caf9;
}

.rank-kingdom {
  background-color: #f3e5f5;
  color: #7b1fa2;
  border-color: #ce93d8;
}

.rank-phylum {
  background-color: #e8f5e8;
  color: #2e7d32;
  border-color: #a5d6a7;
}

.rank-class {
  background-color: #fff3e0;
  color: #ef6c00;
  border-color: #ffcc02;
}

.rank-order {
  background-color: #fce4ec;
  color: #c2185b;
  border-color: #f8bbd9;
}

.rank-family {
  background-color: #f1f8e9;
  color: #558b2f;
  border-color: #c5e1a5;
}

.rank-genus {
  background-color: #e0f2f1;
  color: #00695c;
  border-color: #80cbc4;
}

.rank-species {
  background-color: #e8eaf6;
  color: #3f51b5;
  border-color: #9fa8da;
}

.rank-subspecies {
  background-color: #fafafa;
  color: #424242;
  border-color: #bdbdbd;
}

.rank-strain {
  background-color: #fff8e1;
  color: #ff8f00;
  border-color: #ffcc02;
}

.rank-default {
  background-color: #f5f5f5;
  color: #666;
  border-color: #ccc;
}

/* Dark mode support */
@media (prefers-color-scheme: dark) {
  .section-title {
    color: #f3f3f3;
    border-bottom-color: #444b53;
  }

  .table-container {
    background: #2b3035;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  }

  .taxonomy-table th {
    background-color: #343a40;
    color: #f8f9fa;
    border-bottom-color: #495057;
  }

  .taxonomy-table td {
    background-color: #2b3035;
    color: #f8f9fa;
    border-bottom-color: #495057;
  }

  .taxonomy-table tbody tr:hover {
    background-color: #343a40;
  }

  .tax-id-link {
    color: #66b3ff;
  }

  .tax-id-link:hover {
    background-color: #1a3a52;
    color: #99ccff;
  }

  /* Dark mode rank badges */
  .rank-superkingdom {
    background-color: #2a3f54;
    color: #8bb6e8;
    border-color: #4a5568;
  }

  .rank-kingdom {
    background-color: #3d2a54;
    color: #c8a2db;
    border-color: #4a5568;
  }

  .rank-phylum {
    background-color: #2a4a2a;
    color: #90c695;
    border-color: #4a5568;
  }

  .rank-class {
    background-color: #54422a;
    color: #e8b366;
    border-color: #4a5568;
  }

  .rank-order {
    background-color: #54344a;
    color: #e8a2c8;
    border-color: #4a5568;
  }

  .rank-family {
    background-color: #344a34;
    color: #95c695;
    border-color: #4a5568;
  }

  .rank-genus {
    background-color: #2a4a44;
    color: #80c8bc;
    border-color: #4a5568;
  }

  .rank-species {
    background-color: #344254;
    color: #9cb3e8;
    border-color: #4a5568;
  }

  .rank-subspecies {
    background-color: #3a3a3a;
    color: #b8b8b8;
    border-color: #4a5568;
  }

  .rank-strain {
    background-color: #544a2a;
    color: #e8cc66;
    border-color: #4a5568;
  }

  .rank-default {
    background-color: #3a3a3a;
    color: #a8a8a8;
    border-color: #4a5568;
  }
}

/* Mobile responsiveness */
@media screen and (max-width: 768px) {
  .table-container {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }

  .taxonomy-table {
    font-size: 0.9rem;
    min-width: 480px;
  }

  .taxonomy-table th,
  .taxonomy-table td {
    padding: 0.5rem 0.375rem;
  }

  .taxonomy-table th:nth-child(1),
  .taxonomy-table td:nth-child(1) {
    width: 100px;
    min-width: 100px;
  }

  .taxonomy-table th:nth-child(2),
  .taxonomy-table td:nth-child(2) {
    width: auto;
    min-width: 200px;
  }

  .taxonomy-table th:nth-child(3),
  .taxonomy-table td:nth-child(3) {
    width: 80px;
    min-width: 80px;
  }

  .rank-badge {
    min-width: 60px;
    font-size: 0.7rem;
    padding: 0.2rem 0.5rem;
  }

  .section-title {
    font-size: 1.25rem;
  }
}

@media screen and (max-width: 480px) {
  .table-container {
    margin: 0 -1rem;
    border-radius: 0;
    border-left: none;
    border-right: none;
  }

  .taxonomy-table {
    min-width: 320px;
  }

  .taxonomy-table th:nth-child(1),
  .taxonomy-table td:nth-child(1) {
    width: 80px;
    min-width: 80px;
  }

  .taxonomy-table th:nth-child(2),
  .taxonomy-table td:nth-child(2) {
    width: auto;
    min-width: 150px;
  }

  .taxonomy-table th:nth-child(3),
  .taxonomy-table td:nth-child(3) {
    width: 70px;
    min-width: 70px;
    text-align: right;
  }

  .rank-badge {
    min-width: 50px;
    font-size: 0.65rem;
    padding: 0.15rem 0.4rem;
  }

  .name-cell {
    word-break: break-word;
  }

  .current-taxon-summary {
    word-wrap: break-word;
    overflow-wrap: break-word;
  }
}

/* Additional mobile-specific styles for data source section */
@media screen and (max-width: 768px) {
  .current-taxon-summary {
    font-size: 0.9rem;
    line-height: 1.4;
  }
}
</style>

<script lang="ts">
import { defineComponent, ref, watch, computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiFetchWithCache } from "../utils/apiCache";

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
    <div
      class="header-container"
      style="
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
      "
    >
      <p class="title" style="margin: 0">{{ emoji }} Taxonomy Time Machine</p>
      <div class="documentation-links" style="gap: 0.5rem; display: flex">
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
            'Wuhan seafood market pneumonia virus',
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

      <nav
        class="breadcrumb is-centered has-succeeds-separator"
        aria-label="breadcrumbs"
      >
        <ul>
          <li
            v-for="v in versions"
            :class="{ 'is-active': v.version_date === version }"
          >
            <a href="#" @click.prevent="updateVersion(v.version_date)">
              {{ formatDate(v.version_date) }}
            </a>
          </li>
        </ul>
      </nav>

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
          <code>{{
            `https://ftp.ncbi.nlm.nih.gov/pub/taxonomy/taxdump_archive/taxdmp_${formatDate(version)}.zip`
          }}</code>
          <a
            :href="`https://ftp.ncbi.nlm.nih.gov/pub/taxonomy/taxdump_archive/taxdmp_${formatDate(version)}.zip`"
            target="_blank"
            rel="noopener noreferrer"
            style="margin-left: 0.5em; font-size: 0.95em"
          >
            [download]
          </a>
        </p>
      </div>
    </div>
  </section>

  <!-- TODO make the error look more error-y -->

  <!-- Results -->
</template>

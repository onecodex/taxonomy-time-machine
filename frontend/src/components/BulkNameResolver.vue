<script lang="ts">
import { defineComponent, ref, computed } from "vue";
import { apiFetchWithCache } from "../utils/apiCache";

interface ResolvedName {
  originalName: string;
  resolvedName: string | null;
  taxId: string | null;
  status: "pending" | "resolved" | "not-found" | "error";
  errorMessage?: string;
}

export default defineComponent({
  name: "BulkNameResolver",
  props: {
    apiBase: {
      type: String,
      required: true,
    },
  },
  setup(props) {
    const inputNames = ref("");
    const targetDate = ref("");
    const isProcessing = ref(false);
    const results = ref<ResolvedName[]>([]);
    const processedCount = ref(0);

    // Initialize with current date as default
    const today = new Date();
    targetDate.value = today.toISOString().split("T")[0];

    const formatDate = (isoDate: string): string => {
      const date = new Date(isoDate + "T00:00:00");
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, "0");
      const day = String(date.getDate()).padStart(2, "0");
      return `${year}-${month}-${day}`;
    };

    const formatDisplayDate = (isoDate: string): string => {
      const date = new Date(isoDate + "T00:00:00");
      return date.toLocaleDateString(undefined, {
        year: "numeric",
        month: "long",
        day: "numeric",
      });
    };

    const parseInputNames = (): string[] => {
      return inputNames.value
        .split("\n")
        .map((name) => name.trim())
        .filter((name) => name.length > 0);
    };

    const searchTaxonName = async (name: string): Promise<any[]> => {
      const response = await apiFetchWithCache(
        `${props.apiBase}/search?query=${encodeURIComponent(name)}`,
      );
      return response || [];
    };

    const getLineageAtDate = async (
      taxId: string,
      date: string,
    ): Promise<any[]> => {
      const formattedDate = formatDate(date);
      const response = await apiFetchWithCache(
        `${props.apiBase}/lineage?tax_id=${taxId}&version_date=${formattedDate}T00:00:00`,
      );
      return response || [];
    };

    const resolveNameAtDate = async (
      originalName: string,
    ): Promise<ResolvedName> => {
      try {
        // First, search for the name to get tax_id
        const searchResults = await searchTaxonName(originalName);

        if (!searchResults || searchResults.length === 0) {
          return {
            originalName,
            resolvedName: null,
            taxId: null,
            status: "not-found",
          };
        }

        const taxId = searchResults[0].tax_id;

        // Get the lineage at the target date
        const lineage = await getLineageAtDate(taxId, targetDate.value);

        if (!lineage || lineage.length === 0) {
          return {
            originalName,
            resolvedName: null,
            taxId: taxId,
            status: "not-found",
            errorMessage: "No lineage found at target date",
          };
        }

        // Get the species/lowest level name from the lineage
        const resolvedTaxon = lineage[lineage.length - 1];

        return {
          originalName,
          resolvedName: resolvedTaxon.name,
          taxId: taxId,
          status: "resolved",
        };
      } catch (error) {
        console.error(`Error resolving ${originalName}:`, error);
        return {
          originalName,
          resolvedName: null,
          taxId: null,
          status: "error",
          errorMessage:
            error instanceof Error ? error.message : "Unknown error",
        };
      }
    };

    const processNames = async () => {
      const names = parseInputNames();

      if (names.length === 0) {
        alert("Please enter at least one taxonomic name.");
        return;
      }

      if (!targetDate.value) {
        alert("Please select a target date.");
        return;
      }

      isProcessing.value = true;
      processedCount.value = 0;
      results.value = names.map((name) => ({
        originalName: name,
        resolvedName: null,
        taxId: null,
        status: "pending" as const,
      }));

      // Process names sequentially to avoid overwhelming the API
      for (let i = 0; i < names.length; i++) {
        const result = await resolveNameAtDate(names[i]);
        results.value[i] = result;
        processedCount.value = i + 1;
      }

      isProcessing.value = false;
    };

    const clearResults = () => {
      results.value = [];
      processedCount.value = 0;
    };

    const loadExampleTaxa = async () => {
      // Human-relevant pathogens with verified nomenclature changes - using outdated names
      const exampleTaxa = [
        "Candida pseudohaemulonii", // Now: Candidozyma pseudohaemuli (opportunistic pathogen)
        "Lactobacillus reuteri", // Now: Limosilactobacillus reuteri (probiotic)
        "Mycobacterium koreense", // Now: Mycolicibacillus koreensis (environmental mycobacterium)
        "SARS-related coronavirus", // Now: Severe acute respiratory syndrome-related coronavirus
        "Enterobacteria phage RB32", // Now: Tequatrovirus RB32 (E. coli phage)
        "Candida haemulonis", // Now: Candidozyma haemuli (multidrug-resistant pathogen)
        "Candida duobushaemulonii", // Now: Candidozyma duobushaemuli (emerging pathogen)
        "Escherichia virus RB32", // Now: Tequatrovirus RB32 (bacteriophage)
        "Candida chanthaburiensis", // Multiple nomenclature changes (clinical isolate)
        "Lactobacillus timonenis", // Now: [Lactobacillus] timonensis (gut microbe)
      ];

      inputNames.value = exampleTaxa.join("\n");
      clearResults();

      // Automatically run the query
      await processNames();
    };

    const exportResults = () => {
      if (results.value.length === 0) return;

      const csvContent = [
        "Original Name,Resolved Name,Tax ID,Status,Error Message",
        ...results.value.map((result) =>
          [
            `"${result.originalName}"`,
            `"${result.resolvedName || ""}"`,
            `"${result.taxId || ""}"`,
            `"${result.status}"`,
            `"${result.errorMessage || ""}"`,
          ].join(","),
        ),
      ].join("\n");

      const blob = new Blob([csvContent], { type: "text/csv" });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `taxonomic_names_resolved_${formatDate(targetDate.value)}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    };

    const resolvedCount = computed(
      () => results.value.filter((r) => r.status === "resolved").length,
    );

    const notFoundCount = computed(
      () => results.value.filter((r) => r.status === "not-found").length,
    );

    const errorCount = computed(
      () => results.value.filter((r) => r.status === "error").length,
    );

    const progressPercentage = computed(() => {
      if (results.value.length === 0) return 0;
      return Math.round((processedCount.value / results.value.length) * 100);
    });

    return {
      inputNames,
      targetDate,
      isProcessing,
      results,
      processedCount,
      processNames,
      clearResults,
      loadExampleTaxa,
      exportResults,
      formatDisplayDate,
      resolvedCount,
      notFoundCount,
      errorCount,
      progressPercentage,
    };
  },
});
</script>

<template>
  <div class="container">
    <div class="header-container">
      <h1 class="title responsive-title">🔄 Bulk Name Resolver</h1>
      <div class="documentation-links">
        <router-link to="/" class="button is-small">
          ← Back to Search
        </router-link>
      </div>
    </div>

    <div class="content-section">
      <div class="notification">
        <p class="description">
          Resolve multiple taxonomic names to their current nomenclature at a
          specific date. Enter one name per line and select the target date for
          name resolution.
        </p>
        <div style="margin-top: 1rem">
          <button
            @click="loadExampleTaxa"
            class="button"
            :disabled="isProcessing"
          >
            🧬 Try Example
          </button>
        </div>
      </div>

      <!-- Input Section -->
      <div class="input-section">
        <div class="field">
          <label class="label">Target Date</label>
          <div class="control">
            <input
              v-model="targetDate"
              type="date"
              class="input"
              :disabled="isProcessing"
            />
          </div>
          <p class="help">
            Names will be resolved to their nomenclature as of this date
          </p>
        </div>

        <div class="field">
          <label class="label">Taxonomic Names or Tax IDs (one per line)</label>
          <div class="control">
            <textarea
              v-model="inputNames"
              class="textarea"
              rows="10"
              placeholder="Enter taxonomic names or tax IDs, one per line"
              :disabled="isProcessing"
            ></textarea>
          </div>
        </div>

        <div class="field is-grouped">
          <div class="control">
            <button
              @click="processNames"
              class="button is-primary is-medium"
              :class="{ 'is-loading': isProcessing }"
              :disabled="isProcessing || !inputNames.trim()"
            >
              Resolve Names
            </button>
          </div>
          <div class="control">
            <button
              @click="clearResults"
              class="button is-medium"
              :disabled="isProcessing || results.length === 0"
            >
              Clear Results
            </button>
          </div>
        </div>
      </div>

      <!-- Progress Section -->
      <div v-if="isProcessing || results.length > 0" class="progress-section">
        <div v-if="isProcessing" class="progress-info">
          <p class="processing-status">
            Processing {{ processedCount }} of {{ results.length }} names...
          </p>
          <progress
            class="progress is-primary"
            :value="progressPercentage"
            max="100"
          >
            {{ progressPercentage }}%
          </progress>
        </div>

        <!-- Summary -->
        <div v-if="!isProcessing && results.length > 0" class="summary-stats">
          <div class="stats-grid">
            <div class="stat-item has-text-success">
              <span class="stat-number">{{ resolvedCount }}</span>
              <span class="stat-label">Resolved</span>
            </div>
            <div class="stat-item has-text-warning">
              <span class="stat-number">{{ notFoundCount }}</span>
              <span class="stat-label">Not Found</span>
            </div>
            <div class="stat-item has-text-danger">
              <span class="stat-number">{{ errorCount }}</span>
              <span class="stat-label">Errors</span>
            </div>
            <div class="stat-item">
              <span class="stat-number">{{ results.length }}</span>
              <span class="stat-label">Total</span>
            </div>
          </div>

          <div class="export-section">
            <button
              @click="exportResults"
              class="button is-info"
              :disabled="results.length === 0"
            >
              📥 Export as CSV
            </button>
          </div>
        </div>
      </div>

      <!-- Results Table -->
      <div v-if="results.length > 0" class="results-section">
        <h2 class="section-title">
          Results as of {{ formatDisplayDate(targetDate) }}
        </h2>

        <div class="table-container">
          <table class="table is-fullwidth results-table">
            <thead>
              <tr>
                <th>Original Name</th>
                <th>Resolved Name</th>
                <th>Tax ID</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(result, index) in results"
                :key="index"
                :class="{
                  'has-background-success-light': result.status === 'resolved',
                  'has-background-warning-light': result.status === 'not-found',
                  'has-background-danger-light': result.status === 'error',
                  'has-background-grey-lighter': result.status === 'pending',
                }"
              >
                <td class="original-name">{{ result.originalName }}</td>
                <td class="resolved-name">
                  <span
                    v-if="result.status === 'pending'"
                    class="is-loading-text"
                  >
                    Processing...
                  </span>
                  <span
                    v-else-if="result.resolvedName"
                    class="has-text-weight-semibold"
                  >
                    {{ result.resolvedName }}
                  </span>
                  <span v-else class="has-text-grey">
                    {{ result.errorMessage || "Not found" }}
                  </span>
                </td>
                <td class="tax-id">
                  <span v-if="result.taxId" class="tag is-small">
                    {{ result.taxId }}
                  </span>
                </td>
                <td class="status">
                  <span
                    class="tag is-small"
                    :class="{
                      'is-success': result.status === 'resolved',
                      'is-warning': result.status === 'not-found',
                      'is-danger': result.status === 'error',
                      'is-light': result.status === 'pending',
                    }"
                  >
                    {{ result.status }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.header-container {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 2rem;
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

.content-section {
  max-width: 1200px;
  margin: 0 auto;
}

.description {
  font-size: 1.1rem;
  color: #666;
  margin-bottom: 2rem;
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 6px;
  border-left: 4px solid #007bff;
}

.input-section {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin-bottom: 2rem;
}

.progress-section {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin-bottom: 2rem;
}

.processing-status {
  font-weight: 500;
  margin-bottom: 1rem;
  color: #363636;
}

.summary-stats {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
}

.stats-grid {
  display: flex;
  gap: 2rem;
  flex-wrap: wrap;
}

.stat-item {
  text-align: center;
}

.stat-number {
  display: block;
  font-size: 2rem;
  font-weight: bold;
  line-height: 1;
}

.stat-label {
  display: block;
  font-size: 0.9rem;
  color: #666;
  margin-top: 0.25rem;
}

.export-section {
  flex-shrink: 0;
}

.results-section {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.section-title {
  font-size: 1.5rem;
  font-weight: bold;
  margin: 0;
  padding: 1.5rem;
  background: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
}

.table-container {
  overflow-x: auto;
}

.results-table {
  margin-bottom: 0;
}

.results-table th {
  background-color: #f8f9fa;
  font-weight: bold;
  color: #495057;
  border-bottom: 2px solid #dee2e6;
  padding: 1rem 0.75rem;
  white-space: nowrap;
}

.results-table td {
  padding: 0.875rem 0.75rem;
  vertical-align: middle;
  border-bottom: 1px solid #e9ecef;
}

.original-name {
  font-family: monospace;
  font-weight: 500;
}

.resolved-name {
  font-style: italic;
}

.is-loading-text {
  color: #666;
  font-style: normal;
}

.tax-id {
  font-family: monospace;
}

/* Dark mode support */
@media (prefers-color-scheme: dark) {
  .description {
    background: #2b3035;
    color: #f3f3f3;
    border-left-color: #66b3ff;
  }

  .input-section,
  .progress-section,
  .results-section {
    background: #2b3035;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  }

  .section-title {
    background: #343a40;
    color: #f8f9fa;
    border-bottom-color: #495057;
  }

  .results-table th {
    background-color: #343a40;
    color: #f8f9fa;
    border-bottom-color: #495057;
  }

  .results-table td {
    background-color: #2b3035;
    color: #f8f9fa;
    border-bottom-color: #495057;
  }

  .processing-status {
    color: #f3f3f3;
  }
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

  .input-section,
  .progress-section {
    padding: 1rem;
  }

  .stats-grid {
    justify-content: center;
    gap: 1rem;
  }

  .summary-stats {
    flex-direction: column;
    text-align: center;
  }

  .results-table th,
  .results-table td {
    padding: 0.5rem 0.375rem;
    font-size: 0.9rem;
  }
}

@media screen and (max-width: 480px) {
  .responsive-title {
    font-size: 1.25rem;
  }

  .stats-grid {
    gap: 0.5rem;
  }

  .stat-number {
    font-size: 1.5rem;
  }
}
</style>

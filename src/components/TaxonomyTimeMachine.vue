<script lang="ts">
import { defineComponent, ref, watch } from 'vue';

import { formatDate } from '@/utils.ts';

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

    const emoji = ref<string>('🌳');

    // a common place to store errors
    const error = ref<string | null>(null);
    let timeout: ReturnType<typeof setTimeout> | null = null;

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

    // Debounced input handler
    const onInput = () => {
      if (timeout) clearTimeout(timeout);
      timeout = setTimeout(() => {
        setTaxId();
      }, 300);
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
        <div class="control is-expanded">
          <input
            class="input has-text-success is-primary is-large"
            type="text"
            v-model="query"
            placeholder="Seach for a name or tax ID"
            @input="onInput"
          />
        </div>
      </div>
    </div>
  </section>

  <!-- TODO make the error look more error-y -->
  <div v-if="error" class="error">{{ error }}</div>

  <section class="section">
    <div class="container">
      <nav class="breadcrumb" aria-label="breadcrumbs">
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
    </div>
  </section>

  <!-- Results -->

  <section class="section">
    <div class="container">
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
            <h2>Children</h2>
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

  <section class="section">
    <div class="container">
      <div class="columns">

      </div>
    </div>

  </section>

</template>

<style scoped>
.read-the-docs {
  color: #888;
}
</style>

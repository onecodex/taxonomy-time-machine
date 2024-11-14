<script lang="ts">
import { defineComponent, ref, watch } from 'vue';

export default defineComponent({
  name: 'SearchComponent',
  setup() {

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
      if (isNumeric(query.value)) {
        taxId.value = query.value
      } else {
        findTaxId();
      }
    };

    const findTaxId = async() => {
      if (query.value == null || !query.value.toString().trim()) {
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

      const response = await fetch(`http://localhost:5000/children?tax_id=${encodeURIComponent(taxId.value)}&version=${encodeURIComponent(version.value)}`);

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

      if (lineage.value.some(item => item.name === "Fungi")) {
          emoji.value = "🍄";
      } else if (lineage.value.some(item => item.name === "Bacteria")) {
          emoji.value = "🦠";
      } else if (lineage.value.some(item => item.name === "Viruses")) {
          emoji.value = "😷";
      } else if (lineage.value.some(item => item.name === "Homo sapiens")) {
          emoji.value = "🧑‍🔬";
      } else if (lineage.value.some(item => item.name === "Canis lupus")) {
          emoji.value = "🐕";
      } else {
          emoji.value = "🌳";
      }

      lineage.value = data || [];
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
    };
  },
});
</script>

<template>
  <section>
    <h2>Debug</h2>
    <code>taxId={{ taxId }}</code>
    <code>version={{ version }}</code>
  </section>



  <div class="container">

    <h1 class="title has-text-primary">{{ emoji }} Taxonomy Time Machine</h1>

    <div class="field">
      <label class="label">Search for a name or tax ID</label>
      <div class="control">
        <input
          class="input has-text-success is-primary is-large"
          type="text"
          v-model="query"
          placeholder="Type to search... (example: 498019)"
          @input="onInput"
        />
      </div>
    </div>

    <div v-if="error" class="error">{{ error }}</div>

    <div class="columns">

      <div class="column is-one-fifth">
        <h2>Versions</h2>
        <ol class="ul">
          <li v-for="version in versions">
            <a href="#" @click.prevent="updateVersion(version.version_date)">{{ version.version_date }}</a>
          </li>
        </ol>
      </div>

      <!-- lineage table -->
      <div class="column auto">
        <div v-if="lineage">
          <h2>Lineage</h2>
          <table class="table">
            <thead>
              <tr>
                <th>tax_id</th>
                <th>name</th>
                <th>rank</th>
              </tr>
            </thead>
            <tr v-for="node in lineage">
              <td>{{ node.tax_id }}</td>
              <td>{{ node.name }}</td>
              <td>{{ node.rank }}</td>
            </tr>
          </table>
        </div>
      </div>

      <!-- children table -->
      <div class="column auto">
        <div v-if="children">
          <h2>Children</h2>
          <table class="table">
            <thead>
              <tr>
                <th>tax_id</th>
                <th>name</th>
                <th>rank</th>
              </tr>
            </thead>
            <tr v-for="node in children">
              <td>{{ node.tax_id }}</td>
              <td>{{ node.name }}</td>
              <td>{{ node.rank }}</td>
            </tr>
          </table>
        </div>
      </div>

    </div>

  </div>


  <hr/>


</template>

<style scoped>
.read-the-docs {
  color: #888;
}
</style>

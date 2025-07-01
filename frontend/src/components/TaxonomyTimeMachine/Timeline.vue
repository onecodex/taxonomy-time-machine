<script setup lang="ts">
import { computed } from 'vue';

interface VersionData {
  version_date: string | null;
}

interface Props {
  versions: VersionData[];
  currentVersion: string | null;
}

interface Emits {
  (e: 'update-version', version: string | null): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const formatDateShort = (isoDate: string | null): string => {
  if (!isoDate) return '';
  const date = new Date(isoDate);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  return `${year}-${month}`;
};

const formatDateLong = (isoDate: string | null): string => {
  if (!isoDate) return '';
  const date = new Date(isoDate);
  return date.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
};

const sortedVersions = computed(() => {
  return [...props.versions].sort((a, b) => {
    const dateA = new Date(a.version_date || '');
    const dateB = new Date(b.version_date || '');
    return dateA.getTime() - dateB.getTime();
  });
});

const timelineData = computed(() => {
  if (sortedVersions.value.length === 0) return [];

  const firstDate = new Date(sortedVersions.value[0].version_date || '');
  const lastDate = new Date(sortedVersions.value[sortedVersions.value.length - 1].version_date || '');
  const totalDuration = lastDate.getTime() - firstDate.getTime();

  // Calculate initial positions
  const initialData = sortedVersions.value.map((version, index) => {
    const versionDate = new Date(version.version_date || '');
    const position = totalDuration === 0 ? 0 : ((versionDate.getTime() - firstDate.getTime()) / totalDuration) * 100;

    return {
      ...version,
      position,
      labelPosition: position, // Start with same position as dot
      isActive: version.version_date === props.currentVersion,
      isFirst: index === 0,
      isLast: index === sortedVersions.value.length - 1,
    };
  });

  // Apply label repulsion algorithm
  const minLabelDistance = 8; // Minimum distance between labels in percentage
  const repulsionStrength = 0.3; // How strongly labels repel each other
  const maxIterations = 50;

  for (let iteration = 0; iteration < maxIterations; iteration++) {
    let hasOverlap = false;

    for (let i = 0; i < initialData.length; i++) {
      for (let j = i + 1; j < initialData.length; j++) {
        const item1 = initialData[i];
        const item2 = initialData[j];
        const distance = Math.abs(item1.labelPosition - item2.labelPosition);

        if (distance < minLabelDistance) {
          hasOverlap = true;
          const overlap = minLabelDistance - distance;
          const repulsion = overlap * repulsionStrength;

          // Move labels away from each other
          if (item1.labelPosition < item2.labelPosition) {
            item1.labelPosition = Math.max(0, item1.labelPosition - repulsion / 2);
            item2.labelPosition = Math.min(100, item2.labelPosition + repulsion / 2);
          } else {
            item1.labelPosition = Math.min(100, item1.labelPosition + repulsion / 2);
            item2.labelPosition = Math.max(0, item2.labelPosition - repulsion / 2);
          }
        }
      }
    }

    // If no overlaps, we're done
    if (!hasOverlap) break;
  }

  return initialData;
});

const handleVersionClick = (version: VersionData) => {
  emit('update-version', version.version_date);
};

const currentVersionIndex = computed(() => {
  return sortedVersions.value.findIndex(
    (version) => version.version_date === props.currentVersion
  );
});

const canGoToPrevious = computed(() => {
  return currentVersionIndex.value > 0;
});

const canGoToNext = computed(() => {
  return currentVersionIndex.value < sortedVersions.value.length - 1;
});

const goToPrevious = () => {
  if (canGoToPrevious.value) {
    const previousVersion = sortedVersions.value[currentVersionIndex.value - 1];
    emit('update-version', previousVersion.version_date);
  }
};

const goToNext = () => {
  if (canGoToNext.value) {
    const nextVersion = sortedVersions.value[currentVersionIndex.value + 1];
    emit('update-version', nextVersion.version_date);
  }
};
</script>

<template>
  <div v-if="versions.length > 0" class="timeline-container">
    <div class="timeline-header">
      <button
        class="timeline-nav-button"
        :disabled="!canGoToPrevious"
        @click="goToPrevious"
      >
        &larr; Prev
      </button>
      <h3 class="timeline-title">Version Timeline</h3>
      <button
        class="timeline-nav-button"
        :disabled="!canGoToNext"
        @click="goToNext"
      >
        Next &rarr;
      </button>
    </div>
    <div class="timeline-wrapper">
      <div class="timeline-line"></div>
      <div
        v-for="(version, index) in timelineData"
        :key="index"
        class="timeline-dot-container"
        :style="{ left: `${version.position}%` }"
        @click="handleVersionClick(version)"
      >
        <div
          class="timeline-dot"
          :class="{
            'is-active': version.isActive,
            'is-first': version.isFirst,
            'is-last': version.isLast
          }"
          :title="formatDateLong(version.version_date)"
        ></div>

        <div
          class="timeline-label"
          :class="{ 'is-active': version.isActive }"
          :style="{ left: `${(version.labelPosition - version.position)}%` }"
        >
          {{ formatDateShort(version.version_date) }}
        </div>
      </div>
    </div>
    <div class="timeline-legend">
      <span class="timeline-legend-start">{{ formatDateShort(sortedVersions[0]?.version_date) }}</span>
      <span class="timeline-legend-end">{{ formatDateShort(sortedVersions[sortedVersions.length - 1]?.version_date) }}</span>
    </div>
  </div>
</template>

<style scoped>
.timeline-container {
  margin: 2rem 0;
  padding: 1.5rem;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.timeline-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.timeline-title {
  font-size: 1.25rem;
  font-weight: bold;
  color: #363636;
  margin: 0;
  text-align: center;
  flex-grow: 1;
}

.timeline-nav-button {
  background: #f5f5f5;
  border: 1px solid #dbdbdb;
  border-radius: 4px;
  padding: 0.5rem 1rem;
  font-size: 0.9rem;
  font-weight: bold;
  color: #363636;
  cursor: pointer;
  transition: all 0.2s ease;
}

.timeline-nav-button:hover:not(:disabled) {
  background: #e8e8e8;
  border-color: #b5b5b5;
}

.timeline-nav-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.timeline-wrapper {
  position: relative;
  height: 90px;
  margin: 0 20px;
}

.timeline-line {
  position: absolute;
  top: 25px;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(to right, #dbdbdb, #3273dc, #dbdbdb);
  border-radius: 1px;
}

.timeline-dot-container {
  position: absolute;
  top: 0;
  transform: translateX(-50%);
  cursor: pointer;
  transition: all 0.2s ease;
}

.timeline-dot-container:hover {
  transform: translateX(-50%) scale(1.1);
}

.timeline-dot {
  width: 12px;
  height: 12px;
  background: #dbdbdb;
  border: 2px solid #fff;
  border-radius: 50%;
  position: relative;
  top: 19px;
  transition: all 0.2s ease;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.timeline-dot.is-active {
  background: #3273dc;
  width: 16px;
  height: 16px;
  top: 17px;
  box-shadow: 0 0 0 3px rgba(50, 115, 220, 0.3);
}

.timeline-dot.is-first {
  background: #23d160;
}

.timeline-dot.is-last {
  background: #ff3860;
}

.timeline-dot.is-first.is-active {
  background: #20bc56;
  box-shadow: 0 0 0 3px rgba(35, 209, 96, 0.3);
}

.timeline-dot.is-last.is-active {
  background: #ff1f4e;
  box-shadow: 0 0 0 3px rgba(255, 56, 96, 0.3);
}

.timeline-dot:hover {
  transform: scale(1.2);
}

.timeline-label {
  position: absolute;
  top: 45px;
  left: 50%;
  transform: translateX(-50%) rotate(-45deg);
  transform-origin: center bottom;
  font-size: 0.75rem;
  color: #666;
  white-space: nowrap;
  transition: all 0.2s ease;
  opacity: 0.7;
}

.timeline-label.is-active {
  font-weight: bold;
  color: #3273dc;
  opacity: 1;
}

.timeline-connector {
  position: absolute;
  top: 31px;
  height: 1px;
  background: #ccc;
  transform-origin: left center;
  transition: all 0.2s ease;
  z-index: 1;
}

.timeline-dot-container:hover .timeline-connector {
  background: #3273dc;
  height: 2px;
  top: 30.5px;
}

.timeline-legend {
  display: flex;
  justify-content: space-between;
  font-size: 0.8rem;
  color: #888;
  margin-top: 1rem;
  padding: 0 20px;
}

.timeline-legend-start,
.timeline-legend-end {
  font-weight: 500;
}

/* Dark mode support */
@media (prefers-color-scheme: dark) {
  .timeline-container {
    background: #2b3035;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  }

  .timeline-title {
    color: #f3f3f3;
  }

  .timeline-nav-button {
    background: #3a4147;
    border-color: #4a5568;
    color: #f3f3f3;
  }

  .timeline-nav-button:hover:not(:disabled) {
    background: #4a5568;
    border-color: #66b3ff;
  }

  .timeline-line {
    background: linear-gradient(to right, #4a5568, #66b3ff, #4a5568);
  }

  .timeline-dot {
    background: #4a5568;
    border-color: #2b3035;
  }

  .timeline-dot.is-active {
    background: #66b3ff;
    box-shadow: 0 0 0 3px rgba(102, 179, 255, 0.3);
  }

  .timeline-dot.is-first {
    background: #48c774;
  }

  .timeline-dot.is-last {
    background: #ff6b8a;
  }

  .timeline-dot.is-first.is-active {
    background: #3ec46d;
    box-shadow: 0 0 0 3px rgba(72, 199, 116, 0.3);
  }

  .timeline-dot.is-last.is-active {
    background: #ff5577;
    box-shadow: 0 0 0 3px rgba(255, 107, 138, 0.3);
  }

  .timeline-label {
    color: #a8a8a8;
  }

  .timeline-label.is-active {
    color: #66b3ff;
  }

  .timeline-legend {
    color: #a8a8a8;
  }

  .timeline-connector {
    background: #4a5568;
  }

  .timeline-dot-container:hover .timeline-connector {
    background: #66b3ff;
  }
}

/* Mobile responsiveness */
@media screen and (max-width: 768px) {
  .timeline-container {
    margin: 1rem 0;
    padding: 1rem;
  }

  .timeline-wrapper {
    height: 80px;
    margin: 0 10px;
  }

  .timeline-dot {
    width: 10px;
    height: 10px;
    top: 20px;
  }

  .timeline-dot.is-active {
    width: 14px;
    height: 14px;
    top: 18px;
  }

  .timeline-label {
    top: 40px;
    font-size: 0.7rem;
    transform: translateX(-50%) rotate(-45deg);
  }

  .timeline-legend {
    padding: 0 10px;
    font-size: 0.75rem;
  }

  .timeline-connector {
    top: 26px;
  }

  .timeline-dot-container:hover .timeline-connector {
    top: 25.5px;
  }

  .timeline-header {
    flex-wrap: wrap;
    justify-content: center;
  }

  .timeline-title {
    order: -1;
    width: 100%;
    margin-bottom: 1rem;
  }

  .timeline-nav-button {
    padding: 0.4rem 0.8rem;
    font-size: 0.8rem;
  }
}

@media screen and (max-width: 480px) {
  .timeline-container {
    padding: 0.75rem;
    margin: 0.75rem 0;
  }

  .timeline-title {
    font-size: 1.1rem;
    margin-bottom: 1rem;
  }

  .timeline-wrapper {
    height: 70px;
    margin: 0 5px;
  }

  .timeline-dot {
    width: 8px;
    height: 8px;
    top: 21px;
  }

  .timeline-dot.is-active {
    width: 12px;
    height: 12px;
    top: 19px;
  }

  .timeline-label {
    top: 35px;
    font-size: 0.65rem;
    transform: translateX(-50%) rotate(-45deg);
  }

  .timeline-legend {
    padding: 0 5px;
    font-size: 0.7rem;
  }

  .timeline-connector {
    top: 27px;
  }

  .timeline-dot-container:hover .timeline-connector {
    top: 26.5px;
  }

  .timeline-nav-button {
    padding: 0.3rem 0.6rem;
    font-size: 0.7rem;
  }
}
</style>

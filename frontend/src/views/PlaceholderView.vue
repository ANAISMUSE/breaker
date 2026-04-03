<script setup lang="ts">
defineProps<{
  title: string
}>()
</script>

<template>
  <div class="page">
    <div class="card">
      <h1 class="title">{{ title }}</h1>
      <p class="desc">功能将从原 Streamlit 迁移至 Web 前端。</p>
    </div>
  </div>
</template>

<style scoped>
.page {
  min-height: 100%;
}

.card {
  background: #fff;
  border-radius: 12px;
  padding: 28px 32px;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
}

.title {
  margin: 0 0 12px;
  font-size: 1.35rem;
  color: #0f172a;
}

.desc {
  margin: 0;
  color: #64748b;
  line-height: 1.6;
}
</style>

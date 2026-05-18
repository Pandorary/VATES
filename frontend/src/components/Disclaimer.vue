<template>
  <div class="overlay">
    <div class="modal">
      <h2>风险提示</h2>
      <p>本系统仅展示市场状态与历史概率数据，所有内容<strong>仅供参考，不构成任何投资建议</strong>。股市有风险，投资需谨慎。过去的表现不预示未来结果。</p>
      <button @click="$emit('agree')">我已知晓并同意</button>
    </div>
  </div>
</template>

<script setup lang="ts">
defineEmits<{ agree: [] }>()
</script>

<style scoped>
.overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.6); display: flex; align-items: center; justify-content: center; z-index: 9999; }
.modal { background: #fff; border-radius: 12px; padding: 32px; max-width: 420px; text-align: center; }
.modal h2 { margin-bottom: 16px; font-size: 18px; }
.modal p { color: #666; line-height: 1.8; margin-bottom: 24px; font-size: 14px; }
.modal button { padding: 10px 40px; background: #1677ff; color: #fff; border: none; border-radius: 6px; font-size: 15px; cursor: pointer; transition: background .2s; }
.modal button:hover { background: #4096ff; }
</style>

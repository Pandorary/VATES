<template>
  <div class="layout">
    <header class="header">
      <div class="brand">
          <span class="logo">VATES</span>
          <span class="tagline">see the future</span>
        </div>
      <nav class="nav">
        <span class="nav-item">首页</span>
        <span class="nav-item">大盘</span>
        <span class="nav-item">自选</span>
        <span class="nav-item">复盘</span>
      </nav>
    </header>
    <main class="main"><slot /></main>
    <footer class="footer">交易状态感知与风控辅助系统—仅供参考，不构成投资建议</footer>
    <Disclaimer v-if="!store.disclaimerAgreed" @agree="store.agreeDisclaimer()" />
  </div>
</template>

<script setup lang="ts">
import { useAppStore } from '../stores/app'
import Disclaimer from './Disclaimer.vue'

const store = useAppStore()
</script>

<style scoped>
.layout { min-height: 100vh; display: flex; flex-direction: column; background: #FFFFFF; }
.header { display: flex; justify-content: flex-start; align-items: center; padding: 0 24px; height: 60px; gap: 40px; background: #f5f5f5; }
.brand { display: flex; flex-direction: column; align-items: flex-start; line-height: 1.2; }
.logo { font-weight: 700; font-size: 16px; color: #1a1a1a; letter-spacing: 2px; text-transform: uppercase; }
.tagline { font-size: 8px; font-weight: 400; color: #999; }
.nav { display: flex; gap: 32px; }
.nav-item { font-size: 14px; color: #1a1a1a; cursor: pointer; }
.main { flex: 1; display: flex; align-items: center; justify-content: center; }
.footer { text-align: center; padding: 12px 24px; color: #999; font-size: 12px; }
</style>

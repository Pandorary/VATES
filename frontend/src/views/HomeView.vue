<template>
  <AppLayout>
    <div class="home">
      <div class="brand">
        <h1 class="brand-logo">VATES</h1>
      </div>

      <div class="search-box">
        <svg class="search-icon" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="#999" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/></svg>
        <input v-model="query" @keyup.enter="analyze" placeholder="搜索股票代码或名称..." class="search-input" />
      </div>

      <div class="result" v-if="loading">AI 正在分析...</div>
      <div class="result" v-else-if="error">{{ error }}</div>
      <div class="result-card" v-else-if="result">
        <div class="stock-header">
          <h2>{{ result.stock?.name }}</h2>
          <span class="code">{{ result.stock?.code }}</span>
          <span class="summary">{{ result.stock?.summary }}</span>
        </div>

        <div class="section" v-if="result.market_context">
          <h3>市场环境</h3>
          <p><strong>{{ result.market_context.status }}</strong> — {{ result.market_context.impact }}</p>
        </div>

        <div class="section" v-if="result.analysis">
          <h3>分析</h3>
          <div class="grid-2">
            <div v-if="result.analysis.technical"><h4>技术面</h4><p>{{ result.analysis.technical }}</p></div>
            <div v-if="result.analysis.fund_flow"><h4>资金面</h4><p>{{ result.analysis.fund_flow }}</p></div>
            <div v-if="result.analysis.fundamental"><h4>基本面</h4><p>{{ result.analysis.fundamental }}</p></div>
            <div v-if="result.analysis.catalyst"><h4>催化剂</h4><p>{{ result.analysis.catalyst }}</p></div>
          </div>
        </div>

        <div class="section risk" v-if="result.risk_assessment">
          <h3>风险评估 — {{ result.risk_assessment.level }}</h3>
          <ul>
            <li v-for="r in result.risk_assessment.reasons" :key="r">{{ r }}</li>
          </ul>
          <div class="levels" v-if="result.risk_assessment.support_level">
            支撑：{{ result.risk_assessment.support_level }} | 压力：{{ result.risk_assessment.resistance_level }}
          </div>
        </div>

        <div class="section conclusion" v-if="result.conclusion">
          <h3>综合结论</h3>
          <p>{{ result.conclusion }}</p>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { sendChat } from '../services/api'
import AppLayout from '../components/AppLayout.vue'

const query = ref('')
const loading = ref(false)
const error = ref('')
const result = ref<any>(null)

async function analyze() {
  if (!query.value.trim()) return
  loading.value = true
  error.value = ''
  result.value = null
  try {
    const res = await sendChat(query.value.trim())
    const data = res.data.data
    const content = data?.content || ''
    try {
      const jsonStr = content.replace(/```json\s*/g, '').replace(/```\s*/g, '').trim()
      result.value = JSON.parse(jsonStr)
    } catch {
      result.value = { raw: content }
    }
  } catch (e: any) {
    error.value = '请求失败，请确认后端服务已启动'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.home { display: flex; flex-direction: column; align-items: center; gap: 15px; padding: 40px 0 25vh; }

.brand-logo { font-size: 40px; font-weight: 400; color: #1a1a1a; letter-spacing: 8px; text-transform: uppercase; margin: 0; text-align: center; }

.search-box { display: flex; align-items: center; width: 420px; height: 44px; border: 1px solid #ddd; border-radius: 22px; background: #FFFFFF; padding: 0 16px; gap: 10px; }
.search-icon { flex-shrink: 0; }
.search-input { flex: 1; border: none; outline: none; font-size: 15px; color: #333; background: transparent; }
.search-input::placeholder { color: #ccc; }

.result { color: #999; font-size: 14px; padding: 24px; }

.result-card { width: 100%; max-width: 800px; display: flex; flex-direction: column; gap: 16px; }
.stock-header { background: #fff; border-radius: 8px; padding: 20px; border: 1px solid #e8e8e8; }
.stock-header h2 { font-size: 24px; margin-bottom: 4px; }
.code { color: #999; font-size: 13px; margin-right: 12px; }
.summary { color: #666; font-size: 14px; }

.section { background: #fff; border-radius: 8px; padding: 16px; border: 1px solid #e8e8e8; }
.section h3 { font-size: 15px; margin-bottom: 8px; }
.section h4 { font-size: 13px; color: #999; margin-bottom: 2px; }
.section p { font-size: 14px; line-height: 1.7; }

.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.grid-2 > div { padding: 8px 0; }

.risk { border-color: #fecaca; background: #fef2f2; }
.risk h3 { color: #dc2626; }
.risk li { font-size: 13px; margin: 4px 0 4px 16px; }
.levels { font-size: 12px; color: #999; margin-top: 8px; }

.conclusion { border-color: #1677ff; background: #f0f5ff; }
</style>

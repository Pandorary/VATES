import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  const disclaimerAgreed = ref(localStorage.getItem('vates_disclaimer') === 'true')

  function agreeDisclaimer() {
    disclaimerAgreed.value = true
    localStorage.setItem('vates_disclaimer', 'true')
  }

  return { disclaimerAgreed, agreeDisclaimer }
})

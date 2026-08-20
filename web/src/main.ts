import { createApp } from 'vue'
import { createPinia } from 'pinia'
import Vant from 'vant'
import 'vant/lib/index.css'
import App from './App.vue'
import router from './router'

const params = new URLSearchParams(window.location.search)
const injected = params.get('token')
if (injected) {
  localStorage.setItem('lx_token', injected)
  if (params.get('refresh')) {
    localStorage.setItem('lx_refresh_token', params.get('refresh')!)
  }
  params.delete('token')
  params.delete('refresh')
  const qs = params.toString()
  window.history.replaceState({}, '', window.location.pathname + (qs ? `?${qs}` : ''))
}

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(Vant)

app.mount('#app')

import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import App from './App.vue'
import router from './router'
import { getStoredTheme } from './utils/theme'
import './styles.css'

document.documentElement.dataset.theme = getStoredTheme()

createApp(App).use(router).use(ElementPlus).mount('#app')

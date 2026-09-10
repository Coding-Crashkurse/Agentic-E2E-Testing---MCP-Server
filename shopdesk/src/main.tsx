import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@fontsource-variable/inter'
import './index.css'
import { App } from './App'
import { readRuntimeOptions } from './config/runtime'

// `import.meta.env.VITE_BUG` wird vom Launcher per `define` fest ersetzt – bewusst als vollständiger
// Ausdruck geschrieben, damit Vite ihn statisch austauschen kann.
const options = readRuntimeOptions(window.location.search, { VITE_BUG: import.meta.env.VITE_BUG })

// Animationen global abschalten (?motion=off), damit Screenshots pixelstabil bleiben.
if (!options.motion) {
  document.documentElement.dataset.motion = 'off'
}

const container = document.getElementById('root')
if (!container) {
  throw new Error('Root-Element #root wurde nicht gefunden.')
}

createRoot(container).render(
  <StrictMode>
    <App options={options} />
  </StrictMode>,
)

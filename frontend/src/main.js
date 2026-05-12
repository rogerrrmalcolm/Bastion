import './style.css'
import * as THREE from 'three'

const app = document.querySelector('#app')

app.innerHTML = `
  <main class="experience-shell is-traveling">
    <div id="scene-root" class="scene-root" aria-hidden="true"></div>
    <div class="flight-readout" aria-hidden="true">
      <span>M&A Signal Transit</span>
      <div class="readout-track"><i id="readout-progress"></i></div>
    </div>
    <section class="workflow-dock" aria-label="Bastion workflow input">
      <div class="dock-header">
        <p class="eyebrow">Bastion M&A Workflow</p>
        <h1>Diligence terminal</h1>
      </div>
      <form id="workflow-form" class="workflow-form">
        <label class="upload-target" for="pdf-upload">
          <span class="upload-icon">+</span>
          <span>
            <strong>Attach PDFs</strong>
            <small id="file-summary">No files selected</small>
          </span>
        </label>
        <input id="pdf-upload" type="file" accept="application/pdf" multiple />
        <label class="prompt-field">
          <span>Deal prompt</span>
          <textarea
            id="deal-prompt"
            minlength="20"
            placeholder="Paste company context, acquisition thesis, or diligence questions."
            required
          ></textarea>
        </label>
        <div class="workflow-actions">
          <button type="submit">Run workflow</button>
          <p id="workflow-status" role="status">Ready</p>
        </div>
      </form>
      <output id="workflow-result" class="workflow-result" aria-live="polite"></output>
    </section>
  </main>
`

const sceneRoot = document.querySelector('#scene-root')
const shell = document.querySelector('.experience-shell')
const readoutProgress = document.querySelector('#readout-progress')
const form = document.querySelector('#workflow-form')
const fileInput = document.querySelector('#pdf-upload')
const fileSummary = document.querySelector('#file-summary')
const promptInput = document.querySelector('#deal-prompt')
const workflowStatus = document.querySelector('#workflow-status')
const workflowResult = document.querySelector('#workflow-result')

const scene = new THREE.Scene()
scene.fog = new THREE.FogExp2(0x02030a, 0.018)

const camera = new THREE.PerspectiveCamera(58, 1, 0.1, 220)
camera.position.set(0, 0, 9)

const renderer = new THREE.WebGLRenderer({
  antialias: true,
  alpha: false,
  powerPreference: 'high-performance',
})
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
renderer.setClearColor(0x02030a, 1)
sceneRoot.appendChild(renderer.domElement)

const clock = new THREE.Clock()
const pointer = new THREE.Vector2()
const tunnelLength = 170
const nearLimit = 12
const farLimit = -tunnelLength
const introDuration = 2.85
let hasArrived = false

const palette = {
  blue: new THREE.Color(0x7dd3fc),
  violet: new THREE.Color(0xa78bfa),
  amber: new THREE.Color(0xfbbf24),
  red: new THREE.Color(0xfb7185),
  white: new THREE.Color(0xf8fafc),
}

function randomBetween(min, max) {
  return min + Math.random() * (max - min)
}

function smoothstep(edge0, edge1, value) {
  const x = Math.min(1, Math.max(0, (value - edge0) / (edge1 - edge0)))
  return x * x * (3 - 2 * x)
}

function starPosition(z = randomBetween(farLimit, nearLimit)) {
  const angle = Math.random() * Math.PI * 2
  const radius = randomBetween(3.3, 9.5)
  const wobble = Math.sin(z * 0.1 + angle * 2) * 0.55
  return {
    x: Math.cos(angle) * (radius + wobble),
    y: Math.sin(angle) * (radius + wobble),
    z,
  }
}

function makeStarField() {
  const count = 3600
  const positions = new Float32Array(count * 3)
  const colors = new Float32Array(count * 3)
  const colorChoices = [palette.blue, palette.violet, palette.amber, palette.red, palette.white]

  for (let i = 0; i < count; i += 1) {
    const point = starPosition()
    positions[i * 3] = point.x
    positions[i * 3 + 1] = point.y
    positions[i * 3 + 2] = point.z

    const color = colorChoices[Math.floor(Math.random() * colorChoices.length)]
    colors[i * 3] = color.r
    colors[i * 3 + 1] = color.g
    colors[i * 3 + 2] = color.b
  }

  const geometry = new THREE.BufferGeometry()
  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
  geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3))

  const material = new THREE.PointsMaterial({
    size: 0.045,
    vertexColors: true,
    transparent: true,
    opacity: 0.95,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  })

  return new THREE.Points(geometry, material)
}

function makeTunnelRings() {
  const group = new THREE.Group()
  const ringCount = 72
  const segmentCount = 128

  for (let i = 0; i < ringCount; i += 1) {
    const points = []
    const z = -i * (tunnelLength / ringCount)
    const radius = 3.2 + Math.sin(i * 0.42) * 0.42

    for (let j = 0; j <= segmentCount; j += 1) {
      const angle = (j / segmentCount) * Math.PI * 2
      const ripple = Math.sin(angle * 5 + i * 0.35) * 0.13
      points.push(new THREE.Vector3(
        Math.cos(angle) * (radius + ripple),
        Math.sin(angle) * (radius + ripple),
        z,
      ))
    }

    const geometry = new THREE.BufferGeometry().setFromPoints(points)
    const hueColor = i % 4 === 0 ? 0x7dd3fc : i % 4 === 1 ? 0xa78bfa : i % 4 === 2 ? 0xfbbf24 : 0xfb7185
    const material = new THREE.LineBasicMaterial({
      color: hueColor,
      transparent: true,
      opacity: 0.16,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    })
    const ring = new THREE.LineLoop(geometry, material)
    ring.userData.baseZ = z
    ring.userData.speed = randomBetween(9, 13)
    group.add(ring)
  }

  return group
}

function makeSymbolTexture(label, color = '#fbbf24') {
  const canvas = document.createElement('canvas')
  canvas.width = 256
  canvas.height = 128
  const context = canvas.getContext('2d')

  context.clearRect(0, 0, canvas.width, canvas.height)
  context.shadowColor = color
  context.shadowBlur = 22
  context.fillStyle = 'rgba(2, 6, 23, 0.58)'
  context.strokeStyle = color
  context.lineWidth = 3
  context.beginPath()
  context.roundRect(18, 18, 220, 92, 18)
  context.fill()
  context.stroke()
  context.font = label.length > 3 ? '700 44px Arial' : '800 56px Arial'
  context.textAlign = 'center'
  context.textBaseline = 'middle'
  context.fillStyle = '#f8fafc'
  context.fillText(label, 128, 66)

  const texture = new THREE.CanvasTexture(canvas)
  texture.colorSpace = THREE.SRGBColorSpace
  return texture
}

function symbolPosition(z = randomBetween(-128, -26)) {
  const angle = Math.random() * Math.PI * 2
  const radius = randomBetween(1.65, 4.25)
  return {
    x: Math.cos(angle) * radius,
    y: Math.sin(angle) * radius,
    z,
  }
}

function makeFinanceSymbols() {
  const group = new THREE.Group()
  const labels = ['$', 'M&A', 'DCF', 'IRR', 'IPO', 'NWC', 'EV', 'EBITDA', 'WACC', 'LOI', 'ROI']
  const colors = ['#fbbf24', '#7dd3fc', '#a78bfa', '#fb7185']

  for (let i = 0; i < 62; i += 1) {
    const label = labels[i % labels.length]
    const material = new THREE.SpriteMaterial({
      map: makeSymbolTexture(label, colors[i % colors.length]),
      transparent: true,
      opacity: 0.92,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    })
    const sprite = new THREE.Sprite(material)
    const position = symbolPosition(randomBetween(-104, -8))
    sprite.position.set(position.x, position.y, position.z)
    sprite.scale.setScalar(randomBetween(0.82, 1.45))
    sprite.userData.speed = randomBetween(20, 32)
    sprite.userData.spin = randomBetween(-0.9, 0.9)
    sprite.userData.baseScale = sprite.scale.x
    group.add(sprite)
  }

  return group
}

function makeArrivalGate() {
  const group = new THREE.Group()

  const torus = new THREE.Mesh(
    new THREE.TorusGeometry(2.25, 0.035, 16, 180),
    new THREE.MeshBasicMaterial({
      color: 0x7dd3fc,
      transparent: true,
      opacity: 0.85,
      blending: THREE.AdditiveBlending,
    }),
  )
  const inner = new THREE.Mesh(
    new THREE.TorusGeometry(1.66, 0.018, 12, 180),
    new THREE.MeshBasicMaterial({
      color: 0xfbbf24,
      transparent: true,
      opacity: 0.7,
      blending: THREE.AdditiveBlending,
    }),
  )
  const halo = new THREE.Mesh(
    new THREE.CircleGeometry(1.82, 96),
    new THREE.MeshBasicMaterial({
      color: 0x172554,
      transparent: true,
      opacity: 0.28,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    }),
  )

  group.add(halo, torus, inner)
  group.position.z = -58
  return group
}

const stars = makeStarField()
const rings = makeTunnelRings()
const arrivalGate = makeArrivalGate()
const financeSymbols = makeFinanceSymbols()
scene.add(stars, rings, arrivalGate, financeSymbols)

const ambient = new THREE.AmbientLight(0x93c5fd, 0.45)
scene.add(ambient)

function markArrived() {
  if (hasArrived) {
    return
  }
  hasArrived = true
  shell.classList.remove('is-traveling')
  shell.classList.add('is-arrived')
}

function resizeRenderer() {
  const width = sceneRoot.clientWidth
  const height = sceneRoot.clientHeight
  camera.aspect = width / height
  camera.fov = width < 720 ? 66 : 58
  camera.updateProjectionMatrix()
  renderer.setSize(width, height, false)
}

function recycleStar(index, positions) {
  const point = starPosition(farLimit)
  positions[index] = point.x
  positions[index + 1] = point.y
  positions[index + 2] = point.z
}

function animate() {
  const delta = Math.min(clock.getDelta(), 0.033)
  const elapsed = clock.elapsedTime
  const introProgress = smoothstep(0, introDuration, elapsed)
  const positions = stars.geometry.attributes.position.array
  const speed = 30 + (1 - introProgress) * 34

  for (let i = 0; i < positions.length; i += 3) {
    positions[i + 2] += speed * delta * (1 + Math.abs(positions[i]) * 0.025)
    const twist = delta * 0.1
    const x = positions[i]
    const y = positions[i + 1]
    positions[i] = x * Math.cos(twist) - y * Math.sin(twist)
    positions[i + 1] = x * Math.sin(twist) + y * Math.cos(twist)

    if (positions[i + 2] > nearLimit) {
      recycleStar(i, positions)
    }
  }
  stars.geometry.attributes.position.needsUpdate = true

  rings.children.forEach((ring, index) => {
    ring.position.z += ring.userData.speed * delta * (1 + (1 - introProgress) * 1.65)
    ring.rotation.z += delta * (index % 2 === 0 ? 0.2 : -0.12)
    ring.material.opacity = 0.08 + Math.max(0, 1 - Math.abs(ring.position.z) / 80) * 0.2

    if (ring.position.z > nearLimit) {
      ring.position.z = farLimit
    }
  })

  const symbolFade = 1 - smoothstep(2.35, introDuration + 0.35, elapsed)
  financeSymbols.children.forEach((sprite) => {
    sprite.position.z += sprite.userData.speed * delta
    sprite.material.rotation += sprite.userData.spin * delta
    sprite.material.opacity = 0.92 * symbolFade
    sprite.scale.setScalar(sprite.userData.baseScale * (1 + Math.max(0, sprite.position.z) * 0.035))

    if (sprite.position.z > nearLimit + 2) {
      const position = symbolPosition(randomBetween(-128, -64))
      sprite.position.set(position.x, position.y, position.z)
      sprite.userData.speed = randomBetween(24, 40)
      sprite.userData.baseScale = randomBetween(0.42, 0.82)
    }
  })

  arrivalGate.rotation.z = elapsed * 0.18
  arrivalGate.position.z = -76 + introProgress * 48 + Math.sin(elapsed * 0.7) * 1.4
  arrivalGate.scale.setScalar(0.72 + introProgress * 0.46 + Math.sin(elapsed * 1.3) * 0.035)

  if (readoutProgress) {
    readoutProgress.style.transform = `scaleX(${Math.min(1, elapsed / introDuration)})`
  }

  if (!hasArrived && elapsed >= introDuration) {
    markArrived()
  }

  const tunnelDrift = Math.sin(elapsed * 2.2) * (1 - introProgress) * 0.28
  const targetX = pointer.x * (hasArrived ? 0.7 : 0.32) + tunnelDrift
  const targetY = pointer.y * (hasArrived ? 0.42 : 0.24) + Math.cos(elapsed * 2.7) * (1 - introProgress) * 0.18
  const targetZ = 18 - introProgress * 9
  camera.position.x += (targetX - camera.position.x) * 0.045
  camera.position.y += (targetY - camera.position.y) * 0.045
  camera.position.z += (targetZ - camera.position.z) * 0.04
  camera.lookAt(pointer.x * 0.42, pointer.y * 0.25, -36 + introProgress * 7)

  renderer.render(scene, camera)
  requestAnimationFrame(animate)
}

window.addEventListener('resize', resizeRenderer)
window.addEventListener('pointermove', (event) => {
  pointer.x = (event.clientX / window.innerWidth - 0.5) * 2
  pointer.y = -(event.clientY / window.innerHeight - 0.5) * 2
})

fileInput.addEventListener('change', () => {
  const files = Array.from(fileInput.files ?? [])
  if (files.length === 0) {
    fileSummary.textContent = 'No files selected'
    return
  }
  const totalSize = files.reduce((sum, file) => sum + file.size, 0)
  const sizeMb = totalSize / 1024 / 1024
  fileSummary.textContent = `${files.length} PDF${files.length === 1 ? '' : 's'} selected, ${sizeMb.toFixed(1)} MB`
})

form.addEventListener('submit', async (event) => {
  event.preventDefault()

  const files = Array.from(fileInput.files ?? [])
  const fileContext = files.length
    ? `\n\nAttached PDF filenames for reference:\n${files.map((file) => `- ${file.name}`).join('\n')}`
    : ''
  const companyText = `${promptInput.value.trim()}${fileContext}`

  workflowStatus.textContent = 'Running'
  workflowResult.textContent = ''
  form.classList.add('is-running')

  try {
    const response = await fetch('http://localhost:8000/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: window.crypto?.randomUUID?.() ?? `session-${Date.now()}`,
        company_text: companyText,
      }),
    })

    if (!response.ok) {
      throw new Error(`Workflow returned ${response.status}`)
    }

    const data = await response.json()
    workflowStatus.textContent = 'Complete'
    workflowResult.innerHTML = `
      <strong>${data.investment_memo?.recommendation ?? 'Analysis complete'}</strong>
      <span>${data.investment_memo?.executive_summary ?? 'The workflow returned a response.'}</span>
    `
  } catch (error) {
    workflowStatus.textContent = 'Backend unavailable'
    workflowResult.textContent = 'Start the FastAPI backend on port 8000, then run the workflow again.'
    console.error(error)
  } finally {
    form.classList.remove('is-running')
  }
})

resizeRenderer()
animate()
window.setTimeout(markArrived, introDuration * 1000)

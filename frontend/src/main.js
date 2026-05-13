import './style.css'
import * as THREE from 'three'

const app = document.querySelector('#app')

app.innerHTML = `
  <main class="experience-shell is-traveling">
    <div id="scene-root" class="scene-root" aria-hidden="true"></div>
    <div class="flight-readout" aria-hidden="true">
      <span>Buyer Target Transit</span>
      <div class="readout-track"><i id="readout-progress"></i></div>
    </div>
    <section class="workflow-dock" aria-label="Bastion workflow input">
      <div class="dock-header">
        <p class="eyebrow">Bastion M&A Workflow</p>
        <h1>Diligence terminal</h1>
      </div>
      <form id="workflow-form" class="workflow-form">
        <div class="deal-fields">
          <div class="company-panel">
            <label class="upload-target company-upload" for="buyer-pdf-upload">
              <span class="upload-icon">+</span>
              <span>
                <strong>Buyer PDFs</strong>
                <small id="buyer-file-summary">No buyer PDFs selected</small>
              </span>
            </label>
            <input id="buyer-pdf-upload" class="pdf-input" type="file" accept="application/pdf" multiple />
            <label class="prompt-field company-field">
              <span>Buyer / acquirer</span>
              <textarea
                id="buyer-context"
                minlength="10"
                placeholder="Paste buyer strategy, business profile, financing capacity, rationale, and constraints."
                required
              ></textarea>
            </label>
          </div>
          <div class="company-panel">
            <label class="upload-target company-upload" for="target-pdf-upload">
              <span class="upload-icon">+</span>
              <span>
                <strong>Target PDFs</strong>
                <small id="target-file-summary">No target PDFs selected</small>
              </span>
            </label>
            <input id="target-pdf-upload" class="pdf-input" type="file" accept="application/pdf" multiple />
            <label class="prompt-field company-field">
              <span>Target company</span>
              <textarea
                id="target-context"
                minlength="10"
                placeholder="Paste target financials, product, market position, risks, customer details, or ticker."
                required
              ></textarea>
            </label>
          </div>
          <label class="prompt-field deal-question-field">
            <span>Deal thesis / questions</span>
            <textarea
              id="deal-prompt"
              placeholder="Ask what to compare, such as strategic fit, valuation support, risk, synergies, or whether to proceed."
            ></textarea>
          </label>
        </div>
        <div class="workflow-actions">
          <button type="submit">Compare deal</button>
          <p id="workflow-status" role="status">Ready</p>
        </div>
      </form>
      <output id="workflow-result" class="workflow-result" aria-live="polite"></output>
    </section>
    <section id="workflow-loader" class="workflow-loader" aria-live="polite" aria-hidden="true">
      <div class="loader-panel">
        <div class="loader-header">
          <p class="eyebrow">Agent Routing</p>
          <h2>Dijkstra workflow traversal</h2>
          <p id="loader-caption">Calculating shortest path through Bastion agents.</p>
        </div>
        <div id="workflow-map" class="workflow-map" aria-hidden="true"></div>
        <div class="loader-status-grid">
          <div>
            <span>Current destination</span>
            <strong id="current-agent">Buyer intake</strong>
          </div>
          <div>
            <span>Route cost</span>
            <strong id="route-cost">0</strong>
          </div>
          <div>
            <span>Response mode</span>
            <strong id="response-mode">Analysis</strong>
          </div>
        </div>
      </div>
    </section>
  </main>
`

const sceneRoot = document.querySelector('#scene-root')
const shell = document.querySelector('.experience-shell')
const readoutProgress = document.querySelector('#readout-progress')
const workflowDock = document.querySelector('.workflow-dock')
const form = document.querySelector('#workflow-form')
const buyerFileInput = document.querySelector('#buyer-pdf-upload')
const buyerFileSummary = document.querySelector('#buyer-file-summary')
const targetFileInput = document.querySelector('#target-pdf-upload')
const targetFileSummary = document.querySelector('#target-file-summary')
const buyerInput = document.querySelector('#buyer-context')
const targetInput = document.querySelector('#target-context')
const promptInput = document.querySelector('#deal-prompt')
const workflowStatus = document.querySelector('#workflow-status')
const workflowResult = document.querySelector('#workflow-result')
const workflowLoader = document.querySelector('#workflow-loader')
const workflowMap = document.querySelector('#workflow-map')
const loaderCaption = document.querySelector('#loader-caption')
const currentAgent = document.querySelector('#current-agent')
const routeCost = document.querySelector('#route-cost')
const responseMode = document.querySelector('#response-mode')

const scene = new THREE.Scene()
scene.fog = new THREE.FogExp2(0xf4efe6, 0.015)

const camera = new THREE.PerspectiveCamera(58, 1, 0.1, 220)
camera.position.set(0, 0, 9)

const renderer = new THREE.WebGLRenderer({
  antialias: true,
  alpha: false,
  powerPreference: 'high-performance',
})
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
renderer.setClearColor(0xf4efe6, 1)
sceneRoot.appendChild(renderer.domElement)

const clock = new THREE.Clock()
const pointer = new THREE.Vector2()
const tunnelLength = 170
const nearLimit = 12
const farLimit = -tunnelLength
const introDuration = 2.85
const WORKFLOW_TIMEOUT_MS = 420000
let hasArrived = false
let dealFocus = 'neutral'

const palette = {
  espresso: new THREE.Color(0x2b1a12),
  brown: new THREE.Color(0x5b3a29),
  copper: new THREE.Color(0x9b6a35),
  sand: new THREE.Color(0xd7c4aa),
  ivory: new THREE.Color(0xf4efe6),
  white: new THREE.Color(0xffffff),
}

const agentGraph = {
  nodes: [
    { id: 'buyer', label: 'Buyer', role: 'acquirer profile', x: 10, y: 44 },
    { id: 'target', label: 'Target', role: 'company profile', x: 25, y: 62 },
    { id: 'orchestrator', label: 'Orchestrator', role: 'route planner', x: 32, y: 28 },
    { id: 'market', label: 'Market Agent', role: 'sector signals', x: 48, y: 16 },
    { id: 'financial', label: 'Financial Agent', role: 'QoE and valuation', x: 61, y: 47 },
    { id: 'risk', label: 'Risk Agent', role: 'risk matrix', x: 74, y: 25 },
    { id: 'memo', label: 'Memo Agent', role: 'IC synthesis', x: 80, y: 58 },
    { id: 'output', label: 'Answer', role: 'buyer-target memo', x: 86, y: 82 },
    { id: 'documents', label: 'Documents', role: 'PDF context', x: 39, y: 82 },
    { id: 'market-data', label: 'Market Data', role: 'live signals', x: 66, y: 79 },
  ],
  edges: [
    ['buyer', 'target', 1],
    ['buyer', 'orchestrator', 6],
    ['target', 'orchestrator', 1],
    ['target', 'documents', 6],
    ['orchestrator', 'market', 1],
    ['orchestrator', 'financial', 7],
    ['orchestrator', 'memo', 14],
    ['market', 'financial', 2],
    ['market', 'risk', 8],
    ['financial', 'risk', 2],
    ['financial', 'market-data', 6],
    ['market-data', 'risk', 6],
    ['documents', 'financial', 8],
    ['documents', 'risk', 9],
    ['risk', 'memo', 1],
    ['memo', 'output', 1],
  ],
}

const agentPathState = {
  route: [],
  distances: {},
  visitOrder: [],
  startedAt: 0,
  frame: null,
  isRunning: false,
  isAwaitingResponse: false,
}

function randomBetween(min, max) {
  return min + Math.random() * (max - min)
}

function smoothstep(edge0, edge1, value) {
  const x = Math.min(1, Math.max(0, (value - edge0) / (edge1 - edge0)))
  return x * x * (3 - 2 * x)
}

function tunnelPathOffset(z, elapsed = 0) {
  const t = z * 0.042 + elapsed * 0.72
  return {
    x: Math.sin(t) * 1.45 + Math.sin(t * 0.47 + 1.2) * 0.82,
    y: Math.cos(t * 0.84 + 0.35) * 0.88 + Math.sin(t * 1.34 - 0.7) * 0.42,
  }
}

function edgeId(from, to) {
  return [from, to].sort().join('__')
}

function computeDijkstraRoute(graph, startId, endId) {
  const nodeIds = graph.nodes.map((node) => node.id)
  const distances = Object.fromEntries(nodeIds.map((id) => [id, Number.POSITIVE_INFINITY]))
  const previous = {}
  const visited = []
  const unsettled = new Set(nodeIds)
  const adjacency = Object.fromEntries(nodeIds.map((id) => [id, []]))

  graph.edges.forEach(([from, to, weight]) => {
    adjacency[from].push({ id: to, weight })
    adjacency[to].push({ id: from, weight })
  })

  distances[startId] = 0

  while (unsettled.size > 0) {
    const current = [...unsettled].sort((a, b) => distances[a] - distances[b])[0]
    if (!current || distances[current] === Number.POSITIVE_INFINITY) {
      break
    }

    unsettled.delete(current)
    visited.push(current)

    if (current === endId) {
      break
    }

    adjacency[current].forEach((neighbor) => {
      if (!unsettled.has(neighbor.id)) {
        return
      }

      const nextDistance = distances[current] + neighbor.weight
      if (nextDistance < distances[neighbor.id]) {
        distances[neighbor.id] = nextDistance
        previous[neighbor.id] = current
      }
    })
  }

  const route = []
  let cursor = endId
  while (cursor) {
    route.unshift(cursor)
    cursor = previous[cursor]
  }

  return {
    distances,
    route: route[0] === startId ? route : [startId],
    visitOrder: visited,
  }
}

function renderWorkflowMap() {
  const dijkstra = computeDijkstraRoute(agentGraph, 'buyer', 'output')
  agentPathState.route = dijkstra.route
  agentPathState.distances = dijkstra.distances
  agentPathState.visitOrder = dijkstra.visitOrder

  const lines = agentGraph.edges.map(([from, to, weight]) => {
    const fromNode = agentGraph.nodes.find((node) => node.id === from)
    const toNode = agentGraph.nodes.find((node) => node.id === to)
    return `
      <g class="map-edge" data-edge="${edgeId(from, to)}">
        <line x1="${fromNode.x}" y1="${fromNode.y}" x2="${toNode.x}" y2="${toNode.y}" />
        <text x="${(fromNode.x + toNode.x) / 2}" y="${(fromNode.y + toNode.y) / 2}">${weight}</text>
      </g>
    `
  }).join('')

  const nodes = agentGraph.nodes.map((node) => `
    <div class="map-node" data-node="${node.id}" style="left: ${node.x}%; top: ${node.y}%;">
      <strong>${node.label}</strong>
      <span>${node.role}</span>
      <small data-distance="${node.id}">cost inf</small>
    </div>
  `).join('')

  workflowMap.innerHTML = `
    <svg class="map-edges" viewBox="0 0 100 100" preserveAspectRatio="none">
      ${lines}
    </svg>
    ${nodes}
  `
}

function setLoaderStep(stepIndex, isComplete = false) {
  const route = agentPathState.route
  const boundedIndex = Math.min(stepIndex, route.length - 1)
  const activeId = route[boundedIndex]
  const activeNode = agentGraph.nodes.find((node) => node.id === activeId)
  const reached = new Set(route.slice(0, boundedIndex + 1))

  workflowMap.querySelectorAll('.map-node').forEach((nodeElement) => {
    const nodeId = nodeElement.dataset.node
    nodeElement.classList.toggle('is-reached', reached.has(nodeId))
    nodeElement.classList.toggle('is-active', nodeId === activeId && !isComplete)
    nodeElement.classList.toggle('is-complete', nodeId === 'output' && isComplete)
  })

  workflowMap.querySelectorAll('[data-distance]').forEach((distanceElement) => {
    const nodeId = distanceElement.dataset.distance
    const distance = agentPathState.distances[nodeId]
    distanceElement.textContent = Number.isFinite(distance) && reached.has(nodeId)
      ? `cost ${distance}`
      : 'cost inf'
  })

  workflowMap.querySelectorAll('.map-edge').forEach((edgeElement) => {
    const isRouteEdge = route.some((nodeId, index) => {
      if (index === 0 || index > boundedIndex) {
        return false
      }
      return edgeId(route[index - 1], nodeId) === edgeElement.dataset.edge
    })
    const isActiveEdge = boundedIndex > 0
      && edgeId(route[boundedIndex - 1], route[boundedIndex]) === edgeElement.dataset.edge
    edgeElement.classList.toggle('is-route', isRouteEdge)
    edgeElement.classList.toggle('is-active', isActiveEdge && !isComplete)
  })

  currentAgent.textContent = activeNode?.label ?? 'Routing'
  routeCost.textContent = Number.isFinite(agentPathState.distances[activeId])
    ? String(agentPathState.distances[activeId])
    : 'inf'
}

function startWorkflowLoader(mode) {
  if (workflowMap.childElementCount === 0) {
    renderWorkflowMap()
  }

  agentPathState.startedAt = performance.now()
  agentPathState.isRunning = true
  agentPathState.isAwaitingResponse = false
  responseMode.textContent = mode
  loaderCaption.textContent = 'Comparing buyer and target through the shortest diligence route.'
  workflowLoader.setAttribute('aria-hidden', 'false')
  shell.classList.add('is-processing')
  shell.classList.add('is-comparing')

  const tick = (timestamp) => {
    if (!agentPathState.isRunning) {
      return
    }

    const elapsed = timestamp - agentPathState.startedAt
    const stepDuration = 2600
    const finalIndex = agentPathState.route.length - 1
    const lastWorkingIndex = Math.max(0, finalIndex - 1)
    const routeIndex = Math.min(
      Math.floor(elapsed / stepDuration),
      lastWorkingIndex,
    )

    setLoaderStep(routeIndex)
    if (routeIndex === lastWorkingIndex && !agentPathState.isAwaitingResponse) {
      agentPathState.isAwaitingResponse = true
      workflowStatus.textContent = 'Finalizing'
      loaderCaption.textContent = 'Comparison route complete. Waiting for Bastion to produce the answer.'
    }

    agentPathState.frame = requestAnimationFrame(tick)
  }

  setLoaderStep(0)
  agentPathState.frame = requestAnimationFrame(tick)
}

function stopWorkflowLoader() {
  agentPathState.isRunning = false
  agentPathState.isAwaitingResponse = false
  shell.classList.remove('is-comparing')
  if (agentPathState.frame) {
    cancelAnimationFrame(agentPathState.frame)
  }
}

function completeWorkflowLoader() {
  stopWorkflowLoader()
  loaderCaption.textContent = 'Shortest route complete. Rendering response.'
  setLoaderStep(agentPathState.route.length - 1, true)

  window.setTimeout(() => {
    shell.classList.remove('is-processing')
    workflowLoader.setAttribute('aria-hidden', 'true')
  }, 780)
}

function failWorkflowLoader(message = 'Workflow route interrupted. Check backend availability.') {
  stopWorkflowLoader()
  loaderCaption.textContent = message
  workflowMap.querySelectorAll('.map-node.is-active').forEach((nodeElement) => {
    nodeElement.classList.add('is-error')
  })

  window.setTimeout(() => {
    shell.classList.remove('is-processing')
    workflowLoader.setAttribute('aria-hidden', 'true')
  }, 1300)
}

function starPosition(z = randomBetween(farLimit, nearLimit)) {
  const angle = Math.random() * Math.PI * 2
  const radius = randomBetween(3.3, 9.5)
  const wobble = Math.sin(z * 0.1 + angle * 2) * 0.55
  const path = tunnelPathOffset(z)
  return {
    x: path.x + Math.cos(angle) * (radius + wobble),
    y: path.y + Math.sin(angle) * (radius + wobble),
    z,
  }
}

function makeStarField() {
  const count = 3600
  const positions = new Float32Array(count * 3)
  const colors = new Float32Array(count * 3)
  const colorChoices = [palette.espresso, palette.brown, palette.copper, palette.sand, palette.white]

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
    size: 0.05,
    vertexColors: true,
    transparent: true,
    opacity: 0.72,
    depthWrite: false,
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
    const hueColor = i % 4 === 0 ? 0x5b3a29 : i % 4 === 1 ? 0x9b6a35 : i % 4 === 2 ? 0x2b1a12 : 0xd7c4aa
    const material = new THREE.LineBasicMaterial({
      color: hueColor,
      transparent: true,
      opacity: 0.28,
      depthWrite: false,
    })
    const ring = new THREE.LineLoop(geometry, material)
    ring.userData.baseZ = z
    ring.userData.speed = randomBetween(9, 13)
    ring.userData.pathPhase = randomBetween(-0.4, 0.4)
    group.add(ring)
  }

  return group
}

function makeSymbolTexture(label, color = '#5b3a29') {
  const canvas = document.createElement('canvas')
  canvas.width = 256
  canvas.height = 128
  const context = canvas.getContext('2d')

  context.clearRect(0, 0, canvas.width, canvas.height)
  context.shadowColor = 'rgba(91, 58, 41, 0.45)'
  context.shadowBlur = 18
  context.fillStyle = 'rgba(255, 255, 255, 0.86)'
  context.strokeStyle = color
  context.lineWidth = 3
  context.beginPath()
  context.roundRect(18, 18, 220, 92, 18)
  context.fill()
  context.stroke()
  context.font = label.length > 3 ? '700 44px Arial' : '800 56px Arial'
  context.textAlign = 'center'
  context.textBaseline = 'middle'
  context.fillStyle = '#2b1a12'
  context.fillText(label, 128, 66)

  const texture = new THREE.CanvasTexture(canvas)
  texture.colorSpace = THREE.SRGBColorSpace
  return texture
}

function symbolPosition(z = randomBetween(-128, -26)) {
  const angle = Math.random() * Math.PI * 2
  const radius = randomBetween(1.65, 4.25)
  const path = tunnelPathOffset(z)
  return {
    x: path.x + Math.cos(angle) * radius,
    y: path.y + Math.sin(angle) * radius,
    z,
    angle,
    radius,
  }
}

function makeFinanceSymbols() {
  const group = new THREE.Group()
  const labels = ['$', 'M&A', 'DCF', 'IRR', 'IPO', 'NWC', 'EV', 'EBITDA', 'WACC', 'LOI', 'ROI']
  const colors = ['#5b3a29', '#9b6a35', '#2b1a12', '#d7c4aa']

  for (let i = 0; i < 62; i += 1) {
    const label = labels[i % labels.length]
    const material = new THREE.SpriteMaterial({
      map: makeSymbolTexture(label, colors[i % colors.length]),
      transparent: true,
      opacity: 0.86,
      depthWrite: false,
    })
    const sprite = new THREE.Sprite(material)
    const position = symbolPosition(randomBetween(-104, -8))
    sprite.position.set(position.x, position.y, position.z)
    sprite.scale.setScalar(randomBetween(0.82, 1.45))
    sprite.userData.speed = randomBetween(20, 32)
    sprite.userData.spin = randomBetween(-0.9, 0.9)
    sprite.userData.baseScale = sprite.scale.x
    sprite.userData.angle = position.angle
    sprite.userData.radius = position.radius
    sprite.userData.orbitSpeed = randomBetween(0.25, 0.7)
    group.add(sprite)
  }

  return group
}

function makeArrivalGate() {
  const group = new THREE.Group()

  const torus = new THREE.Mesh(
    new THREE.TorusGeometry(2.25, 0.035, 16, 180),
    new THREE.MeshBasicMaterial({
      color: 0x5b3a29,
      transparent: true,
      opacity: 0.85,
    }),
  )
  const inner = new THREE.Mesh(
    new THREE.TorusGeometry(1.66, 0.018, 12, 180),
    new THREE.MeshBasicMaterial({
      color: 0x9b6a35,
      transparent: true,
      opacity: 0.7,
    }),
  )
  const halo = new THREE.Mesh(
    new THREE.CircleGeometry(1.82, 96),
    new THREE.MeshBasicMaterial({
      color: 0xf4efe6,
      transparent: true,
      opacity: 0.42,
      depthWrite: false,
    }),
  )

  group.add(halo, torus, inner)
  group.position.z = -58
  return group
}

function makeBeaconLabelTexture(label) {
  const canvas = document.createElement('canvas')
  canvas.width = 512
  canvas.height = 160
  const context = canvas.getContext('2d')

  context.clearRect(0, 0, canvas.width, canvas.height)
  context.fillStyle = 'rgba(255, 255, 255, 0.9)'
  context.strokeStyle = 'rgba(91, 58, 41, 0.75)'
  context.lineWidth = 4
  context.beginPath()
  context.roundRect(28, 34, 456, 92, 24)
  context.fill()
  context.stroke()
  context.font = '800 52px Arial'
  context.textAlign = 'center'
  context.textBaseline = 'middle'
  context.fillStyle = '#2b1a12'
  context.fillText(label, 256, 82)

  const texture = new THREE.CanvasTexture(canvas)
  texture.colorSpace = THREE.SRGBColorSpace
  return texture
}

function makeDealBeacon(label, x, color) {
  const group = new THREE.Group()
  const ringMaterial = new THREE.MeshBasicMaterial({
    color,
    transparent: true,
    opacity: 0.72,
    depthWrite: false,
  })
  const coreMaterial = new THREE.MeshBasicMaterial({
    color: 0xffffff,
    transparent: true,
    opacity: 0.46,
    depthWrite: false,
  })
  const ring = new THREE.Mesh(new THREE.TorusGeometry(0.82, 0.035, 14, 96), ringMaterial)
  const inner = new THREE.Mesh(new THREE.CircleGeometry(0.54, 64), coreMaterial)
  const labelSprite = new THREE.Sprite(new THREE.SpriteMaterial({
    map: makeBeaconLabelTexture(label),
    transparent: true,
    opacity: 0.84,
    depthWrite: false,
  }))

  labelSprite.position.set(0, -1.08, 0.05)
  labelSprite.scale.set(1.95, 0.62, 1)
  group.position.set(x, 0, 0)
  group.add(inner, ring, labelSprite)
  group.userData = { ring, inner, label: labelSprite }
  return group
}

function makeDealComparisonBeacons() {
  const group = new THREE.Group()
  const buyer = makeDealBeacon('BUYER', -2.8, 0x5b3a29)
  const target = makeDealBeacon('TARGET', 2.8, 0x9b6a35)
  const bridgeGeometry = new THREE.BufferGeometry().setFromPoints([
    new THREE.Vector3(-1.92, 0, -0.03),
    new THREE.Vector3(1.92, 0, -0.03),
  ])
  const bridge = new THREE.Line(
    bridgeGeometry,
    new THREE.LineBasicMaterial({
      color: 0xd7c4aa,
      transparent: true,
      opacity: 0.38,
      depthWrite: false,
    }),
  )

  group.add(bridge, buyer, target)
  group.position.set(0, 0.6, -24)
  group.userData = { buyer, target, bridge }
  return group
}

const stars = makeStarField()
const rings = makeTunnelRings()
const arrivalGate = makeArrivalGate()
const financeSymbols = makeFinanceSymbols()
const dealBeacons = makeDealComparisonBeacons()
scene.add(stars, rings, arrivalGate, financeSymbols, dealBeacons)

const ambient = new THREE.AmbientLight(0xffffff, 0.56)
scene.add(ambient)

function markArrived() {
  if (hasArrived) {
    return
  }
  hasArrived = true
  shell.classList.remove('is-traveling')
  shell.classList.add('is-arrived')
}

function setDealFocus(focus) {
  dealFocus = focus
  shell.classList.toggle('is-buyer-focus', focus === 'buyer')
  shell.classList.toggle('is-target-focus', focus === 'target')
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
    const priorPath = tunnelPathOffset(positions[i + 2], elapsed - delta)
    positions[i + 2] += speed * delta * (1 + Math.abs(positions[i]) * 0.025)
    const nextPath = tunnelPathOffset(positions[i + 2], elapsed)
    positions[i] += (nextPath.x - priorPath.x) * 0.34
    positions[i + 1] += (nextPath.y - priorPath.y) * 0.34
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
    const ringPath = tunnelPathOffset(ring.position.z + ring.userData.pathPhase, elapsed)
    const pathIntensity = hasArrived ? 0.46 : 1
    ring.position.x = ringPath.x * pathIntensity
    ring.position.y = ringPath.y * pathIntensity
    ring.rotation.z += delta * (index % 2 === 0 ? 0.2 : -0.12)
    ring.rotation.x = Math.sin(elapsed * 0.45 + index * 0.12) * 0.09 * pathIntensity
    ring.rotation.y = Math.cos(elapsed * 0.36 + index * 0.1) * 0.08 * pathIntensity
    ring.material.opacity = 0.09 + Math.max(0, 1 - Math.abs(ring.position.z) / 80) * 0.22

    if (ring.position.z > nearLimit) {
      ring.position.z = farLimit
    }
  })

  const symbolFade = 1 - smoothstep(2.35, introDuration + 0.35, elapsed)
  financeSymbols.children.forEach((sprite) => {
    sprite.position.z += sprite.userData.speed * delta
    const path = tunnelPathOffset(sprite.position.z, elapsed)
    const orbit = sprite.userData.angle + elapsed * sprite.userData.orbitSpeed + sprite.position.z * 0.045
    sprite.position.x = path.x + Math.cos(orbit) * sprite.userData.radius
    sprite.position.y = path.y + Math.sin(orbit * 0.94) * sprite.userData.radius * 0.78
    sprite.material.rotation += sprite.userData.spin * delta
    sprite.material.opacity = 0.92 * symbolFade
    sprite.scale.setScalar(sprite.userData.baseScale * (1 + Math.max(0, sprite.position.z) * 0.035))

    if (sprite.position.z > nearLimit + 2) {
      const position = symbolPosition(randomBetween(-128, -64))
      sprite.position.set(position.x, position.y, position.z)
      sprite.userData.speed = randomBetween(24, 40)
      sprite.userData.baseScale = randomBetween(0.42, 0.82)
      sprite.userData.angle = position.angle
      sprite.userData.radius = position.radius
      sprite.userData.orbitSpeed = randomBetween(0.25, 0.7)
    }
  })

  const gatePath = tunnelPathOffset(arrivalGate.position.z, elapsed)
  arrivalGate.rotation.z = elapsed * 0.18
  arrivalGate.position.z = -76 + introProgress * 48 + Math.sin(elapsed * 0.7) * 1.4
  arrivalGate.position.x = gatePath.x * 0.58
  arrivalGate.position.y = gatePath.y * 0.58
  arrivalGate.scale.setScalar(0.72 + introProgress * 0.46 + Math.sin(elapsed * 1.3) * 0.035)

  const compareBias = agentPathState.isRunning
    ? Math.sin(elapsed * 1.15)
    : dealFocus === 'buyer'
      ? -1
      : dealFocus === 'target'
        ? 1
        : 0
  const beaconOpacity = hasArrived ? (agentPathState.isRunning ? 0.95 : 0.48) : introProgress * 0.2
  const buyerEmphasis = compareBias < -0.16 ? 1 : 0.62
  const targetEmphasis = compareBias > 0.16 ? 1 : 0.62
  const beaconPath = tunnelPathOffset(-24, elapsed)
  dealBeacons.position.x = beaconPath.x * 0.22
  dealBeacons.position.y = 0.72 + beaconPath.y * 0.15 + Math.sin(elapsed * 0.9) * 0.08
  dealBeacons.position.z = -23 + Math.sin(elapsed * 0.52) * 0.6
  dealBeacons.rotation.z = Math.sin(elapsed * 0.28) * 0.08
  dealBeacons.userData.bridge.material.opacity = beaconOpacity * (0.45 + Math.abs(compareBias) * 0.36)
  ;[
    [dealBeacons.userData.buyer, buyerEmphasis],
    [dealBeacons.userData.target, targetEmphasis],
  ].forEach(([beacon, emphasis]) => {
    beacon.scale.setScalar(0.9 + emphasis * 0.18 + Math.sin(elapsed * 2.1) * 0.025)
    beacon.userData.ring.rotation.z += delta * (0.58 + emphasis * 0.32)
    beacon.userData.ring.material.opacity = beaconOpacity * emphasis
    beacon.userData.inner.material.opacity = beaconOpacity * 0.45 * emphasis
    beacon.userData.label.material.opacity = beaconOpacity * (0.66 + emphasis * 0.22)
  })

  if (readoutProgress) {
    readoutProgress.style.transform = `scaleX(${Math.min(1, elapsed / introDuration)})`
  }

  if (!hasArrived && elapsed >= introDuration) {
    markArrived()
  }

  const cameraPath = tunnelPathOffset(-18 + introProgress * 10, elapsed)
  const lookPath = tunnelPathOffset(-40 + introProgress * 14, elapsed + 0.32)
  const routeIntensity = hasArrived ? 0.28 : 1
  const tunnelDrift = Math.sin(elapsed * 2.2) * (1 - introProgress) * 0.34
  const targetX = pointer.x * (hasArrived ? 0.7 : 0.32)
    + cameraPath.x * 0.52 * routeIntensity
    + tunnelDrift
    + compareBias * (agentPathState.isRunning ? 0.95 : 0.52)
  const targetY = pointer.y * (hasArrived ? 0.42 : 0.24)
    + cameraPath.y * 0.55 * routeIntensity
    + (agentPathState.isRunning ? Math.sin(elapsed * 0.82) * 0.58 : Math.abs(compareBias) * 0.12)
  const targetZ = 18 - introProgress * 9
  camera.position.x += (targetX - camera.position.x) * 0.045
  camera.position.y += (targetY - camera.position.y) * 0.045
  camera.position.z += (targetZ - camera.position.z) * 0.04
  camera.lookAt(
    lookPath.x * 0.42 + pointer.x * 0.36,
    lookPath.y * 0.42 + pointer.y * 0.22,
    -36 + introProgress * 7,
  )
  camera.rotation.z += Math.sin(elapsed * 1.22) * 0.09 * routeIntensity

  renderer.render(scene, camera)
  requestAnimationFrame(animate)
}

window.addEventListener('resize', resizeRenderer)
window.addEventListener('pointermove', (event) => {
  pointer.x = (event.clientX / window.innerWidth - 0.5) * 2
  pointer.y = -(event.clientY / window.innerHeight - 0.5) * 2
})

buyerInput.addEventListener('focus', () => setDealFocus('buyer'))
targetInput.addEventListener('focus', () => setDealFocus('target'))
promptInput.addEventListener('focus', () => setDealFocus('neutral'))

function formatFileSummary(files, emptyLabel) {
  if (files.length === 0) {
    return emptyLabel
  }
  const totalSize = files.reduce((sum, file) => sum + file.size, 0)
  const sizeMb = totalSize / 1024 / 1024
  return `${files.length} PDF${files.length === 1 ? '' : 's'} selected, ${sizeMb.toFixed(1)} MB`
}

buyerFileInput.addEventListener('change', () => {
  const files = Array.from(buyerFileInput.files ?? [])
  buyerFileSummary.textContent = formatFileSummary(files, 'No buyer PDFs selected')
})

targetFileInput.addEventListener('change', () => {
  const files = Array.from(targetFileInput.files ?? [])
  targetFileSummary.textContent = formatFileSummary(files, 'No target PDFs selected')
})

function appendResultElement(tagName, text, className) {
  const element = document.createElement(tagName)
  element.textContent = text
  if (className) {
    element.className = className
  }
  workflowResult.appendChild(element)
  return element
}

function appendQuestionAnswers(answers) {
  if (!Array.isArray(answers) || answers.length === 0) {
    return
  }

  appendResultElement('strong', 'Answers to your questions')
  answers.slice(0, 8).forEach((item) => {
    const answerCard = document.createElement('article')
    answerCard.className = 'result-answer'

    const question = document.createElement('b')
    question.textContent = item.question ?? 'Question'
    answerCard.appendChild(question)

    const answer = document.createElement('span')
    answer.textContent = item.answer ?? 'No answer returned.'
    answerCard.appendChild(answer)

    const meta = [
      item.evidence_status,
      item.confidence ? `${item.confidence} confidence` : '',
      Array.isArray(item.source_agents) && item.source_agents.length
        ? item.source_agents.join(', ')
        : '',
    ].filter(Boolean)

    if (meta.length > 0) {
      const detail = document.createElement('small')
      detail.textContent = meta.join(' | ')
      answerCard.appendChild(detail)
    }

    workflowResult.appendChild(answerCard)
  })
}

function resolveReportUrl(data) {
  const candidates = [
    data?.pdf_url,
    data?.report_url,
    data?.output_url,
    data?.investment_memo?.pdf_url,
    data?.report?.url,
  ]

  return candidates.find((candidate) => typeof candidate === 'string' && candidate.length > 0)
}

function renderWorkflowResponse(data) {
  const memo = data?.investment_memo ?? {}
  const reportUrl = resolveReportUrl(data)
  workflowResult.textContent = ''
  workflowDock.classList.add('has-result')

  appendResultElement(
    'strong',
    memo.recommendation ?? (reportUrl ? 'Report ready' : 'Analysis complete'),
  )
  appendResultElement(
    'span',
    memo.executive_summary ?? data?.answer ?? 'The workflow returned a response.',
  )

  if (memo.headline) {
    appendResultElement('span', memo.headline, 'result-emphasis')
  }

  if (memo.buyer_target_fit_view) {
    appendResultElement('span', `Buyer-target fit: ${memo.buyer_target_fit_view}`)
  }

  appendQuestionAnswers(memo.question_answers)

  if (Array.isArray(memo.investment_committee_conditions) && memo.investment_committee_conditions.length > 0) {
    appendResultElement(
      'span',
      `Conditions: ${memo.investment_committee_conditions.slice(0, 3).join('; ')}`,
    )
  }

  if (Array.isArray(memo.open_questions) && memo.open_questions.length > 0) {
    appendResultElement('span', `Open questions: ${memo.open_questions.slice(0, 3).join('; ')}`)
  }

  if (reportUrl) {
    const link = appendResultElement('a', 'Open generated PDF', 'result-link')
    link.href = reportUrl
    link.target = '_blank'
    link.rel = 'noreferrer'
  }
}

function renderWorkflowError(
  title = 'Backend unavailable',
  message = 'Start the FastAPI backend on port 8000, then run the workflow again.',
) {
  workflowResult.textContent = ''
  workflowDock.classList.add('has-result')
  appendResultElement('strong', title)
  appendResultElement('span', message)
}

function parseDealQuestions(text) {
  return text
    .split(/\n+/)
    .map((question) => question.replace(/^\s*[-*\d.)]+\s*/, '').trim())
    .filter(Boolean)
}

form.addEventListener('submit', async (event) => {
  event.preventDefault()

  const buyerFiles = Array.from(buyerFileInput.files ?? [])
  const targetFiles = Array.from(targetFileInput.files ?? [])
  const buyerFileContext = buyerFiles.length
    ? `\n\nBuyer PDF filenames for reference:\n${buyerFiles.map((file) => `- ${file.name}`).join('\n')}`
    : ''
  const targetFileContext = targetFiles.length
    ? `\n\nTarget PDF filenames for reference:\n${targetFiles.map((file) => `- ${file.name}`).join('\n')}`
    : ''
  const buyerContext = `${buyerInput.value.trim()}${buyerFileContext}`.trim()
  const targetContext = `${targetInput.value.trim()}${targetFileContext}`.trim()
  const dealContext = promptInput.value.trim()
  const questions = parseDealQuestions(promptInput.value.trim())
  const hasFiles = buyerFiles.length > 0 || targetFiles.length > 0

  workflowStatus.textContent = 'Routing'
  workflowResult.textContent = ''
  workflowDock.classList.remove('has-result')
  form.classList.add('is-running')
  setDealFocus('neutral')
  startWorkflowLoader(hasFiles ? 'PDF + comparison' : 'Buyer-target comparison')
  const controller = new AbortController()
  const timeoutId = window.setTimeout(() => {
    controller.abort()
  }, WORKFLOW_TIMEOUT_MS)

  try {
    const response = await fetch('http://127.0.0.1:8000/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
      body: JSON.stringify({
        session_id: window.crypto?.randomUUID?.() ?? `session-${Date.now()}`,
        buyer_context: buyerContext,
        target_context: targetContext,
        deal_context: dealContext || 'Compare the buyer and target for a potential M&A transaction.',
        questions,
      }),
    })

    if (!response.ok) {
      throw new Error(`Workflow returned ${response.status}`)
    }

    const data = await response.json()
    workflowStatus.textContent = resolveReportUrl(data) ? 'Report ready' : 'Complete'
    renderWorkflowResponse(data)
    completeWorkflowLoader()
  } catch (error) {
    const didTimeout = error?.name === 'AbortError'
    workflowStatus.textContent = didTimeout ? 'Timed out' : 'Backend unavailable'
    renderWorkflowError(
      didTimeout ? 'Workflow timed out' : 'Backend unavailable',
      didTimeout
        ? 'The agent route completed, but the backend did not return before the timeout. Try a shorter prompt or run the backend logs to inspect the Gemini call.'
        : 'Start the FastAPI backend on port 8000, then run the workflow again.',
    )
    failWorkflowLoader(
      didTimeout
        ? 'Workflow timed out while waiting for the backend response.'
        : 'Workflow route interrupted. Check backend availability.',
    )
    console.error(error)
  } finally {
    window.clearTimeout(timeoutId)
    form.classList.remove('is-running')
  }
})

resizeRenderer()
animate()
window.setTimeout(markArrived, introDuration * 1000)

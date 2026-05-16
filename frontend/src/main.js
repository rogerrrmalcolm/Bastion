import './style.css'
import * as THREE from 'three'

const app = document.querySelector('#app')

app.innerHTML = `
  <main class="experience-shell is-traveling is-landing">
    <div id="scene-root" class="scene-root" aria-hidden="true"></div>
    <div class="flight-readout" aria-hidden="true">
      <span>Buyer Target Transit</span>
      <div class="readout-track"><i id="readout-progress"></i></div>
    </div>
    <section class="landing-page" aria-label="Bastion overview">
      <nav class="landing-nav" aria-label="Bastion navigation">
        <strong>Bastion</strong>
        <button id="landing-dashboard-button" class="ghost-action" type="button">Dashboard</button>
      </nav>
      <section class="landing-hero">
        <div class="landing-copy">
          <p class="eyebrow">AI diligence command center</p>
          <h1>Bastion</h1>
          <p>
            Bastion turns buyer materials, target materials, market context, and deal questions into
            an investment-committee-ready view of strategic fit, financial support, risk, and next
            diligence steps.
          </p>
          <div class="landing-actions">
            <button id="landing-start-button" class="primary-action" type="button">Open diligence terminal</button>
            <button id="landing-learn-button" class="ghost-action" type="button">See workflow</button>
          </div>
        </div>
      </section>
      <section id="landing-workflow" class="landing-section" aria-label="Bastion workflow">
        <div class="section-heading">
          <p class="eyebrow">How Bastion Works</p>
          <h2>From messy deal inputs to a decision-ready memo.</h2>
        </div>
        <div class="landing-grid">
          <article>
            <span>01</span>
            <strong>Separate buyer and target context</strong>
            <p>Upload or paste each side of the transaction independently so the analysis can compare capacity, fit, risks, and evidence gaps.</p>
          </article>
          <article>
            <span>02</span>
            <strong>Route specialist agents</strong>
            <p>Market, financial, and risk agents pressure-test the thesis before the memo agent synthesizes the committee view.</p>
          </article>
          <article>
            <span>03</span>
            <strong>Generate visuals beside the report</strong>
            <p>Decision signal, confidence, risk mix, and diligence queue visuals make the output faster to read and easier to discuss.</p>
          </article>
        </div>
      </section>
      <section class="landing-section landing-band" aria-label="Bastion audience">
        <div class="section-heading">
          <p class="eyebrow">Built For Deal Work</p>
          <h2>A focused workspace for M&A screening and diligence follow-up.</h2>
        </div>
        <div class="landing-split">
          <p>
            Bastion is designed for analysts and deal teams who need a structured first-pass view of
            whether a buyer-target combination is worth more work. It keeps the workflow close to the
            actual questions: strategic fit, valuation support, downside risk, missing information,
            and conditions before signing.
          </p>
          <button id="landing-bottom-start-button" class="primary-action" type="button">Start analysis</button>
        </div>
      </section>
    </section>
    <section class="workflow-dock" aria-label="Bastion workflow input">
      <div class="dock-header">
        <div class="dock-heading">
          <div class="terminal-logo" aria-label="Bastion">
            <span>B</span>
            <strong>Bastion</strong>
          </div>
          <p class="eyebrow">Bastion M&A Workflow</p>
          <h1>Diligence terminal</h1>
        </div>
        <div class="view-switch" role="tablist" aria-label="Workflow views">
          <button id="analysis-view-button" class="view-tab is-active" type="button" role="tab" aria-selected="true">
            Analyze
          </button>
          <button id="dashboard-view-button" class="view-tab" type="button" role="tab" aria-selected="false">
            Dashboard
          </button>
        </div>
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
      <section id="dashboard-panel" class="dashboard-panel" aria-label="Deal dashboard" hidden>
        <div class="dashboard-hero">
          <div>
            <span>Pipeline</span>
            <strong id="dashboard-count">0 analyses</strong>
          </div>
          <button id="clear-dashboard-button" class="subtle-button" type="button">Clear</button>
        </div>
        <div class="dashboard-metrics">
          <article>
            <span>Total</span>
            <strong id="dashboard-total">0</strong>
          </article>
          <article>
            <span>Proceed</span>
            <strong id="dashboard-proceed">0</strong>
          </article>
          <article>
            <span>High Risk</span>
            <strong id="dashboard-risk">0</strong>
          </article>
          <article>
            <span>Questions</span>
            <strong id="dashboard-questions">0</strong>
          </article>
        </div>
        <div id="dashboard-list" class="dashboard-list"></div>
      </section>
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
const landingStartButton = document.querySelector('#landing-start-button')
const landingBottomStartButton = document.querySelector('#landing-bottom-start-button')
const landingDashboardButton = document.querySelector('#landing-dashboard-button')
const landingLearnButton = document.querySelector('#landing-learn-button')
const workflowDock = document.querySelector('.workflow-dock')
const analysisViewButton = document.querySelector('#analysis-view-button')
const dashboardViewButton = document.querySelector('#dashboard-view-button')
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
const dashboardPanel = document.querySelector('#dashboard-panel')
const dashboardCount = document.querySelector('#dashboard-count')
const dashboardTotal = document.querySelector('#dashboard-total')
const dashboardProceed = document.querySelector('#dashboard-proceed')
const dashboardRisk = document.querySelector('#dashboard-risk')
const dashboardQuestions = document.querySelector('#dashboard-questions')
const dashboardList = document.querySelector('#dashboard-list')
const clearDashboardButton = document.querySelector('#clear-dashboard-button')
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
const workspaceTransitionDuration = 2.15
const WORKFLOW_TIMEOUT_MS = 420000
const API_BASE_URL = 'http://127.0.0.1:8000'
const DASHBOARD_STORAGE_KEY = 'bastion-dashboard-analyses'
const confidenceScores = {
  low: 34,
  medium: 67,
  high: 100,
}
const severityScores = {
  low: 34,
  medium: 67,
  high: 100,
  critical: 100,
}
const recommendationScores = {
  proceed: 92,
  proceed_with_caution: 68,
  pause: 42,
  decline: 18,
}
let hasArrived = false
let dealFocus = 'neutral'
const workspaceTransition = {
  isActive: false,
  startedAt: 0,
  targetView: 'analysis',
  timer: null,
}

const palette = {
  espresso: new THREE.Color(0x2b1a12),
  brown: new THREE.Color(0x5b3a29),
  copper: new THREE.Color(0x9b6a35),
  sand: new THREE.Color(0xd7c4aa),
  ivory: new THREE.Color(0xf4efe6),
  white: new THREE.Color(0xffffff),
}

const agentGraph = {
  centralNodeId: 'bastion',
  nodes: [
    { id: 'bastion', label: 'Bastion', role: 'agent routing core', x: 50, y: 50, badge: 'B', kind: 'core' },
    { id: 'buyer', label: 'Buyer', role: 'acquirer profile', x: 17, y: 25, badge: 'BY' },
    { id: 'target', label: 'Target', role: 'company profile', x: 18, y: 67, badge: 'TG' },
    { id: 'documents', label: 'Documents', role: 'PDF context', x: 35, y: 18, badge: 'PDF' },
    { id: 'market-data', label: 'Market Data', role: 'live signals', x: 32, y: 83, badge: 'MD' },
    { id: 'market', label: 'Market Agent', role: 'sector signals', x: 63, y: 18, badge: 'MA' },
    { id: 'financial', label: 'Financial Agent', role: 'QoE and valuation', x: 82, y: 35, badge: 'FA' },
    { id: 'risk', label: 'Risk Agent', role: 'risk matrix', x: 82, y: 66, badge: 'RA' },
    { id: 'memo', label: 'Memo Agent', role: 'IC synthesis', x: 67, y: 83, badge: 'IC' },
    { id: 'output', label: 'Answer', role: 'buyer-target memo', x: 50, y: 87, badge: 'OUT' },
  ],
  edges: [
    ['bastion', 'buyer', 1],
    ['bastion', 'target', 2],
    ['bastion', 'documents', 3],
    ['bastion', 'market-data', 4],
    ['bastion', 'market', 5],
    ['bastion', 'financial', 6],
    ['bastion', 'risk', 7],
    ['bastion', 'memo', 8],
    ['bastion', 'output', 9],
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

function wirePath(fromNode, toNode, index) {
  const dx = toNode.x - fromNode.x
  const dy = toNode.y - fromNode.y
  const offset = ((index % 3) - 1) * 1.8
  const horizontalFirst = Math.abs(dx) >= Math.abs(dy)
  const bendX = fromNode.x + dx * 0.48 + offset
  const bendY = fromNode.y + dy * 0.48 - offset

  if (horizontalFirst) {
    return `M ${fromNode.x} ${fromNode.y} L ${bendX} ${fromNode.y} L ${bendX} ${toNode.y} L ${toNode.x} ${toNode.y}`
  }

  return `M ${fromNode.x} ${fromNode.y} L ${fromNode.x} ${bendY} L ${toNode.x} ${bendY} L ${toNode.x} ${toNode.y}`
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
  const dijkstra = computeDijkstraRoute(agentGraph, agentGraph.centralNodeId, 'output')
  agentPathState.route = dijkstra.visitOrder.length > 0 ? dijkstra.visitOrder : dijkstra.route
  agentPathState.distances = dijkstra.distances
  agentPathState.visitOrder = dijkstra.visitOrder

  const lines = agentGraph.edges.map(([from, to, weight], index) => {
    const fromNode = agentGraph.nodes.find((node) => node.id === from)
    const toNode = agentGraph.nodes.find((node) => node.id === to)
    return `
      <g class="map-edge" data-edge="${edgeId(from, to)}">
        <path d="${wirePath(fromNode, toNode, index)}" pathLength="100" vector-effect="non-scaling-stroke" />
        <circle class="wire-contact" cx="${toNode.x}" cy="${toNode.y}" r="0.72" />
        <text x="${fromNode.x + (toNode.x - fromNode.x) * 0.56}" y="${fromNode.y + (toNode.y - fromNode.y) * 0.56}">d${weight}</text>
      </g>
    `
  }).join('')

  const nodes = agentGraph.nodes.map((node) => {
    const classes = [
      'map-node',
      node.kind === 'core' ? 'is-core' : '',
      node.id === 'output' ? 'is-output' : '',
    ].filter(Boolean).join(' ')

    return `
    <div class="${classes}" data-node="${node.id}" style="left: ${node.x}%; top: ${node.y}%;">
      <i aria-hidden="true">${node.badge ?? node.label.slice(0, 2).toUpperCase()}</i>
      <strong>${node.label}</strong>
      <span>${node.role}</span>
      <small data-distance="${node.id}">cost inf</small>
    </div>
  `
  }).join('')

  workflowMap.innerHTML = `
    <svg class="map-edges" viewBox="0 0 100 100" preserveAspectRatio="none">
      ${lines}
    </svg>
    ${nodes}
  `
}

function setLoaderStep(stepIndex, isComplete = false) {
  const route = agentPathState.route
  const centralNodeId = agentGraph.centralNodeId
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

  const activeWireTarget = activeId === centralNodeId ? route[boundedIndex + 1] : activeId
  const activeEdgeId = activeWireTarget && activeWireTarget !== centralNodeId
    ? edgeId(centralNodeId, activeWireTarget)
    : ''

  workflowMap.querySelectorAll('.map-edge').forEach((edgeElement) => {
    const isRouteEdge = [...reached].some((nodeId) => (
      nodeId !== centralNodeId && edgeId(centralNodeId, nodeId) === edgeElement.dataset.edge
    ))
    const isActiveEdge = edgeElement.dataset.edge === activeEdgeId
    edgeElement.classList.toggle('is-route', isRouteEdge)
    edgeElement.classList.toggle('is-active', isActiveEdge && !isComplete)
  })

  currentAgent.textContent = activeNode?.label ?? 'Routing'
  routeCost.textContent = Number.isFinite(agentPathState.distances[activeId])
    ? String(agentPathState.distances[activeId])
    : 'inf'
}

function startWorkflowLoader(mode) {
  renderWorkflowMap()

  agentPathState.startedAt = performance.now()
  agentPathState.isRunning = true
  agentPathState.isAwaitingResponse = false
  responseMode.textContent = mode
  loaderCaption.textContent = 'Bastion is energizing the agent circuit around the deal.'
  workflowLoader.setAttribute('aria-hidden', 'false')
  shell.classList.add('is-processing')
  shell.classList.add('is-comparing')

  const tick = (timestamp) => {
    if (!agentPathState.isRunning) {
      return
    }

    const elapsed = timestamp - agentPathState.startedAt
    const stepDuration = 1500
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
      loaderCaption.textContent = 'Agent circuit lit. Waiting for Bastion to produce the answer.'
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
  loaderCaption.textContent = 'Bastion circuit complete. Rendering response.'
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

function finishWorkspaceTransition() {
  if (!workspaceTransition.isActive) {
    return
  }

  workspaceTransition.isActive = false
  if (workspaceTransition.timer) {
    window.clearTimeout(workspaceTransition.timer)
    workspaceTransition.timer = null
  }
  markArrived()
  shell.classList.remove('is-landing', 'is-transitioning')
  switchWorkflowView(workspaceTransition.targetView)
  landingStartButton.disabled = false
  landingBottomStartButton.disabled = false
  landingDashboardButton.disabled = false
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
  const transitionRaw = workspaceTransition.isActive
    ? Math.min(1, Math.max(0, (performance.now() - workspaceTransition.startedAt) / (workspaceTransitionDuration * 1000)))
    : 0
  const transitionProgress = smoothstep(0, 1, transitionRaw)
  const transitionPulse = Math.sin(transitionProgress * Math.PI)
  const positions = stars.geometry.attributes.position.array
  const speed = 30 + (1 - introProgress) * 34 + transitionPulse * 82

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
    ring.position.z += ring.userData.speed * delta * (1 + (1 - introProgress) * 1.65 + transitionPulse * 2.25)
    const ringPath = tunnelPathOffset(ring.position.z + ring.userData.pathPhase, elapsed)
    const pathIntensity = hasArrived ? 0.46 : 1
    ring.position.x = ringPath.x * pathIntensity
    ring.position.y = ringPath.y * pathIntensity
    ring.rotation.z += delta * (index % 2 === 0 ? 0.2 : -0.12)
    ring.rotation.x = Math.sin(elapsed * 0.45 + index * 0.12) * 0.09 * pathIntensity
    ring.rotation.y = Math.cos(elapsed * 0.36 + index * 0.1) * 0.08 * pathIntensity
    ring.material.opacity = 0.09 + Math.max(0, 1 - Math.abs(ring.position.z) / 80) * 0.22 + transitionPulse * 0.08

    if (ring.position.z > nearLimit) {
      ring.position.z = farLimit
    }
  })

  const symbolFade = 1 - smoothstep(2.35, introDuration + 0.35, elapsed)
  financeSymbols.children.forEach((sprite) => {
    sprite.position.z += sprite.userData.speed * delta * (1 + transitionPulse * 1.6)
    const path = tunnelPathOffset(sprite.position.z, elapsed)
    const orbit = sprite.userData.angle + elapsed * sprite.userData.orbitSpeed + sprite.position.z * 0.045
    sprite.position.x = path.x + Math.cos(orbit) * sprite.userData.radius
    sprite.position.y = path.y + Math.sin(orbit * 0.94) * sprite.userData.radius * 0.78
    sprite.material.rotation += sprite.userData.spin * delta
    sprite.material.opacity = 0.92 * symbolFade * (1 - transitionProgress * 0.65)
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
  arrivalGate.position.z = -76 + introProgress * 48 + Math.sin(elapsed * 0.7) * 1.4 + transitionPulse * 23 + transitionProgress * 5
  arrivalGate.position.x = gatePath.x * 0.58
  arrivalGate.position.y = gatePath.y * 0.58
  arrivalGate.scale.setScalar(0.72 + introProgress * 0.46 + Math.sin(elapsed * 1.3) * 0.035 + transitionPulse * 0.85)

  const compareBias = agentPathState.isRunning
    ? Math.sin(elapsed * 1.15)
    : dealFocus === 'buyer'
      ? -1
      : dealFocus === 'target'
        ? 1
        : 0
  const beaconOpacity = workspaceTransition.isActive
    ? 0.28 + transitionProgress * 0.68
    : hasArrived ? (agentPathState.isRunning ? 0.95 : 0.48) : introProgress * 0.2
  const buyerEmphasis = compareBias < -0.16 ? 1 : 0.62
  const targetEmphasis = compareBias > 0.16 ? 1 : 0.62
  const beaconPath = tunnelPathOffset(-24, elapsed)
  dealBeacons.position.x = beaconPath.x * 0.22
  dealBeacons.position.y = 0.72 + beaconPath.y * 0.15 + Math.sin(elapsed * 0.9) * 0.08
  dealBeacons.position.z = -23 + Math.sin(elapsed * 0.52) * 0.6 + transitionProgress * 7.5
  dealBeacons.rotation.z = Math.sin(elapsed * 0.28) * 0.08 + transitionPulse * 0.18
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

  if (workspaceTransition.isActive && transitionRaw >= 1) {
    finishWorkspaceTransition()
  }

  const cameraPath = tunnelPathOffset(-18 + introProgress * 10, elapsed)
  const lookPath = tunnelPathOffset(-40 + introProgress * 14, elapsed + 0.32)
  const routeIntensity = workspaceTransition.isActive ? 0.14 : hasArrived ? 0.28 : 1
  const tunnelDrift = Math.sin(elapsed * 2.2) * (1 - introProgress) * 0.34
  const pointerDamp = 1 - transitionProgress * 0.78
  const targetX = pointer.x * (hasArrived ? 0.7 : 0.32) * pointerDamp
    + cameraPath.x * 0.52 * routeIntensity
    + tunnelDrift
    + compareBias * (agentPathState.isRunning ? 0.95 : 0.52)
  const targetY = pointer.y * (hasArrived ? 0.42 : 0.24) * pointerDamp
    + cameraPath.y * 0.55 * routeIntensity
    + (agentPathState.isRunning ? Math.sin(elapsed * 0.82) * 0.58 : Math.abs(compareBias) * 0.12)
    + transitionPulse * 0.35
  const targetZ = 18 - introProgress * 9 - transitionPulse * 5.5 + transitionProgress * 0.75
  const cameraEase = workspaceTransition.isActive ? 0.085 : 0.045
  camera.position.x += (targetX - camera.position.x) * cameraEase
  camera.position.y += (targetY - camera.position.y) * cameraEase
  camera.position.z += (targetZ - camera.position.z) * (workspaceTransition.isActive ? 0.082 : 0.04)
  camera.lookAt(
    lookPath.x * 0.42 + pointer.x * 0.36,
    lookPath.y * 0.42 + pointer.y * 0.22,
    -36 + introProgress * 7 + transitionProgress * 10,
  )
  camera.rotation.z += Math.sin(elapsed * 1.22) * 0.09 * routeIntensity + transitionPulse * 0.018

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

async function uploadPdfFiles(files, side, signal) {
  const uploads = []
  for (const file of files) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('side', side)

    const response = await fetch(`${API_BASE_URL}/documents/upload`, {
      method: 'POST',
      body: formData,
      signal,
    })

    if (!response.ok) {
      const detail = await response.text()
      throw new Error(`S3 upload failed for ${file.name}: ${detail}`)
    }

    uploads.push(await response.json())
  }
  return uploads
}

function formatUploadedPdfContext(label, uploads) {
  if (!uploads.length) {
    return ''
  }

  return `\n\n${label} PDFs stored in S3:\n${uploads
    .map((upload) => `- ${upload.filename}: ${upload.uri}`)
    .join('\n')}`
}

function openWorkspace(view = 'analysis') {
  if (workspaceTransition.isActive) {
    return
  }

  workspaceTransition.isActive = true
  workspaceTransition.startedAt = performance.now()
  workspaceTransition.targetView = view
  workspaceTransition.timer = window.setTimeout(
    finishWorkspaceTransition,
    workspaceTransitionDuration * 1000 + 220,
  )
  landingStartButton.disabled = true
  landingBottomStartButton.disabled = true
  landingDashboardButton.disabled = true
  shell.classList.add('is-transitioning')
  switchWorkflowView(view)
}

landingStartButton.addEventListener('click', () => openWorkspace('analysis'))
landingBottomStartButton.addEventListener('click', () => openWorkspace('analysis'))
landingDashboardButton.addEventListener('click', () => openWorkspace('dashboard'))
landingLearnButton.addEventListener('click', () => {
  document.querySelector('#landing-workflow')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
})

analysisViewButton.addEventListener('click', () => switchWorkflowView('analysis'))
dashboardViewButton.addEventListener('click', () => switchWorkflowView('dashboard'))
clearDashboardButton.addEventListener('click', () => {
  window.localStorage.removeItem(DASHBOARD_STORAGE_KEY)
  renderDashboard()
})

function switchWorkflowView(view) {
  const isDashboard = view === 'dashboard'
  workflowDock.classList.toggle('is-dashboard', isDashboard)
  form.hidden = isDashboard
  workflowResult.hidden = isDashboard
  dashboardPanel.hidden = !isDashboard
  analysisViewButton.classList.toggle('is-active', !isDashboard)
  dashboardViewButton.classList.toggle('is-active', isDashboard)
  analysisViewButton.setAttribute('aria-selected', String(!isDashboard))
  dashboardViewButton.setAttribute('aria-selected', String(isDashboard))

  if (isDashboard) {
    renderDashboard()
  }
}

function toTitleCase(value) {
  return String(value ?? '')
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function clampPercent(value) {
  return Math.max(0, Math.min(100, Number.isFinite(value) ? value : 0))
}

function scoreForConfidence(value) {
  return confidenceScores[String(value ?? '').toLowerCase()] ?? 0
}

function scoreForSeverity(value) {
  return severityScores[String(value ?? '').toLowerCase()] ?? 0
}

function scoreForRecommendation(value) {
  return recommendationScores[String(value ?? '').toLowerCase()] ?? 50
}

function getRiskItems(data) {
  const risk = data?.risk_analysis ?? {}
  return [
    ...(Array.isArray(risk.top_risks) ? risk.top_risks : []),
    ...(Array.isArray(risk.deal_breaker_risks) ? risk.deal_breaker_risks : []),
    ...(Array.isArray(risk.acquisition_risk_factors) ? risk.acquisition_risk_factors : []),
  ]
}

function getRiskMix(data) {
  return getRiskItems(data).reduce(
    (mix, item) => {
      const severity = String(item.severity ?? '').toLowerCase()
      if (severity in mix) {
        mix[severity] += 1
      }
      return mix
    },
    { low: 0, medium: 0, high: 0 },
  )
}

function createMeter(label, value, score, className = '') {
  const meter = document.createElement('div')
  meter.className = `metric-meter ${className}`.trim()

  const row = document.createElement('div')
  row.className = 'metric-meter-row'

  const labelElement = document.createElement('span')
  labelElement.textContent = label
  row.appendChild(labelElement)

  const valueElement = document.createElement('strong')
  valueElement.textContent = value
  row.appendChild(valueElement)

  const track = document.createElement('i')
  track.style.setProperty('--meter-value', `${clampPercent(score)}%`)

  meter.append(row, track)
  return meter
}

function createVisualCard(title, value, detail) {
  const card = document.createElement('article')
  card.className = 'visual-card'

  const titleElement = document.createElement('span')
  titleElement.textContent = title
  card.appendChild(titleElement)

  const valueElement = document.createElement('strong')
  valueElement.textContent = value
  card.appendChild(valueElement)

  if (detail) {
    const detailElement = document.createElement('small')
    detailElement.textContent = detail
    card.appendChild(detailElement)
  }

  return card
}

function buildReportVisuals(data) {
  const memo = data?.investment_memo ?? {}
  const risk = data?.risk_analysis ?? {}
  const riskMix = getRiskMix(data)
  const highRiskCount = riskMix.high
  const totalRisks = riskMix.low + riskMix.medium + riskMix.high
  const openQuestionCount = Array.isArray(memo.open_questions) ? memo.open_questions.length : 0
  const conditionCount = Array.isArray(memo.investment_committee_conditions)
    ? memo.investment_committee_conditions.length
    : 0
  const nextStepCount = Array.isArray(memo.next_diligence_steps) ? memo.next_diligence_steps.length : 0

  const section = document.createElement('section')
  section.className = 'report-visuals'
  section.setAttribute('aria-label', 'Report visuals')

  const header = document.createElement('div')
  header.className = 'visuals-header'
  const headerTitle = document.createElement('strong')
  headerTitle.textContent = 'Deal visuals'
  const headerMeta = document.createElement('span')
  headerMeta.textContent = `${totalRisks} risks tracked | ${openQuestionCount} open questions`
  header.append(headerTitle, headerMeta)
  section.appendChild(header)

  const grid = document.createElement('div')
  grid.className = 'visual-grid'

  const recommendation = memo.recommendation ?? 'analysis'
  const decisionCard = createVisualCard(
    'Decision Signal',
    toTitleCase(recommendation),
    memo.overall_confidence ? `${memo.overall_confidence} memo confidence` : '',
  )
  decisionCard.appendChild(createMeter('Signal strength', `${scoreForRecommendation(recommendation)}%`, scoreForRecommendation(recommendation)))
  grid.appendChild(decisionCard)

  const confidenceCard = createVisualCard('Agent Confidence', 'Workstream View')
  confidenceCard.append(
    createMeter('Market', toTitleCase(data?.market_analysis?.overall_confidence || 'unknown'), scoreForConfidence(data?.market_analysis?.overall_confidence)),
    createMeter('Financial', toTitleCase(data?.financial_analysis?.overall_confidence || 'unknown'), scoreForConfidence(data?.financial_analysis?.overall_confidence)),
    createMeter('Risk', toTitleCase(data?.risk_analysis?.overall_confidence || 'unknown'), scoreForConfidence(data?.risk_analysis?.overall_confidence)),
    createMeter('Memo', toTitleCase(memo.overall_confidence || 'unknown'), scoreForConfidence(memo.overall_confidence)),
  )
  grid.appendChild(confidenceCard)

  const riskCard = createVisualCard(
    'Risk Mix',
    risk.overall_deal_risk_score ? toTitleCase(risk.overall_deal_risk_score) : `${highRiskCount} High`,
    risk.overall_risk_rating ? `${risk.overall_risk_rating} overall rating` : '',
  )
  const riskMax = Math.max(riskMix.low, riskMix.medium, riskMix.high, 1)
  riskCard.append(
    createMeter('Low', String(riskMix.low), (riskMix.low / riskMax) * 100, 'meter-low'),
    createMeter('Medium', String(riskMix.medium), (riskMix.medium / riskMax) * 100, 'meter-medium'),
    createMeter('High', String(riskMix.high), (riskMix.high / riskMax) * 100, 'meter-high'),
  )
  grid.appendChild(riskCard)

  const diligenceCard = createVisualCard('Diligence Queue', `${openQuestionCount + conditionCount + nextStepCount} Items`)
  const diligenceMax = Math.max(openQuestionCount, conditionCount, nextStepCount, 1)
  diligenceCard.append(
    createMeter('Conditions', String(conditionCount), (conditionCount / diligenceMax) * 100),
    createMeter('Open Questions', String(openQuestionCount), (openQuestionCount / diligenceMax) * 100),
    createMeter('Next Steps', String(nextStepCount), (nextStepCount / diligenceMax) * 100),
  )
  grid.appendChild(diligenceCard)

  section.appendChild(grid)
  return section
}

function loadDashboardSummaries() {
  try {
    const stored = JSON.parse(window.localStorage.getItem(DASHBOARD_STORAGE_KEY) ?? '[]')
    return Array.isArray(stored) ? stored : []
  } catch {
    return []
  }
}

function saveDashboardSummary(data, buyerContext, targetContext) {
  const memo = data?.investment_memo ?? {}
  const riskMix = getRiskMix(data)
  const summaries = loadDashboardSummaries()
  // Store only display summaries until authenticated database persistence is wired.
  const summary = {
    id: data?.session_id ?? `analysis-${Date.now()}`,
    createdAt: new Date().toISOString(),
    title: memo.headline || memo.recommendation_rationale || 'Untitled analysis',
    recommendation: memo.recommendation ?? 'analysis',
    confidence: memo.overall_confidence ?? 'unknown',
    riskRating: data?.risk_analysis?.overall_deal_risk_score ?? data?.risk_analysis?.overall_risk_rating ?? 'unknown',
    highRiskCount: riskMix.high,
    openQuestions: Array.isArray(memo.open_questions) ? memo.open_questions.length : 0,
    conditions: Array.isArray(memo.investment_committee_conditions) ? memo.investment_committee_conditions.length : 0,
    buyerLength: buyerContext.length,
    targetLength: targetContext.length,
  }

  const nextSummaries = [summary, ...summaries.filter((item) => item.id !== summary.id)].slice(0, 12)
  window.localStorage.setItem(DASHBOARD_STORAGE_KEY, JSON.stringify(nextSummaries))
  renderDashboard(nextSummaries)
}

function renderDashboard(providedSummaries) {
  const summaries = providedSummaries ?? loadDashboardSummaries()
  const total = summaries.length
  const proceed = summaries.filter((item) => item.recommendation === 'proceed').length
  const highRisk = summaries.filter((item) => item.highRiskCount > 0 || item.riskRating === 'high' || item.riskRating === 'critical').length
  const questions = summaries.reduce((sum, item) => sum + (item.openQuestions ?? 0), 0)

  dashboardCount.textContent = `${total} ${total === 1 ? 'analysis' : 'analyses'}`
  dashboardTotal.textContent = String(total)
  dashboardProceed.textContent = String(proceed)
  dashboardRisk.textContent = String(highRisk)
  dashboardQuestions.textContent = String(questions)
  dashboardList.textContent = ''

  if (total === 0) {
    const empty = document.createElement('p')
    empty.className = 'dashboard-empty'
    empty.textContent = 'Completed deal analyses will appear here.'
    dashboardList.appendChild(empty)
    return
  }

  summaries.forEach((item) => {
    const card = document.createElement('article')
    card.className = 'dashboard-card'

    const cardHeader = document.createElement('div')
    cardHeader.className = 'dashboard-card-header'

    const title = document.createElement('strong')
    title.textContent = item.title
    cardHeader.appendChild(title)

    const date = document.createElement('span')
    date.textContent = new Intl.DateTimeFormat(undefined, {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    }).format(new Date(item.createdAt))
    cardHeader.appendChild(date)

    const meta = document.createElement('div')
    meta.className = 'dashboard-card-meta'
    const metaItems = [
      toTitleCase(item.recommendation),
      `${toTitleCase(item.confidence)} confidence`,
      `${toTitleCase(item.riskRating)} risk`,
      `${item.openQuestions ?? 0} open questions`,
    ]
    metaItems.forEach((value) => {
      const pill = document.createElement('span')
      pill.textContent = value
      meta.appendChild(pill)
    })

    const bars = document.createElement('div')
    bars.className = 'dashboard-bars'
    bars.append(
      createMeter('Decision', `${scoreForRecommendation(item.recommendation)}%`, scoreForRecommendation(item.recommendation)),
      createMeter('Confidence', toTitleCase(item.confidence), scoreForConfidence(item.confidence)),
      createMeter('Risk', toTitleCase(item.riskRating), scoreForSeverity(item.riskRating), 'meter-high'),
    )

    card.append(cardHeader, meta, bars)
    dashboardList.appendChild(card)
  })
}

function appendResultElement(tagName, text, className) {
  const element = document.createElement(tagName)
  element.textContent = text
  if (className) {
    element.className = className
  }
  workflowResult.appendChild(element)
  return element
}

function citationLabel(citation) {
  const parts = [
    citation.title,
    citation.source && citation.source !== citation.title ? citation.source : '',
    citation.page ? `p. ${citation.page}` : '',
    citation.as_of ? `as of ${citation.as_of}` : '',
  ].filter(Boolean)
  return parts.join(' | ') || 'Source'
}

function appendBulletList(parent, items, className = 'report-bullets') {
  if (!Array.isArray(items) || items.length === 0) {
    return
  }

  const list = document.createElement('ul')
  list.className = className
  items.slice(0, 8).forEach((item) => {
    const text = String(item ?? '').trim()
    if (!text) {
      return
    }
    const li = document.createElement('li')
    li.textContent = text
    list.appendChild(li)
  })

  if (list.childElementCount > 0) {
    parent.appendChild(list)
  }
}

function appendCitationList(parent, citations, limit = 5) {
  const list = document.createElement('ul')
  list.className = 'citation-list'
  const usableCitations = Array.isArray(citations) ? citations.slice(0, limit) : []

  usableCitations.forEach((citation) => {
    const li = document.createElement('li')

    const label = citation.url ? document.createElement('a') : document.createElement('span')
    label.textContent = citationLabel(citation)
    if (citation.url) {
      label.href = citation.url
      label.target = '_blank'
      label.rel = 'noreferrer'
    }
    li.appendChild(label)

    const meta = document.createElement('small')
    meta.textContent = [
      citation.agent_name ? toTitleCase(citation.agent_name) : '',
      citation.source_type ? toTitleCase(citation.source_type) : '',
      citation.relevance,
    ].filter(Boolean).join(' | ')
    li.appendChild(meta)

    if (citation.excerpt) {
      const excerpt = document.createElement('em')
      excerpt.textContent = citation.excerpt
      li.appendChild(excerpt)
    }

    list.appendChild(li)
  })

  if (list.childElementCount === 0) {
    const empty = document.createElement('p')
    empty.className = 'citation-empty'
    empty.textContent = 'No source citations returned for this item.'
    parent.appendChild(empty)
    return
  }

  parent.appendChild(list)
}

function appendReportPackage(report) {
  if (!report || typeof report !== 'object') {
    return
  }

  const packageSection = document.createElement('section')
  packageSection.className = 'report-package'
  packageSection.setAttribute('aria-label', 'Structured report service')

  const header = document.createElement('div')
  header.className = 'report-package-header'
  const headerTitle = document.createElement('strong')
  headerTitle.textContent = report.title || 'Compiled report'
  const headerMeta = document.createElement('span')
  headerMeta.textContent = [
    report.recommendation ? toTitleCase(report.recommendation) : '',
    Array.isArray(report.source_register) ? `${report.source_register.length} sources` : '',
  ].filter(Boolean).join(' | ')
  header.append(headerTitle, headerMeta)
  packageSection.appendChild(header)

  if (report.executive_summary) {
    const summary = document.createElement('p')
    summary.className = 'report-summary'
    summary.textContent = report.executive_summary
    packageSection.appendChild(summary)
  }

  if (Array.isArray(report.agent_contributions) && report.agent_contributions.length > 0) {
    const agentSection = document.createElement('section')
    agentSection.className = 'agent-source-map'

    const agentTitle = document.createElement('strong')
    agentTitle.textContent = 'Agent contributions and citations'
    agentSection.appendChild(agentTitle)

    const grid = document.createElement('div')
    grid.className = 'agent-contribution-grid'

    report.agent_contributions.forEach((contribution) => {
      const card = document.createElement('article')
      card.className = 'agent-contribution-card'

      const cardHeader = document.createElement('div')
      cardHeader.className = 'agent-card-header'

      const label = document.createElement('strong')
      label.textContent = contribution.label || toTitleCase(contribution.agent_name || 'Agent')
      cardHeader.appendChild(label)

      if (contribution.confidence) {
        const confidence = document.createElement('span')
        confidence.textContent = `${toTitleCase(contribution.confidence)} confidence`
        cardHeader.appendChild(confidence)
      }

      const summary = document.createElement('p')
      summary.textContent = contribution.summary || 'No contribution summary returned.'

      const providesLabel = document.createElement('b')
      providesLabel.textContent = 'Provides to final solution'

      const sourcesLabel = document.createElement('b')
      sourcesLabel.textContent = 'Sources used'

      card.append(cardHeader, summary, providesLabel)
      appendBulletList(card, contribution.provides_to_final_solution)
      card.appendChild(sourcesLabel)
      appendCitationList(card, contribution.citations, 4)
      grid.appendChild(card)
    })

    agentSection.appendChild(grid)
    packageSection.appendChild(agentSection)
  }

  if (Array.isArray(report.sections) && report.sections.length > 0) {
    const sections = document.createElement('section')
    sections.className = 'compiled-report-sections'

    const sectionTitle = document.createElement('strong')
    sectionTitle.textContent = 'Compiled report'
    sections.appendChild(sectionTitle)

    report.sections.forEach((section) => {
      const article = document.createElement('article')
      article.className = 'compiled-report-section'

      const title = document.createElement('b')
      title.textContent = section.title || 'Report section'
      article.appendChild(title)

      if (section.summary) {
        const summary = document.createElement('p')
        summary.textContent = section.summary
        article.appendChild(summary)
      }

      appendBulletList(article, section.bullets)

      if (Array.isArray(section.source_agents) && section.source_agents.length > 0) {
        const agents = document.createElement('small')
        agents.textContent = `Source agents: ${section.source_agents.map(toTitleCase).join(', ')}`
        article.appendChild(agents)
      }

      appendCitationList(article, section.citations, 3)
      sections.appendChild(article)
    })

    packageSection.appendChild(sections)
  }

  if (Array.isArray(report.source_limitations) && report.source_limitations.length > 0) {
    const limitations = document.createElement('section')
    limitations.className = 'source-limitations'
    const title = document.createElement('strong')
    title.textContent = 'Source limitations'
    limitations.appendChild(title)
    appendBulletList(limitations, report.source_limitations)
    packageSection.appendChild(limitations)
  }

  workflowResult.appendChild(packageSection)
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
  workflowResult.appendChild(buildReportVisuals(data))
  appendReportPackage(data?.report)

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
  const dealContext = promptInput.value.trim()
  const questions = parseDealQuestions(promptInput.value.trim())
  const hasFiles = buyerFiles.length > 0 || targetFiles.length > 0

  workflowStatus.textContent = hasFiles ? 'Uploading PDFs' : 'Routing'
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
    const [buyerUploads, targetUploads] = await Promise.all([
      uploadPdfFiles(buyerFiles, 'buyer', controller.signal),
      uploadPdfFiles(targetFiles, 'target', controller.signal),
    ])
    const buyerContext = `${buyerInput.value.trim()}${formatUploadedPdfContext('Buyer', buyerUploads)}`.trim()
    const targetContext = `${targetInput.value.trim()}${formatUploadedPdfContext('Target', targetUploads)}`.trim()

    workflowStatus.textContent = 'Routing'
    const response = await fetch(`${API_BASE_URL}/analyze`, {
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
    saveDashboardSummary(data, buyerContext, targetContext)
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

renderDashboard()
resizeRenderer()
animate()

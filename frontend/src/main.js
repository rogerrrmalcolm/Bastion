import './style.css'
import * as THREE from 'three'

const app = document.querySelector('#app')

const scene = new THREE.Scene()
scene.background = new THREE.Color(0x06070a)

const camera = new THREE.PerspectiveCamera(
  45,
  window.innerWidth / window.innerHeight,
  0.1,
  100,
)
camera.position.set(0, 0, 6)

const renderer = new THREE.WebGLRenderer({ antialias: true })
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
renderer.setSize(window.innerWidth, window.innerHeight)
app.appendChild(renderer.domElement)

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight
  camera.updateProjectionMatrix()
  renderer.setSize(window.innerWidth, window.innerHeight)
})

function animate() {
  renderer.render(scene, camera)
  requestAnimationFrame(animate)
}

animate()

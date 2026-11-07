import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { HologramState } from '../../types';

interface MatrixHologramProps {
  state: HologramState;
  size?: number;
  className?: string;
}

export const MatrixHologram: React.FC<MatrixHologramProps> = ({
  state,
  size = 280,
  className = '',
}) => {
  const mountRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    // 1. Scene, Camera, Renderer
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 1000);
    camera.position.z = 4.2;

    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
      powerPreference: 'low-power',
    });
    renderer.setSize(size, size);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.innerHTML = '';
    container.appendChild(renderer.domElement);

    // 2. Holographic State Colors
    const getColors = (s: HologramState) => {
      switch (s) {
        case 'listening':
          return { primary: 0x00ff9d, secondary: 0x00f0ff, speed: 1.8 };
        case 'thinking':
          return { primary: 0x9933ff, secondary: 0x00f0ff, speed: 2.5 };
        case 'speaking':
          return { primary: 0x00f0ff, secondary: 0x0066ff, speed: 2.0 };
        case 'executing':
          return { primary: 0xffb800, secondary: 0xff3366, speed: 2.2 };
        case 'error':
          return { primary: 0xff3366, secondary: 0x880022, speed: 0.8 };
        case 'offline':
          return { primary: 0x445566, secondary: 0x223344, speed: 0.3 };
        case 'idle':
        default:
          return { primary: 0x00f0ff, secondary: 0x0066ff, speed: 1.0 };
      }
    };

    const colorConfig = getColors(state);

    // 3. Central Core Particle Sphere
    const particleCount = 600;
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(particleCount * 3);
    const originalPositions = new Float32Array(particleCount * 3);

    for (let i = 0; i < particleCount; i++) {
      const u = Math.random();
      const v = Math.random();
      const theta = u * 2.0 * Math.PI;
      const phi = Math.acos(2.0 * v - 1.0);
      const r = 1.0 + (Math.random() - 0.5) * 0.15;

      const x = r * Math.sin(phi) * Math.cos(theta);
      const y = r * Math.sin(phi) * Math.sin(theta);
      const z = r * Math.cos(phi);

      positions[i * 3] = x;
      positions[i * 3 + 1] = y;
      positions[i * 3 + 2] = z;

      originalPositions[i * 3] = x;
      originalPositions[i * 3 + 1] = y;
      originalPositions[i * 3 + 2] = z;
    }

    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));

    const particleMaterial = new THREE.PointsMaterial({
      color: colorConfig.primary,
      size: 0.045,
      transparent: true,
      opacity: 0.85,
      blending: THREE.AdditiveBlending,
    });

    const particles = new THREE.Points(geometry, particleMaterial);
    scene.add(particles);

    // 4. Orbital Hologram Concentric Rings
    const createRing = (radius: number, color: number, tiltX: number, tiltY: number) => {
      const ringGeo = new THREE.TorusGeometry(radius, 0.012, 8, 80);
      const ringMat = new THREE.MeshBasicMaterial({
        color,
        transparent: true,
        opacity: 0.45,
        wireframe: true,
      });
      const ring = new THREE.Mesh(ringGeo, ringMat);
      ring.rotation.x = tiltX;
      ring.rotation.y = tiltY;
      return ring;
    };

    const ring1 = createRing(1.4, colorConfig.secondary, Math.PI / 4, 0);
    const ring2 = createRing(1.65, colorConfig.primary, -Math.PI / 3, Math.PI / 6);
    const ring3 = createRing(1.9, colorConfig.secondary, Math.PI / 6, -Math.PI / 4);

    scene.add(ring1);
    scene.add(ring2);
    scene.add(ring3);

    // 5. Animation Loop
    let animationFrameId: number;
    let clock = new THREE.Clock();

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      const elapsedTime = clock.getElapsedTime() * colorConfig.speed;

      // Rotate core & rings
      particles.rotation.y = elapsedTime * 0.35;
      particles.rotation.x = elapsedTime * 0.15;

      ring1.rotation.z = elapsedTime * 0.4;
      ring2.rotation.z = -elapsedTime * 0.5;
      ring3.rotation.y = elapsedTime * 0.3;

      // Audio undulating pulse wave simulation on particles
      const posAttr = geometry.attributes.position as THREE.BufferAttribute;
      const array = posAttr.array as Float32Array;

      for (let i = 0; i < particleCount; i++) {
        const ox = originalPositions[i * 3];
        const oy = originalPositions[i * 3 + 1];
        const oz = originalPositions[i * 3 + 2];

        const wave = Math.sin(elapsedTime * 3 + ox * 4 + oy * 4) * 0.06;
        array[i * 3] = ox * (1 + wave);
        array[i * 3 + 1] = oy * (1 + wave);
        array[i * 3 + 2] = oz * (1 + wave);
      }
      posAttr.needsUpdate = true;

      renderer.render(scene, camera);
    };

    animate();

    // 6. Cleanup
    return () => {
      cancelAnimationFrame(animationFrameId);
      renderer.dispose();
      geometry.dispose();
      particleMaterial.dispose();
      ring1.geometry.dispose();
      ring2.geometry.dispose();
      ring3.geometry.dispose();
      container.innerHTML = '';
    };
  }, [state, size]);

  return (
    <div className={`relative flex items-center justify-center ${className}`}>
      {/* Outer ambient glow halo */}
      <div
        className="absolute rounded-full pointer-events-none filter blur-xl transition-all duration-700"
        style={{
          width: size * 0.85,
          height: size * 0.85,
          background:
            state === 'error'
              ? 'radial-gradient(circle, rgba(255,51,102,0.2) 0%, transparent 70%)'
              : state === 'listening'
              ? 'radial-gradient(circle, rgba(0,255,157,0.25) 0%, transparent 70%)'
              : state === 'thinking'
              ? 'radial-gradient(circle, rgba(153,51,255,0.25) 0%, transparent 70%)'
              : 'radial-gradient(circle, rgba(0,240,255,0.22) 0%, transparent 70%)',
        }}
      />
      <div ref={mountRef} className="relative z-10" />
      {/* State Badge */}
      <div className="absolute -bottom-2 z-20 flex items-center gap-1.5 px-3 py-1 rounded-full bg-matrix-card/80 border border-matrix-cyan/30 backdrop-blur-md">
        <span
          className={`w-2 h-2 rounded-full ${
            state === 'error'
              ? 'bg-matrix-red animate-ping'
              : state === 'listening'
              ? 'bg-matrix-green animate-pulse'
              : state === 'thinking'
              ? 'bg-purple-400 animate-pulse'
              : state === 'offline'
              ? 'bg-slate-500'
              : 'bg-matrix-cyan animate-pulse'
          }`}
        />
        <span className="text-[11px] font-mono tracking-wider uppercase text-slate-300">
          CORE: {state}
        </span>
      </div>
    </div>
  );
};

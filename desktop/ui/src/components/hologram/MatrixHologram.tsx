import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { HologramState } from '../../types';

interface MatrixHologramProps {
  state: HologramState;
  size?: number;
  className?: string;
  onClick?: () => void;
}

export const MatrixHologram: React.FC<MatrixHologramProps> = ({
  state,
  size = 460,
  className = '',
  onClick,
}) => {
  const mountRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    // 1. Scene, Camera, Renderer
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 1000);
    camera.position.z = 4.3;

    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
      powerPreference: 'low-power',
    });
    renderer.setSize(size, size);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.innerHTML = '';
    container.appendChild(renderer.domElement);

    // 2. Holographic State Colors & Dynamics
    const getStateConfig = (s: HologramState) => {
      switch (s) {
        case 'wake_word':
          return { primary: 0x00ffff, secondary: 0x38bdf8, speed: 3.2, pulseIntensity: 0.22, coreGlow: 0x00f0ff };
        case 'listening':
          return { primary: 0x00ff9d, secondary: 0x00f0ff, speed: 2.2, pulseIntensity: 0.18, coreGlow: 0x00ff9d };
        case 'thinking':
          return { primary: 0xa855f7, secondary: 0x38bdf8, speed: 2.8, pulseIntensity: 0.15, coreGlow: 0x9333ea };
        case 'processing':
          return { primary: 0x3b82f6, secondary: 0x06b6d4, speed: 3.0, pulseIntensity: 0.16, coreGlow: 0x2563eb };
        case 'executing':
          return { primary: 0xf59e0b, secondary: 0x06b6d4, speed: 2.4, pulseIntensity: 0.14, coreGlow: 0xd97706 };
        case 'speaking':
          return { primary: 0x00f0ff, secondary: 0x2563eb, speed: 2.5, pulseIntensity: 0.24, coreGlow: 0x00e5ff };
        case 'interrupted':
          return { primary: 0xf43f5e, secondary: 0xfbbf24, speed: 3.5, pulseIntensity: 0.25, coreGlow: 0xe11d48 };
        case 'error':
          return { primary: 0xef4444, secondary: 0x991b1b, speed: 0.9, pulseIntensity: 0.08, coreGlow: 0xb91c1c };
        case 'offline':
          return { primary: 0x475569, secondary: 0x1e293b, speed: 0.3, pulseIntensity: 0.02, coreGlow: 0x334155 };
        case 'idle':
        default:
          return { primary: 0x00f0ff, secondary: 0x0284c7, speed: 1.0, pulseIntensity: 0.08, coreGlow: 0x00b4d8 };
      }
    };

    const config = getStateConfig(state);

    // 3. Central Core Particle Cloud (1000 particles)
    const particleCount = size > 350 ? 1000 : 600;
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(particleCount * 3);
    const originalPositions = new Float32Array(particleCount * 3);

    for (let i = 0; i < particleCount; i++) {
      const u = Math.random();
      const v = Math.random();
      const theta = u * 2.0 * Math.PI;
      const phi = Math.acos(2.0 * v - 1.0);
      const r = 1.0 + (Math.random() - 0.5) * 0.2;

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
      color: config.primary,
      size: size > 350 ? 0.048 : 0.040,
      transparent: true,
      opacity: 0.9,
      blending: THREE.AdditiveBlending,
    });

    const particles = new THREE.Points(geometry, particleMaterial);
    scene.add(particles);

    // 4. Inner Luminous Core (Geometric Wireframe Sphere)
    const innerGeo = new THREE.IcosahedronGeometry(0.55, 2);
    const innerMat = new THREE.MeshBasicMaterial({
      color: config.coreGlow,
      wireframe: true,
      transparent: true,
      opacity: 0.35,
    });
    const innerCore = new THREE.Mesh(innerGeo, innerMat);
    scene.add(innerCore);

    // 5. Gyroscopic Hologram Rings
    const createRing = (radius: number, tubeRadius: number, color: number, tiltX: number, tiltY: number) => {
      const ringGeo = new THREE.TorusGeometry(radius, tubeRadius, 8, 96);
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

    const ring1 = createRing(1.35, 0.012, config.secondary, Math.PI / 4, 0);
    const ring2 = createRing(1.60, 0.010, config.primary, -Math.PI / 3, Math.PI / 6);
    const ring3 = createRing(1.85, 0.014, config.secondary, Math.PI / 6, -Math.PI / 4);
    const ring4 = createRing(2.10, 0.008, config.primary, Math.PI / 2, Math.PI / 8);

    scene.add(ring1);
    scene.add(ring2);
    scene.add(ring3);
    scene.add(ring4);

    // 6. Ambient Floating Dust Particles (External Field)
    const dustCount = 120;
    const dustGeo = new THREE.BufferGeometry();
    const dustPos = new Float32Array(dustCount * 3);
    for (let i = 0; i < dustCount; i++) {
      dustPos[i * 3] = (Math.random() - 0.5) * 5.0;
      dustPos[i * 3 + 1] = (Math.random() - 0.5) * 5.0;
      dustPos[i * 3 + 2] = (Math.random() - 0.5) * 3.0;
    }
    dustGeo.setAttribute('position', new THREE.BufferAttribute(dustPos, 3));
    const dustMat = new THREE.PointsMaterial({
      color: config.secondary,
      size: 0.025,
      transparent: true,
      opacity: 0.4,
      blending: THREE.AdditiveBlending,
    });
    const dust = new THREE.Points(dustGeo, dustMat);
    scene.add(dust);

    // 7. Dynamic Animation Loop
    let animationFrameId: number;
    const clock = new THREE.Clock();

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      const elapsedTime = clock.getElapsedTime() * config.speed;

      // Rotations
      particles.rotation.y = elapsedTime * 0.35;
      particles.rotation.x = elapsedTime * 0.15;
      innerCore.rotation.y = -elapsedTime * 0.45;
      innerCore.rotation.z = elapsedTime * 0.25;

      ring1.rotation.z = elapsedTime * 0.45;
      ring2.rotation.z = -elapsedTime * 0.55;
      ring3.rotation.y = elapsedTime * 0.35;
      ring4.rotation.x = -elapsedTime * 0.25;

      dust.rotation.y = elapsedTime * 0.08;

      // Particle pulse wave & breathing dynamics
      const posAttr = geometry.attributes.position as THREE.BufferAttribute;
      const array = posAttr.array as Float32Array;
      const intensity = config.pulseIntensity;

      for (let i = 0; i < particleCount; i++) {
        const ox = originalPositions[i * 3];
        const oy = originalPositions[i * 3 + 1];
        const oz = originalPositions[i * 3 + 2];

        let wave = 0;
        if (state === 'speaking') {
          // Undulating acoustic wave
          wave = (Math.sin(elapsedTime * 6.0 + ox * 5.0) + Math.cos(elapsedTime * 4.0 + oy * 5.0)) * 0.5 * intensity;
        } else if (state === 'listening') {
          // Expanding radar pulse
          wave = Math.sin(elapsedTime * 5.0 - (ox * ox + oy * oy) * 3.0) * intensity;
        } else if (state === 'thinking' || state === 'processing') {
          // Inward swirling vortex
          wave = Math.sin(elapsedTime * 4.0 + oz * 6.0) * intensity;
        } else {
          // Serene breathing pulse
          wave = Math.sin(elapsedTime * 2.2 + ox * 3.0 + oy * 3.0) * intensity;
        }

        array[i * 3] = ox * (1 + wave);
        array[i * 3 + 1] = oy * (1 + wave);
        array[i * 3 + 2] = oz * (1 + wave);
      }
      posAttr.needsUpdate = true;

      // Pulse inner core scale
      const coreScale = 1.0 + Math.sin(elapsedTime * 3.0) * (intensity * 0.8);
      innerCore.scale.set(coreScale, coreScale, coreScale);

      renderer.render(scene, camera);
    };

    animate();

    return () => {
      cancelAnimationFrame(animationFrameId);
      renderer.dispose();
      geometry.dispose();
      particleMaterial.dispose();
      innerGeo.dispose();
      innerMat.dispose();
      dustGeo.dispose();
      dustMat.dispose();
    };
  }, [state, size]);

  return (
    <div
      ref={mountRef}
      onClick={onClick}
      className={`relative flex items-center justify-center cursor-pointer select-none transition-transform duration-500 hover:scale-[1.02] ${className}`}
      style={{ width: size, height: size }}
      title={`MATRIX Core Hologram — State: ${state.toUpperCase()}`}
    />
  );
};

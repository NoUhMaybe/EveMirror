import { useEffect, useRef, useState } from "react";
import {
  AdditiveBlending,
  Color,
  IcosahedronGeometry,
  LineBasicMaterial,
  LineSegments,
  PerspectiveCamera,
  Points,
  Scene,
  ShaderMaterial,
  WebGLRenderer,
  WireframeGeometry,
} from "three";
import { StaticOrb, type OrbProps } from "../components/AssistantOrb";

/** All vertex deformation is on the GPU. Geometry/material allocations happen once. */
export default function OrbGL(props: OrbProps) {
  const container = useRef<HTMLDivElement>(null);
  const latest = useRef(props);
  latest.current = props;
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    if (!container.current) return;
    const target = container.current;
    let renderer: WebGLRenderer;
    try {
      renderer = new WebGLRenderer({
        alpha: true,
        antialias: props.quality === "high",
        powerPreference: "low-power",
      });
    } catch {
      setFailed(true);
      return;
    }
    const scene = new Scene();
    const camera = new PerspectiveCamera(38, 1, 0.1, 20);
    camera.position.z = 4.8;
    const geometry = new IcosahedronGeometry(
      1.12,
      props.quality === "low" ? 2 : props.quality === "high" ? 4 : 3,
    );
    const material = new ShaderMaterial({
      transparent: true,
      depthWrite: false,
      blending: AdditiveBlending,
      uniforms: {
        uTime: { value: 0 },
        uLevel: { value: 0.08 },
        uColor: { value: new Color("#a9dfe9") },
        uScale: { value: 1 },
      },
      vertexShader: `uniform float uTime; uniform float uLevel; uniform float uScale; varying float vLight;
        void main(){float wave=sin(position.y*4.0+uTime)*cos(position.x*3.0-uTime*0.6);
        vec3 p=position*(1.0+wave*uLevel*0.12); vec4 mv=modelViewMatrix*vec4(p,1.0);
        vLight=clamp((p.z+1.5)/2.5,0.18,1.0); gl_PointSize=(1.1+vLight*2.0)*uScale;
        gl_Position=projectionMatrix*mv;}`,
      fragmentShader: `uniform vec3 uColor; varying float vLight; void main(){float d=length(gl_PointCoord-0.5);
        if(d>0.5)discard; gl_FragColor=vec4(uColor,vLight*smoothstep(0.5,0.12,d)*0.85);}`,
    });
    const points = new Points(geometry, material);
    const wireGeometry = new WireframeGeometry(geometry);
    const wireMaterial = new LineBasicMaterial({
      color: "#699cba",
      transparent: true,
      opacity: 0.12,
    });
    const wire = new LineSegments(wireGeometry, wireMaterial);
    scene.add(points, wire);
    renderer.setPixelRatio(
      Math.min(
        devicePixelRatio,
        props.quality === "low" ? 1 : props.quality === "high" ? 1.5 : 1.25,
      ),
    );
    renderer.setClearColor(0x000000, 0);
    target.appendChild(renderer.domElement);
    material.uniforms.uScale.value = renderer.getPixelRatio();
    const resize = () => {
      const { width, height } = target.getBoundingClientRect();
      renderer.setSize(width, height, false);
      camera.aspect = width / Math.max(1, height);
      camera.updateProjectionMatrix();
    };
    const observer = new ResizeObserver(resize);
    observer.observe(target);
    resize();
    let timer: ReturnType<typeof setTimeout> | undefined;
    let raf = 0,
      last = 0,
      first = 0,
      measured = 0,
      frames = 0,
      disposed = false;
    const draw = (time: number) => {
      if (disposed || document.hidden) return;
      const p = latest.current;
      const active = !["IDLE", "OFFLINE", "MUTED"].includes(p.phase);
      const fps =
        p.reduced || document.hidden
          ? 1
          : active
            ? p.quality === "high"
              ? 45
              : p.quality === "low"
                ? 15
                : 30
            : 12;

      const dt = last ? time - last : 0;
      last = time;
      if (!document.hidden) {
        material.uniforms.uTime.value = p.reduced ? 0 : time / 1600;
        const energy =
          p.phase === "LISTENING"
            ? Math.min(1, p.level * 8)
            : p.phase === "SPEAKING"
              ? 0.2 + 0.15 * Math.sin(p.progress * Math.PI) ** 2
              : active
                ? 0.18
                : 0.05;
        material.uniforms.uLevel.value = energy * p.intensity;
        material.uniforms.uColor.value.set(
          p.phase === "ALARM"
            ? "#e8bf80"
            : p.phase === "ERROR"
              ? "#e7a0a0"
              : "#a9dfe9",
        );
        if (!p.reduced) {
          points.rotation.y += dt * 0.000045;
          points.rotation.z = Math.sin(time / 16000) * 0.06;
          wire.rotation.copy(points.rotation);
        }
        const scale =
          1 + (p.reduced ? 0 : Math.sin(time / 2100) * 0.012 * p.intensity);
        points.scale.setScalar(scale);
        wire.scale.setScalar(scale);
        renderer.render(scene, camera);
        frames++;
        if (!first) first = time;
        measured += dt;
        if (measured > 2000) {
          latest.current.metrics?.((1000 * frames) / Math.max(1, time - first));
          frames = 0;
          first = time;
          measured = 0;
        }
      }
      timer = setTimeout(() => {
        raf = requestAnimationFrame(draw);
      }, 1000 / fps);
    };
    const visibility = () => {
      clearTimeout(timer);
      cancelAnimationFrame(raf);
      if (!document.hidden) raf = requestAnimationFrame(draw);
    };
    document.addEventListener("visibilitychange", visibility);
    const lost = (event: Event) => {
      event.preventDefault();
      cancelAnimationFrame(raf);
      setFailed(true);
    };
    renderer.domElement.addEventListener("webglcontextlost", lost);
    raf = requestAnimationFrame(draw);
    return () => {
      disposed = true;
      clearTimeout(timer);
      document.removeEventListener("visibilitychange", visibility);
      cancelAnimationFrame(raf);
      observer.disconnect();
      renderer.domElement.removeEventListener("webglcontextlost", lost);
      geometry.dispose();
      wireGeometry.dispose();
      material.dispose();
      wireMaterial.dispose();
      renderer.dispose();
      renderer.domElement.remove();
    };
  }, [props.quality, failed]);
  return failed ? (
    <StaticOrb phase={props.phase} />
  ) : (
    <div className="orb-canvas" ref={container} aria-hidden="true" />
  );
}

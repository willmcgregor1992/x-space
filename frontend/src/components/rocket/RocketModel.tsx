import { Suspense, useEffect, useMemo, useRef, type ReactNode } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, useGLTF } from "@react-three/drei";
import { Group, type Object3D, Vector3 } from "three";
import type { StagePose, StackConfig, VehicleKind } from "./stackState";
import { poseOffset } from "./stackState";

const MODEL_URL: Record<VehicleKind, string> = {
  falcon9: "/models/falcon9.glb",
  falcon_heavy: "/models/falcon_heavy.glb",
  starship: "/models/starship.glb",
};

type Bucket = "left" | "right" | "core" | "upper" | "fairing" | "ship" | "superHeavy";

function classify(name: string): Bucket {
  const n = name.toLowerCase();
  if (n.startsWith("left_")) return "left";
  if (n.startsWith("right_")) return "right";
  if (n.includes("fairing")) return "fairing";
  if (n.startsWith("second_stage")) return "upper";
  if (n.startsWith("ship_")) return "ship";
  if (
    n.startsWith("super_heavy") ||
    n.startsWith("hot_stage") ||
    n.startsWith("booster_") ||
    n.startsWith("raptor_")
  ) {
    return "superHeavy";
  }
  return "core";
}

function groupMeshes(root: Object3D): Record<Bucket, Group> {
  const buckets: Record<Bucket, Group> = {
    left: new Group(),
    right: new Group(),
    core: new Group(),
    upper: new Group(),
    fairing: new Group(),
    ship: new Group(),
    superHeavy: new Group(),
  };
  const meshes: Object3D[] = [];
  root.traverse((obj) => {
    if ((obj as { isMesh?: boolean }).isMesh) meshes.push(obj);
  });
  for (const mesh of meshes) {
    buckets[classify(mesh.name)].attach(mesh);
  }
  return buckets;
}

function LerpGroup({
  target,
  tilt = 0,
  visible = true,
  reducedMotion,
  children,
}: {
  target: [number, number, number];
  tilt?: number;
  visible?: boolean;
  reducedMotion: boolean;
  children: ReactNode;
}) {
  const ref = useRef<Group>(null);
  const goal = useMemo(() => new Vector3(...target), [target]);
  useEffect(() => {
    if (!ref.current || !reducedMotion) return;
    ref.current.position.copy(goal);
    ref.current.rotation.z = tilt;
  }, [goal, reducedMotion, tilt]);
  useFrame((_, delta) => {
    if (!ref.current || reducedMotion) return;
    const k = 1 - Math.exp(-3.2 * delta);
    ref.current.position.lerp(goal, k);
    ref.current.rotation.z += (tilt - ref.current.rotation.z) * k;
  });
  return (
    <group ref={ref} visible={visible}>
      {children}
    </group>
  );
}

function RocketScene({ config, reducedMotion }: { config: StackConfig; reducedMotion: boolean }) {
  const url = MODEL_URL[config.kind];
  const { scene } = useGLTF(url);
  const parts = useMemo(() => groupMeshes(scene.clone(true)), [scene]);
  const left = poseOffset(config.sideBoosters, "left");
  const right = poseOffset(config.sideBoosters, "right");
  const core = poseOffset(config.firstStage, "down");
  const booster = poseOffset(config.superHeavy, "down");
  const falling = (pose: StagePose) => (pose === "separating" ? 0.18 : pose === "away" ? 0.28 : 0);
  return (
    <group>
      <LerpGroup target={left} tilt={falling(config.sideBoosters)} reducedMotion={reducedMotion}>
        <primitive object={parts.left} />
      </LerpGroup>
      <LerpGroup target={right} tilt={-falling(config.sideBoosters)} reducedMotion={reducedMotion}>
        <primitive object={parts.right} />
      </LerpGroup>
      <LerpGroup target={core} tilt={config.firstStage === "attached" ? 0 : 0.14} reducedMotion={reducedMotion}>
        <primitive object={parts.core} />
      </LerpGroup>
      <primitive object={parts.upper} />
      <LerpGroup
        target={[0, 0, 0]}
        visible={config.fairing === "attached"}
        reducedMotion={reducedMotion}
      >
        <primitive object={parts.fairing} />
      </LerpGroup>
      <LerpGroup
        target={booster}
        tilt={config.superHeavy === "attached" ? 0 : 0.12}
        reducedMotion={reducedMotion}
      >
        <primitive object={parts.superHeavy} />
      </LerpGroup>
      <primitive object={parts.ship} />
    </group>
  );
}

function CameraRig({ heightM, reducedMotion }: { heightM: number; reducedMotion: boolean }) {
  const distance = heightM * 1.12;
  return (
    <OrbitControls
      enablePan={false}
      enableZoom
      autoRotate={!reducedMotion}
      autoRotateSpeed={0.45}
      target={[0, heightM * 0.4, 0]}
      minDistance={distance * 0.45}
      maxDistance={distance * 1.8}
      makeDefault
    />
  );
}

export function RocketModel({
  config,
  reducedMotion,
}: {
  config: StackConfig;
  reducedMotion: boolean;
}) {
  const height = config.heightM;
  return (
    <div className="relative h-72 w-full" role="img" aria-label={config.caption}>
      <Canvas
        camera={{
          position: [height * 0.48, height * 0.38, height * 0.88],
          fov: 28,
          near: 0.5,
          far: 800,
        }}
        gl={{ alpha: true, antialias: true }}
        dpr={[1, 1.75]}
      >
        <color attach="background" args={["#07090d"]} />
        <ambientLight intensity={0.55} />
        <directionalLight position={[40, 80, 30]} intensity={1.35} />
        <directionalLight position={[-30, 20, -40]} intensity={0.35} color="#8eb0cc" />
        <Suspense fallback={null}>
          <RocketScene key={config.kind} config={config} reducedMotion={reducedMotion} />
        </Suspense>
        <CameraRig heightM={height} reducedMotion={reducedMotion} />
      </Canvas>
    </div>
  );
}

export function preloadRocket(kind: VehicleKind): void {
  useGLTF.preload(MODEL_URL[kind]);
}

export type { StagePose };

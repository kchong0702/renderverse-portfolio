import { useCallback, useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import { Center, useEnvironment } from "@react-three/drei";
import { useControls } from "leva";
import * as THREE from "three";
import EzbotModel from "@/experience/models/EzbotModel";
import { useSceneStore } from "@/experience/state/sceneStore";
import { useChatStore } from "@/features/ezbot/state/chatStore";
import { useOpenChat } from "@/features/ezbot/hooks/useOpenChat";
import {
  CONNECTION_STATUS,
  useEzbotStatus,
} from "@/features/ezbot/hooks/useEzbotStatus";
import { CONFIG } from "@/app/config";

const WALL_INSET = 0.7;
const ROOM_BOUNDS = {
  minX: -8.7 + WALL_INSET,
  maxX: 7 - WALL_INSET,
  minZ: -7.9 + WALL_INSET,
  maxZ: 6 - WALL_INSET,
};

const MOVING_SPEED = 0.5;
const SIDE_HYSTERESIS = 0.3;
const VIEW_CONE = 35;
const LEASH = 1.5;
const SETTLED = 0.15;
const BOB_SPEED = 2;
const BOB_AMPLITUDE = 0.05;
const MAX_TILT = 0.25;

const forward = new THREE.Vector3();
const left = new THREE.Vector3();
const mirrored = new THREE.Vector3();
const toEzbot = new THREE.Vector3();

const outOfBounds = ({ x, z }: { x: number; z: number }) =>
  Math.max(0, ROOM_BOUNDS.minX - x, x - ROOM_BOUNDS.maxX) +
  Math.max(0, ROOM_BOUNDS.minZ - z, z - ROOM_BOUNDS.maxZ);

const clampToRoom = (point: THREE.Vector3) => {
  point.x = THREE.MathUtils.clamp(point.x, ROOM_BOUNDS.minX, ROOM_BOUNDS.maxX);
  point.z = THREE.MathUtils.clamp(point.z, ROOM_BOUNDS.minZ, ROOM_BOUNDS.maxZ);
};

const smoothingFactor = (lambda: number, delta: number) =>
  1 - Math.exp(-lambda * delta);

const dampAngle = (
  current: number,
  target: number,
  lambda: number,
  delta: number,
) => {
  const diff =
    THREE.MathUtils.euclideanModulo(target - current + Math.PI, Math.PI * 2) -
    Math.PI;
  return current + diff * smoothingFactor(lambda, delta);
};

function EzbotCompanion() {
  const specialIsLocked = useSceneStore((s) => s.specialIsLocked);
  const isReplying = useChatStore((s) => s.isReplying);
  const connectionStatus = useEzbotStatus();
  const openChat = useOpenChat();

  const envMap = useEnvironment({ preset: "dawn" });

  const { distance, angle, belowEye, height, smoothing, brightness } =
    useControls("Ezbot companion", {
      distance: { value: 3.5, min: 1, max: 6, step: 0.1 },
      angle: { value: 25, min: 0, max: 60, step: 1 },
      belowEye: { value: 0.6, min: -1, max: 2, step: 0.05 },
      height: { value: 0.7, min: 0.3, max: 3, step: 0.05 },
      smoothing: { value: 4, min: 0.5, max: 12, step: 0.5 },
      brightness: { value: 1, min: 0, max: 3, step: 0.05 },
    });

  const body = useRef<THREE.Group>(null);
  const lean = useRef<THREE.Group>(null);
  const goal = useRef(new THREE.Vector3());
  const side = useRef(1);
  const isFlying = useRef(true);
  const isPlaced = useRef(false);

  const [modelHeight, setModelHeight] = useState(1);
  const [isHovered, setHovered] = useState(false);

  const handleCentered = useCallback(
    ({ height: measured }: { height: number }) => setModelHeight(measured),
    [],
  );

  const isFollowing = specialIsLocked !== false;
  const mode = isReplying ? "thinking" : "idle";

  useFrame(({ camera, clock }, delta) => {
    if (!body.current || !lean.current || delta <= 0) return;
    const { position, rotation } = body.current;

    if (isFollowing) {
      camera.getWorldDirection(forward).setY(0);

      if (forward.lengthSq() > 1e-6) {
        forward.normalize();
        toEzbot.subVectors(position, camera.position).setY(0);
        if (
          THREE.MathUtils.radToDeg(forward.angleTo(toEzbot)) > VIEW_CONE ||
          Math.abs(toEzbot.length() - distance) > LEASH
        )
          isFlying.current = true;
      }

      if (isFlying.current && forward.lengthSq() > 1e-6) {
        left.set(forward.z, 0, -forward.x);

        const radians = THREE.MathUtils.degToRad(angle);
        const ahead = Math.cos(radians) * distance;
        const aside = Math.sin(radians) * distance * side.current;

        goal.current
          .copy(camera.position)
          .addScaledVector(forward, ahead)
          .addScaledVector(left, aside);
        mirrored
          .copy(camera.position)
          .addScaledVector(forward, ahead)
          .addScaledVector(left, -aside);

        if (
          outOfBounds(mirrored) + SIDE_HYSTERESIS <
          outOfBounds(goal.current)
        ) {
          side.current *= -1;
          goal.current.copy(mirrored);
        }

        clampToRoom(goal.current);
      }

      goal.current.y = camera.position.y - belowEye;
    }

    if (!isPlaced.current) {
      position.copy(goal.current);
      isPlaced.current = true;
    }

    const previousX = position.x;
    const previousZ = position.z;
    position.lerp(goal.current, smoothingFactor(smoothing, delta));
    if (position.distanceTo(goal.current) < SETTLED) isFlying.current = false;

    const dx = position.x - previousX;
    const dz = position.z - previousZ;
    const speed = Math.hypot(dx, dz) / delta;

    const heading =
      speed > MOVING_SPEED
        ? Math.atan2(dx, dz)
        : Math.atan2(
            camera.position.x - position.x,
            camera.position.z - position.z,
          );
    rotation.y = dampAngle(rotation.y, heading, smoothing * 1.5, delta);

    lean.current.rotation.x = THREE.MathUtils.damp(
      lean.current.rotation.x,
      Math.min(speed * 0.04, MAX_TILT),
      smoothing,
      delta,
    );
    lean.current.position.y =
      Math.sin(clock.elapsedTime * BOB_SPEED) * BOB_AMPLITUDE * height;
  });

  return (
    <group ref={body}>
      <group
        ref={lean}
        onPointerEnter={(event) => {
          event.stopPropagation();
          setHovered(true);
        }}
        onPointerLeave={() => setHovered(false)}
        onClick={(event) => {
          event.stopPropagation();
          openChat();
        }}
      >
        <group scale={height / modelHeight}>
          <Center onCentered={handleCentered}>
            <EzbotModel
              isActive={connectionStatus === CONNECTION_STATUS.ONLINE}
              neutralWhenInactive
              isHovered={isHovered && CONFIG.isChatbotEnabled}
              mode={mode}
              envMap={envMap}
              envMapIntensity={brightness}
            />
          </Center>
        </group>
      </group>
    </group>
  );
}

export default EzbotCompanion;

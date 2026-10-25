import * as THREE from "three";
import { useEffect, useRef, type RefObject } from "react";
import { useFrame } from "@react-three/fiber";

const LOOK_PLANE_DEPTH = 0.6;
const MAX_HEAD_YAW = 0.7;
const MAX_HEAD_PITCH = 0.45;
const HEAD_SMOOTHING = 8;

const pointerNdc = new THREE.Vector2();
const raycaster = new THREE.Raycaster();
const lookPlane = new THREE.Plane();
const headWorld = new THREE.Vector3();
const toCamera = new THREE.Vector3();
const lookTarget = new THREE.Vector3();

export const useHeadFollowsPointer = (
  head: RefObject<THREE.Object3D | null>,
) => {
  const pointer = useRef<{ x: number; y: number } | null>(null);

  useEffect(() => {
    const onMove = (event: PointerEvent) => {
      pointer.current = { x: event.clientX, y: event.clientY };
    };
    const onLeave = (event: PointerEvent) => {
      if (!event.relatedTarget) pointer.current = null;
    };
    window.addEventListener("pointermove", onMove);
    document.addEventListener("pointerout", onLeave);
    return () => {
      window.removeEventListener("pointermove", onMove);
      document.removeEventListener("pointerout", onLeave);
      pointer.current = null;
    };
  }, []);

  useFrame(({ camera, gl }, delta) => {
    const headGroup = head.current;
    if (!headGroup?.parent) return;
    let yaw = 0;
    let pitch = 0;
    if (pointer.current) {
      const rect = gl.domElement.getBoundingClientRect();
      pointerNdc.set(
        ((pointer.current.x - rect.left) / rect.width) * 2 - 1,
        -((pointer.current.y - rect.top) / rect.height) * 2 + 1,
      );
      raycaster.setFromCamera(pointerNdc, camera);
      headGroup.getWorldPosition(headWorld);
      toCamera.subVectors(camera.position, headWorld);
      lookTarget.copy(headWorld).addScaledVector(toCamera, LOOK_PLANE_DEPTH);
      lookPlane.setFromNormalAndCoplanarPoint(toCamera.normalize(), lookTarget);
      if (raycaster.ray.intersectPlane(lookPlane, lookTarget)) {
        headGroup.parent.worldToLocal(lookTarget).sub(headGroup.position);
        yaw = THREE.MathUtils.clamp(
          Math.atan2(lookTarget.x, lookTarget.z),
          -MAX_HEAD_YAW,
          MAX_HEAD_YAW,
        );
        pitch = THREE.MathUtils.clamp(
          -Math.atan2(lookTarget.y, Math.hypot(lookTarget.x, lookTarget.z)),
          -MAX_HEAD_PITCH,
          MAX_HEAD_PITCH,
        );
      }
    }
    // Ease toward the cursor, or back to rest when it leaves the page
    const t = 1 - Math.exp(-HEAD_SMOOTHING * delta);
    headGroup.rotation.y += (yaw - headGroup.rotation.y) * t;
    headGroup.rotation.x += (pitch - headGroup.rotation.x) * t;
  });
};

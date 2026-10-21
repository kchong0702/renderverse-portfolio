import CameraControls from "camera-controls";
import * as THREE from "three";
import { useThree, useFrame } from "@react-three/fiber";
import { useMemo } from "react";
import type { Vec3 } from "@/experience/state/sceneStore";

CameraControls.install({ THREE });

interface CameraControllerProps {
  focus: Vec3;
  loc?: Vec3;
  pos?: THREE.Vector3;
  look?: THREE.Vector3;
  zoom?: number;
}

export default function CameraController({
  focus,
  loc,
  pos = new THREE.Vector3(0, 0, 0),
  look = new THREE.Vector3(),
  zoom,
}: CameraControllerProps) {
  const camera = useThree((state) => state.camera);
  if (zoom) camera.zoom = zoom;
  const gl = useThree((state) => state.gl);
  const controls = useMemo(
    () => new CameraControls(camera, gl.domElement),
    [camera, gl.domElement],
  );

  useFrame((state, delta) => {
    look.set(focus.x, focus.y, focus.z);
    if (loc) pos.set(loc.x, loc.y, loc.z);

    // Interpolate position
    state.camera.position.lerp(pos, 0.5);

    state.camera.updateProjectionMatrix();

    controls.setLookAt(
      state.camera.position.x,
      state.camera.position.y,
      state.camera.position.z,
      look.x,
      look.y,
      look.z,
      true,
    );
    controls.update(delta);
  });

  return null;
}

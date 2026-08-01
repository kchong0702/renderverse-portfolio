import { useControls } from "leva";
import { useRef } from "react";
import { useHelper } from "@react-three/drei";
import * as THREE from "three";

function Lighting() {
  const { position1, rotation1 } = useControls("light", {
    position1: {
      value: {
        x: 6,
        y: 18,
        z: -15,
      },
      joystick: "invertY",
    },
    rotation1: {
      x: 0,
      y: 0,
      z: 0,
    },
  });

  const light = useRef();
  useHelper(light, THREE.PointLightHelper, 1);

  return (
    <>
      <ambientLight
        position={[5, 16, -19]}
        rotation={[rotation1.x, rotation1.y, rotation1.z]}
        args={["white", 1]}
      />
      <pointLight
        args={["red", 8, 2]}
        position={[3, 18, -23]}
        rotation={[rotation1.x, rotation1.y, rotation1.z]}
      />
      <rectAreaLight
        position={[position1.x, position1.y, position1.z]}
        rotation={[rotation1.x, rotation1.y, rotation1.z]}
        intensity={1.5}
        width={10}
        height={10}
        color={"yellow"}
      />
    </>
  );
}

export default Lighting;

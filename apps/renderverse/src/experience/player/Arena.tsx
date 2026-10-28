import { useControls } from "leva";
import { RigidBody, CuboidCollider } from "@react-three/rapier";

function Arena() {
  const { position, rotation, dimension } = useControls("Arena", {
    position: {
      value: {
        x: -8.7,
        y: 3.5,
        z: 0.1,
      },
      joystick: "invertY",
    },
    rotation: {
      value: {
        x: 0,
        y: Math.PI / 2,
        z: 0,
      },
    },
    dimension: {
      value: {
        x: 8,
        y: 3.8,
        z: 0.2,
      },
    },
  });
  return (
    <RigidBody type="fixed">
      <CuboidCollider
        name="floor"
        args={[8.41, 7.75, 0.2]}
        position={[-0.1, -0.1, 0.1]}
        rotation={[-Math.PI / 2, 0, 0]}
      ></CuboidCollider>
      <CuboidCollider
        name="front"
        args={[8.4, 3.8, 0.2]}
        position={[-0.1, 3.5, 6]} // 8
        rotation={[0, 0, 0]}
      ></CuboidCollider>
      <CuboidCollider
        name="back"
        args={[8.4, 3.8, 0.2]}
        position={[-0.1, 3.5, -7.9]}
        rotation={[0, 0, 0]}
      ></CuboidCollider>
      <CuboidCollider
        name="left"
        args={[dimension.x, dimension.y, dimension.z]}
        position={[7, 3.5, 0.15]} // x = 8.3
        rotation={[rotation.x, rotation.y, rotation.z]}
      ></CuboidCollider>
      <CuboidCollider
        name="right"
        args={[dimension.x, dimension.y, dimension.z]}
        position={[position.x, position.y, position.z]}
        rotation={[rotation.x, rotation.y, rotation.z]}
      ></CuboidCollider>
    </RigidBody>
  );
}

export default Arena;

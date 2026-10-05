import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { RigidBody } from "@react-three/rapier";
import * as THREE from "three";
import { usePersonControls } from "../../hooks/usePersonControls.js";
import PropTypes from "prop-types";

const MOVE_SPEED = 5;
const direction = new THREE.Vector3();
const frontVector = new THREE.Vector3();
const sideVector = new THREE.Vector3();

function Person({ pointerState }) {
  const playerRef = useRef();
  const { forward, backward, left, right } = usePersonControls();
  useFrame((state) => {
    if (!playerRef.current || pointerState.specialIsLocked === false) return;
    /**
     * linear velocity - rate of change of position of an
     * object in a straight line path
     */
    const velocity = playerRef.current.linvel();
    frontVector.set(0, 0, backward - forward);
    sideVector.set(left - right, 0, 0);
    direction
      .subVectors(frontVector, sideVector) // subtract (combined movement direction vector)
      .normalize() // ensure magnitude is 1
      .multiplyScalar(MOVE_SPEED) // final movement amount per frame
      .applyEuler(state.camera.rotation); // camera trajectory
    playerRef.current.wakeUp(); // wake up physics body
    playerRef.current.setLinvel({
      x: direction.x,
      y: velocity.y,
      z: direction.z,
    });

    // camera to person
    const { x, y, z } = playerRef.current.translation();
    state.camera.position.set(x, y + 2.5, z);
  });

  return (
    <RigidBody position={[2.1, 4, -6]} ref={playerRef}>
      <mesh>
        <capsuleGeometry args={[1, 1]} />
        <meshBasicMaterial transparent opacity={0} />
      </mesh>
    </RigidBody>
  );
}

Person.propTypes = {
  pointerState: PropTypes.object,
};

export default Person;

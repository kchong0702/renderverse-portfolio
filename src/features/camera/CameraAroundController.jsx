import * as THREE from "three";
import { useFrame } from "@react-three/fiber";
import { useThree } from "@react-three/fiber";

export default function CameraAroundController() {
  const camera = useThree((state) => state.camera);
  const look = new THREE.Vector3(4.4, 17, -22.128);
  const animations = [
    {
      id: "rotate",
      rad: 3.5,
      duration: 12,
      down: 0.01,
      radianlim: 3.13,
      cycle: 2, // cycle before going down
      ylim: 17,
      lookdown: 2,
    },
    // {
    //   id: "transition",
    //   duration: 15,
    //   speed: { x: 0.15, y: -0.1, z: 0.3 },
    //   axis: ["x", "y", "z"],
    //   limit: { x: 5, y: 16, z: -12 },
    //   delay: 2000,
    //   sign: { x: "+", y: "-", z: "+" },
    // },
  ];

  let counter = 0;
  let animFlag = animations[counter];
  let cycle = 0;
  const animLen = animations.length;
  const defLook = look.clone();
  const defCamera = camera.position.clone();

  return useFrame((state) => {
    const { clock } = state;

    if (animFlag.id === "rotate") {
      const angularVelocity = (2 * Math.PI) / animFlag.duration;
      const theta = clock.elapsedTime * angularVelocity;

      const pos = new THREE.Vector3();
      pos.x = animFlag.rad * Math.sin(theta);
      pos.z = animFlag.rad * Math.cos(theta);
      pos.y = animFlag.lookdown;

      const rad = Math.atan2(pos.z, pos.x); // quadrant

      if (rad > animFlag.radianlim) {
        cycle = cycle + 1;
      }

      if (cycle >= animFlag.cycle + 1) {
        look.y = look.y - animFlag.down / animFlag.duration;
      }

      if (look.y < animFlag.ylim && rad > animFlag.radianlim) {
        cycle = 0;
        counter = counter + 1;
        if (counter >= animLen) {
          counter = 0;
          look.set(defLook.x, defLook.y, defLook.z);
          state.camera.position.set(defCamera.x, defCamera.y, defCamera.z);
        }
        animFlag = animations[counter];
      }

      state.camera.position.copy(look).add(pos);

      state.camera.lookAt(look);
    }

    if (animFlag.id === "transition") {
      let flag = true;
      animFlag.axis.forEach((a) => {
        // look[a] += animFlag.speed / animFlag.duration;
        if (
          animFlag.sign[a] === "+" &&
          state.camera.position[a] >= animFlag.limit[a]
        ) {
          flag = true;
        } else if (
          animFlag.sign[a] === "-" &&
          state.camera.position[a] <= animFlag.limit[a]
        ) {
          flag = true;
        } else {
          state.camera.position[a] += animFlag.speed[a] / animFlag.duration;
          flag = false;
        }
      });

      state.camera.lookAt(look);

      if (flag) {
        counter = counter + 1;
        if (counter >= animLen) {
          counter = 0;
          look.set(defLook.x, defLook.y, defLook.z);
          state.camera.position.set(defCamera.x, defCamera.y, defCamera.z);
        }
        animFlag = animations[counter];
      }
    }

    state.camera.updateProjectionMatrix();
  });
}

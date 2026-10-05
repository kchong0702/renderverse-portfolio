import { useRef } from "react";
import * as THREE from "three";
import { PerspectiveCamera, useHelper } from "@react-three/drei";
import { useControls } from "leva";
import PropTypes from "prop-types";

function CustomCamera({ settings }) {
  const ref = useRef();
  const { fov, near, far, position, rotation } = useControls("Camera", {
    fov: {
      value: 55,
      step: 1,
    },
    near: {
      value: 0.1,
      step: 0.01,
    },
    far: {
      value: 100,
      step: 0.01,
    },
    position: {
      value: {
        x: 4.3,
        y: 18.5,
        z: -24.6,
      },
      step: 0.01,
      joystick: "invertY",
    },
    rotation: {
      value: {
        x: 0.4,
        y: Math.PI,
        z: 0,
      },
    },
  });

  useHelper(true, ref, THREE.CameraHelper);
  // useHelper(ref, THREE.CameraHelper);

  return (
    <>
      {settings.makeDef ? (
        <PerspectiveCamera
          ref={ref}
          fov={settings.fov ? settings.fov : fov}
          near={settings.near ? settings.near : near}
          far={settings.far ? settings.far : far}
          zoom={settings.zoom ? settings.zoom : 1}
          position={
            settings.position
              ? [
                  settings.position[0],
                  settings.position[1],
                  settings.position[2],
                ]
              : [position.x, position.y, position.z]
          }
          rotation={
            settings.rotation
              ? [
                  settings.rotation[0],
                  settings.rotation[1],
                  settings.rotation[2],
                ]
              : [rotation.x, rotation.y, rotation.z]
          }
          makeDefault
        ></PerspectiveCamera>
      ) : (
        <PerspectiveCamera
          ref={ref}
          fov={settings.fov ? settings.fov : fov}
          near={settings.near ? settings.near : near}
          far={settings.far ? settings.far : far}
          zoom={settings.zoom ? settings.zoom : 1}
          position={
            settings.position
              ? [
                  settings.position[0],
                  settings.position[1],
                  settings.position[2],
                ]
              : [position.x, position.y, position.z]
          }
          rotation={
            settings.rotation
              ? [
                  settings.rotation[0],
                  settings.rotation[1],
                  settings.rotation[2],
                ]
              : [rotation.x, rotation.y, rotation.z]
          }
        ></PerspectiveCamera>
      )}
    </>
  );
}

CustomCamera.propTypes = {
  settings: PropTypes.shape({
    fov: PropTypes.number,
    near: PropTypes.number,
    far: PropTypes.number,
    zoom: PropTypes.number,
    position: PropTypes.array,
    rotation: PropTypes.array,
    makeDef: PropTypes.bool,
  }),
};

export default CustomCamera;

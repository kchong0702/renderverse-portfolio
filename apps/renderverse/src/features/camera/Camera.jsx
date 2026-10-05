import PropTypes from "prop-types";
import CustomCamera from "./CustomCamera";
import CameraController from "./CameraController";
import { PointerLockControls, OrbitControls } from "@react-three/drei";
import { useRef, useEffect } from "react";
import CameraAroundController from "./CameraAroundController";

export default function Camera({ state, fpv }) {
  const control = useRef();

  useEffect(() => {
    const projele = document.getElementById("viewindicator");
    const contactele = document.getElementById("contactindicator");
    if (state.specialIsLocked === true) {
      if (projele) projele.style.display = "flex";
      if (contactele) contactele.style.display = "flex";
      if (control.current) control.current.lock();
    } else if (state.specialIsLocked === false) {
      if (projele) projele.style.display = "none";
      if (contactele) contactele.style.display = "none";
      if (control.current) {
        control.current.unlock();
      } else {
        document.exitPointerLock();
      }
    }
  }, [state.specialIsLocked]);

  // useEffect(() => {
  //   const ele = document.getElementById("viewindicator");
  //   if (state.cooldown) {
  //     if (ele) ele.style.display = "none";
  //   } else if (!state.cooldown) {
  //     if (state.specialIsLocked === true || state.specialIsLocked === null) {
  //       if (ele) ele.style.display = "flex";
  //     } else if (state.specialIsLocked === false) {
  //       if (ele) ele.style.display = "none";
  //     }
  //   }
  // }, [state.cooldown, state.specialIsLocked]);

  return (
    <>
      {fpv ? (
        !state.isTLocked ? (
          <PointerLockControls ref={control} selector="#enter" />
        ) : (
          !state.tInnerFocus &&
          !state.tInnerAround && (
            <OrbitControls
              target={state.tFocus ? state.tFocus : [6, 15.7, -19.8]}
              enablePan={false}
              enableDamping={false}
              enableRotate={false}
              enableZoom={false}
            />
          )
        )
      ) : (
        <OrbitControls />
      )}
      {/* Room Camera */}
      <CustomCamera
        settings={{
          fov: 55,
          near: 0.1,
          far: 100,
          zoom: state.tInnerZoom,
          position: state.isTLocked ? [-5, 15.7, -19.8] : [0, 0, 0],
          rotation: [0, 3, 0],
          makeDef: fpv && state.tInnerAround === null,
        }}
      />
      {/* Godzilla Camera */}
      <CustomCamera
        settings={{
          fov: 55,
          near: 0.1,
          far: 100,
          zoom: 1,
          position: [4.3, 18.5, -24.6],
          rotation: [0.4, 3.14, 0],
          makeDef: state.tInnerAround !== null,
        }}
      />
      {state.focus && (
        <CameraController
          focus={state.focus.look}
          loc={state.focus.pos}
          zoom={state.tInnerZoom}
        />
      )}
      {state.tInnerAround && (
        <CameraAroundController animation={state.tInnerAround} />
      )}
    </>
  );
}

Camera.propTypes = {
  state: PropTypes.object,
  fpv: PropTypes.bool,
};

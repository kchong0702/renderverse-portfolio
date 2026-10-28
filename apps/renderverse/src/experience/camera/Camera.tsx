import CustomCamera from "./CustomCamera";
import CameraController from "./CameraController";
import { PointerLockControls, OrbitControls } from "@react-three/drei";
import { useRef, useEffect, type ElementRef } from "react";
import CameraAroundController from "./CameraAroundController";
import { ROOM_CAMERA_FOV } from "./constants";
import type { SceneState } from "@/experience/state/sceneStore";

interface CameraProps {
  state: SceneState;
  fpv: boolean;
}

export default function Camera({ state, fpv }: CameraProps) {
  const control = useRef<ElementRef<typeof PointerLockControls>>(null);

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
          fov: ROOM_CAMERA_FOV,
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
      {state.tInnerAround && <CameraAroundController />}
    </>
  );
}

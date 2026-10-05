import PropTypes from "prop-types";
import { Environment } from "@react-three/drei";

// import { useControls } from "leva";
// import { useMemo, useRef } from "react";
// import { useHelper } from "@react-three/drei";
// import * as THREE from 'three'

export default function ChatRoomLighting(props) {
  // const options = useMemo(() => {
  //     return {
  //         posx: { value: 0, min: -Math.PI * 2, max: Math.PI * 2, step: 0.01 },
  //         posy: { value: 0, min: -Math.PI * 2, max: Math.PI * 2, step: 0.01 },
  //         posz: { value: 0, min: -Math.PI * 2, max: Math.PI * 2, step: 0.01 },
  //         rotx: { value: 0, min: -Math.PI * 2, max: Math.PI * 2, step: 0.01 },
  //         roty: { value: 0, min: -Math.PI * 2, max: Math.PI * 2, step: 0.01 },
  //         rotz: { value: 0, min: -Math.PI * 2, max: Math.PI * 2, step: 0.01 },
  //         intensity: {value: 0, min: 0, max: 1, step: 0.01},
  //         color: {value: 'lime'},
  //         height: {value: 10},
  //         width: {value: 10}
  //     }
  // }, [])
  // const pointLight = useRef();
  // const pp = useControls('Point Light', options)
  // useHelper(pointLight, THREE.PointLightHelper)

  // const ap = useControls('Area Light', options)
  // const dp = useControls('Directional Light', options)

  return (
    <>
      {!props.isLightOff && (
        <>
          <Environment preset="dawn" environmentIntensity={0.3} />
          <ambientLight args={["white", 0.2]} />
          <rectAreaLight
            position={[-1.72, -0.12, 3.46]}
            intensity={0.5}
            // intensity={0}
            color={"#ffffff"}
            height={10}
            width={10}
          />
          <directionalLight
            position={[0, 2.35, -0.58]}
            intensity={1}
            // intensity={0}
            color={"#f8f8f8"}
          />
        </>
      )}
      <pointLight
        // ref={pointLight}
        position={[0.02, -0.7, 0.94]}
        color={props.isActive ? "#0023fc" : "#FF0000"}
        intensity={props.isLightOff ? 0.01 : 0.06}
      />
    </>
  );
}

ChatRoomLighting.propTypes = {
  isActive: PropTypes.bool,
  isLightOff: PropTypes.bool,
};

import { Html } from "@react-three/drei";
// import { useControls } from "leva";
import styles from "./Indicator.module.css";
import PropTypes from "prop-types";
import { extend } from "@react-three/fiber";
import { geometry } from "maath";

extend(geometry);

function Indicator({ settings }) {
  // const { position, rotation } = useControls("Indicator", {
  //   position: {
  //     value: {
  //       x: 0,
  //       y: 0,
  //       z: 0,
  //     },
  //     joystick: "invertY",
  //   },
  //   rotation: {
  //     value: {
  //       x: 0,
  //       y: 0,
  //       z: 0,
  //     },
  //   },
  // });
  return (
    <Html
      transform
      occlude="blending"
      distanceFactor={2.5}
      position={[
        settings.position[0],
        settings.position[1],
        settings.position[2],
      ]}
      rotation={[
        settings.rotation[0],
        settings.rotation[1],
        settings.rotation[2],
      ]}
      geometry={<roundedPlaneGeometry args={[0.25, 0.25, 0.12]} />}
    >
      <div id={settings.id} className={styles.content}>
        <div className={styles.icon}>{settings.icon}</div>
      </div>
    </Html>
  );
}

Indicator.propTypes = {
  settings: PropTypes.shape({
    position: PropTypes.array,
    rotation: PropTypes.array,
    icon: PropTypes.any,
    id: PropTypes.string,
  }),
};

export default Indicator;

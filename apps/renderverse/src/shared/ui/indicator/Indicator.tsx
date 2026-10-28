import type { ReactNode } from "react";
import { Html } from "@react-three/drei";
// import { useControls } from "leva";
import styles from "./Indicator.module.css";
import { extend, type BufferGeometryNode } from "@react-three/fiber";
import { geometry } from "maath";

extend(geometry);

declare module "@react-three/fiber" {
  interface ThreeElements {
    roundedPlaneGeometry: BufferGeometryNode<
      geometry.RoundedPlaneGeometry,
      typeof geometry.RoundedPlaneGeometry
    >;
  }
}

type Vector3Tuple = [number, number, number];

export interface IndicatorSettings {
  position: Vector3Tuple;
  rotation: Vector3Tuple;
  icon: ReactNode;
  id: string;
}

interface IndicatorProps {
  settings: IndicatorSettings;
}

function Indicator({ settings }: IndicatorProps) {
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

export default Indicator;

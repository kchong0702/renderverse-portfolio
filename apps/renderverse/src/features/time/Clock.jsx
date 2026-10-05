import { Html } from "@react-three/drei";
import { useControls } from "leva";
import styles from "./Clock.module.css";
import { useClock } from "../../hooks/useClock";
// import Indicator from "../../ui/indicator/Indicator";
// import { IoPartlySunny } from "react-icons/io5";
// import { MdNightsStay } from "react-icons/md";

function Clock() {
  const { hours, minutes } = useClock();
  const { position, rotation } = useControls("Clock html", {
    position: {
      value: {
        x: -2.78,
        y: 1.76,
        z: 6.769,
      },
      joystick: "invertY",
    },
    rotation: {
      value: {
        x: 0,
        y: 2.83,
        z: 0,
      },
    },
  });
  return (
    <>
      {/* <Indicator
        settings={{
          position: [-2.83, 2.08, 6.9],
          rotation: [0, 2.7, 0],
          icon:
            hours >= 18 ? (
              <MdNightsStay size={23} />
            ) : (
              <IoPartlySunny size={23} />
            ),
          id: "themeindicator",
        }}
      /> */}
      <Html
        transform
        occlude="blending"
        distanceFactor={2.5}
        position={[position.x, position.y, position.z]}
        rotation={[rotation.x, rotation.y, rotation.z]}
      >
        <div className={styles.content}>
          <span className={styles.time}>
            {hours}
            <span className={styles.blink}>:</span>
            {minutes}
          </span>
        </div>
      </Html>
    </>
  );
}

export default Clock;

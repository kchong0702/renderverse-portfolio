import { extend, useLoader } from "@react-three/fiber";
import { FontLoader } from "three/examples/jsm/loaders/FontLoader";
import { TextGeometry } from "three/examples/jsm/geometries/TextGeometry";
import { useControls } from "leva";
import { Center } from "@react-three/drei";
import { MeshBasicMaterial } from "three";
import { useTranslation } from "react-i18next";

extend({ TextGeometry });

// const textMaterials = [
//   new MeshPhongMaterial({ color: 0x171f27, flatShading: true }),
//   new MeshPhongMaterial({ color: 0xffffff }), // Example for another material
// ];

const textMaterials = [
  new MeshBasicMaterial({ color: 0x171f27 }),
  new MeshBasicMaterial({ color: 0x171f27 }), // Example for another material
];

const Title = () => {
  const { t } = useTranslation();
  const nameFont = useLoader(FontLoader, "./fonts/unione.json");
  const positionFont = useLoader(FontLoader, "./fonts/helvatica.json");

  const { position1, rotation1, dimension1 } = useControls("Title Font 1", {
    position1: {
      value: {
        x: 0,
        y: 5.2,
        z: 7.9,
      },
      joystick: "invertY",
    },
    rotation1: {
      value: {
        x: 0,
        y: Math.PI,
        z: 0,
      },
    },
    dimension1: {
      value: {
        size: 0.5,
        height: 0.1,
      },
    },
  });
  const { position2, rotation2, dimension2 } = useControls("Title Font 2", {
    position2: {
      value: {
        x: 0,
        y: 4.8,
        z: 7.9,
      },
      joystick: "invertY",
    },
    rotation2: {
      value: {
        x: 0,
        y: Math.PI,
        z: 0,
      },
    },
    dimension2: {
      value: {
        size: 0.16,
        height: 0.05,
      },
    },
  });
  return (
    <Center disableY disableZ>
      <mesh
        position={[position1.x, position1.y, position1.z]}
        rotation={[rotation1.x, rotation1.y, rotation1.z]}
      >
        <textGeometry
          args={[
            t("title.name"),
            { font: nameFont, size: dimension1.size, depth: dimension1.height },
          ]}
        />
        {textMaterials.map((material, index) => (
          <meshBasicMaterial key={index} attachArray="material" {...material} />
        ))}
      </mesh>
      <mesh
        position={[position2.x, position2.y, position2.z]}
        rotation={[rotation2.x, rotation2.y, rotation2.z]}
      >
        <textGeometry
          args={[
            t("title.role"),
            {
              font: positionFont,
              size: dimension2.size,
              depth: dimension2.height,
            },
          ]}
        />
        {textMaterials.map((material, index) => (
          <meshBasicMaterial key={index} attachArray="material" {...material} />
        ))}
      </mesh>
    </Center>
  );
};

export default Title;

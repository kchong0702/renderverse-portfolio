import { Html } from "@react-three/drei";
import { useControls } from "leva";
import styles from "./Skills.module.css";
import SkillCategory from "./SkillCategory";
import { MathJaxContext, MathJax } from "better-react-mathjax";
import { useTranslation } from "react-i18next";
import { useState, useEffect } from "react";

function Skills() {
  const { t } = useTranslation();
  const { position, rotation } = useControls("Skills html", {
    position: {
      value: {
        x: -0.4,
        y: 4.5,
        z: -7.156, // -7.156
      },
      joystick: "invertY",
    },
    rotation: {
      value: {
        x: 0,
        y: 0,
        z: -Math.PI / 2,
      },
    },
  });

  const skills = {
    [t("skills.categories.ai")]: [
      { name: t("skills.items.computerUseAgent"), rating: 5 },
      { name: t("skills.items.voiceAgent"), rating: 5 },
      { name: t("skills.items.bankingAgent"), rating: 5 },
    ],
    [t("skills.categories.frameworks")]: [
      { name: t("skills.items.langgraph"), rating: 5 },
      { name: t("skills.items.pytorch"), rating: 5 },
      { name: t("skills.items.springBoot"), rating: 5 },
      { name: t("skills.items.qt"), rating: 5 },
      { name: t("skills.items.angular"), rating: 5 },
      { name: t("skills.items.flutter"), rating: 5 },
    ],
    [t("skills.categories.telephony")]: [
      { name: t("skills.items.pbx"), rating: 5 },
      { name: t("skills.items.smpp"), rating: 5 },
      { name: t("skills.items.livekit"), rating: 5 },
      { name: t("skills.items.stuner"), rating: 5 },
    ],
    [t("skills.categories.language")]: [
      { name: t("skills.items.cpp"), rating: 5 },
      { name: t("skills.items.python"), rating: 5 },
      { name: t("skills.items.java"), rating: 5 },
      { name: t("skills.items.rust"), rating: 5 },
    ],
    [t("skills.categories.ops")]: [
      { name: t("skills.items.terraform"), rating: 5 },
      { name: t("skills.items.aws"), rating: 5 },
      { name: t("skills.items.gcp"), rating: 5 },
    ],
  };

  const [transformRedy, setTransformReady] = useState(false)
  useEffect(() => {
    const timer = setTimeout(() => setTransformReady(true), 100) // need delay to wait MathJax rendering
    return () => clearTimeout(timer)
  }, [])

  return (
    <Html
      transform={transformRedy}
      occlude
      distanceFactor={2.4} // 3
      position={[position.x, position.y, position.z]}
      rotation={[rotation.x, rotation.y, rotation.z]}
    >
      <div className={styles.skillContainer}>
        <div style={{ display: "flex", justifyContent: "flex-end" }}>
          <MathJaxContext>
            <MathJax style={{ transform: "rotate(-5deg)", fontSize: "1rem" }}>
              {
                "\\(W{x} = W{x} - \\alpha (\\frac{\\partial L}{\\partial W_{x}})\\)"
              }
            </MathJax>
          </MathJaxContext>
        </div>
        <div className={styles.content}>
          {Object.entries(skills).map(([key, value]) => (
            <SkillCategory category={key} contents={value} key={key} />
          ))}
        </div>
      </div>
    </Html>
  );
}

export default Skills;

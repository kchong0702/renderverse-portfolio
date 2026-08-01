import { Html } from "@react-three/drei";
import { useControls } from "leva";
import styles from "./Skills.module.css";
import SkillCategory from "./SkillCategory";
import { MathJaxContext, MathJax } from "better-react-mathjax";

const skills = {
  AI: [
    { name: "Computer Use Agent", rating: 5 },
    { name: "Voice Agent", rating: 5 },
    { name: "Banking Agent", rating: 5 },
  ],
  Frameworks: [
    { name: "Langgraph", rating: 5 },
    { name: "Pytorch", rating: 5 },
    { name: "Spring Boot", rating: 5 },
    { name: "Qt", rating: 5 },
    { name: "Angular", rating: 5 },
    { name: "Flutter", rating: 5 },
  ],
  Telephony: [
    { name: "PBX", rating: 5 },
    { name: "SMPP", rating: 5 },
    { name: "Livekit", rating: 5 },
    { name: "Stuner", rating: 5 },
  ],
  Language: [
    { name: "C++", rating: 5 },
    { name: "Python", rating: 5 },
    { name: "Java", rating: 5 },
    { name: "Rust", rating: 5 },
  ],
  Ops: [
    { name: "Terraform", rating: 5 },
    { name: "AWS", rating: 5 },
    { name: "GCP", rating: 5 },
  ],
};

function Skills() {
  const { position, rotation } = useControls("Skills html", {
    position: {
      value: {
        x: -0.4,
        y: 4.5,
        z: -7.156, // -7.155
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
  return (
    <Html
      transform
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
        {/* <div style={{ position: "absolute", right: "-10%", top: "-5%" }}>
          <MathJaxContext>
            <MathJax style={{ transform: "rotate(-5deg)", fontSize: "1.2rem" }}>
              {
                "\\(W{x} = W{x} - \\alpha (\\frac{\\partial L}{\\partial W_{x}})\\)"
              }
            </MathJax>
          </MathJaxContext>
        </div> */}
      </div>
    </Html>
  );
}

export default Skills;

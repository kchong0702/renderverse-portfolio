import { Html } from "@react-three/drei";
import styles from "./Contacts.module.css";
import { useControls } from "leva";
import { extend } from "@react-three/fiber";
import { geometry } from "maath";
import { MdEmail } from "react-icons/md";
import {
  FaFacebook,
  FaGithub,
  FaGitlab,
  FaInstagram,
  FaLink,
  FaLinkedin,
  FaXTwitter,
  FaYoutube,
} from "react-icons/fa6";
import { MdClose } from "react-icons/md";
import Indicator from "@/shared/components/Indicator";
import { MdContactPhone } from "react-icons/md";
import { useTranslation } from "react-i18next";
import { useRelease } from "@/features/portfolio/hooks/useRelease";
import type {
  SceneInteraction,
  SceneState,
} from "@/experience/state/sceneStore";

interface ContactsProps {
  handlePLInteraction: SceneInteraction;
  state: Pick<SceneState, "specialIsLocked">;
}

extend(geometry);

const contacts = [
  {
    contact_type_id: 0,
    contact_type: "Email",
    link: "kelvinchong.dev@gmail.com",
  },
  {
    contact_type_id: 1,
    contact_type: "LinkedIn",
    link: "https://www.linkedin.com/in/kelvin-chong-001570243",
  },
  {
    contact_type_id: 2,
    contact_type: "Instagram",
    link: "https://www.instagram.com/kelvinchong0702?igsh=MWJtYWZrODB2aGh2Zw==",
  },
];

const linkIcons = [
  { pattern: /linkedin/, icon: <FaLinkedin size={25} /> },
  { pattern: /github/, icon: <FaGithub size={25} /> },
  { pattern: /gitlab/, icon: <FaGitlab size={25} /> },
  { pattern: /instagram/, icon: <FaInstagram size={25} /> },
  { pattern: /facebook/, icon: <FaFacebook size={25} /> },
  { pattern: /youtube|youtu\.be/, icon: <FaYoutube size={25} /> },
  {
    pattern: /twitter|^x\b|\/\/(www\.)?x\.com/,
    icon: <FaXTwitter size={25} />,
  },
];

function Contacts({ handlePLInteraction, state }: ContactsProps) {
  const { t } = useTranslation();
  const { data: release } = useRelease();
  const links = release
    ? release.about.links.map((link) =>
        typeof link === "string" ? { label: "", url: link } : link,
      )
    : contacts
        .slice(1)
        .map((contact) => ({ label: contact.contact_type, url: contact.link }));
  const { position, rotation } = useControls("Contact html", {
    position: {
      value: {
        x: -3.75,
        y: 2.3,
        z: 6.2,
      },
      joystick: "invertY",
    },
    rotation: {
      value: {
        x: 0,
        y: 2.7,
        z: 0,
      },
    },
  });

  return (
    <>
      <Indicator
        settings={{
          position: [-3.75, 1.9, 6.2],
          rotation: [0, -0.5, 0],
          icon: <MdContactPhone size={23} />,
          id: "contactindicator",
        }}
      />
      {state.specialIsLocked === false && (
        <Html
          transform
          occlude="blending"
          distanceFactor={2.5}
          position={[position.x, position.y, position.z]}
          rotation={[rotation.x, rotation.y, rotation.z]}
          geometry={<roundedPlaneGeometry args={[1.4, 1.2, 0.1]} />}
        >
          <div className={styles.content}>
            <MdClose
              className={styles.close}
              size={20}
              onClick={(event) => {
                event.stopPropagation();
                handlePLInteraction("SLOCK");
              }}
            />
            <div className={styles.email}>
              <MdEmail size={40} />
              <h4>{t("contacts.sendEmail")}</h4>
              <span>{contacts[0].link}</span>
            </div>
            <div className={styles.separator}>
              <div className={styles.line}></div>
              <div className={styles.text}>{t("contacts.orFollow")}</div>
              <div className={styles.line}></div>
            </div>
            <div className={styles.social}>
              <ul>
                {links.map((link) => (
                  <li key={link.url}>
                    <a target="_blank" href={link.url} title={link.label}>
                      {linkIcons.find(({ pattern }) =>
                        pattern.test(`${link.label} ${link.url}`.toLowerCase()),
                      )?.icon ?? <FaLink size={25} />}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </Html>
      )}
    </>
  );
}

export default Contacts;

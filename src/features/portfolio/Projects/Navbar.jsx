import styles from "./Navbar.module.css";
// import { SiNetflix } from "react-icons/si";
import { RiNetflixFill } from "react-icons/ri";
import { VscMultipleWindows } from "react-icons/vsc";
import { VscChromeMinimize } from "react-icons/vsc";
import { MdClose } from "react-icons/md";
import PropTypes from "prop-types";

export default function Navbar({ handlePLInteraction }) {
  const brandSize = 18;
  const closeSize = 15;

  return (
    <div className={styles.navbar}>
      <ul>
        <li>
          <b className={styles.leftcurve}></b>
          <b className={styles.rightcurve}></b>
          <a style={{ marginRight: "15px" }}>
            <RiNetflixFill className={styles.netflix} size={brandSize} />
            <p>Netflix</p>
            <MdClose className={styles.close} size={closeSize} />
          </a>
        </li>
        <li className={styles.active}>
          <b className={styles.leftcurve}></b>
          <b className={styles.rightcurve}></b>
          <a>
            <img
              src="/logo/logo.png"
              alt="Logo"
              width={brandSize}
              height={brandSize}
              className={styles.logo}
            />
            <p>Projects</p>
            <MdClose className={styles.close} size={closeSize} />
          </a>
        </li>
      </ul>
      <div className={styles.endwidget}>
        <VscChromeMinimize
          className={styles.widget}
          size={20}
          onClick={(event) => {
            event.stopPropagation();
            handlePLInteraction("SLOCK");
          }}
        />
        <VscMultipleWindows
          className={styles.widget}
          size={20}
          onClick={(event) => {
            event.stopPropagation();
            handlePLInteraction("SLOCK");
          }}
        />
        <MdClose
          id="close-proj"
          className={`${styles.widget} ${styles.widgetclose}`}
          size={20}
          onClick={(event) => {
            event.stopPropagation();
            handlePLInteraction("SLOCK");
          }}
        />
      </div>
    </div>
  );
}

Navbar.propTypes = {
  handlePLInteraction: PropTypes.func,
};

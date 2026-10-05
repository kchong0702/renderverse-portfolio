import styles from "./FigureRoom.module.css";
import { FaArrowRight, FaArrowLeft } from "react-icons/fa";
import { useSceneControl } from "../../hooks/useSceneControl";
import { useState, useRef } from "react";
import { BiSolidZoomIn } from "react-icons/bi";
import { IoIosVideocam } from "react-icons/io";
import { BsFillInfoCircleFill } from "react-icons/bs";
import { TiLightbulb } from "react-icons/ti";
import { ImExit } from "react-icons/im";
import { RiZoomOutFill } from "react-icons/ri";
import { AiFillSound } from "react-icons/ai";
import { BsMusicNoteList } from "react-icons/bs";
const tInnerFocusStateTypes = [
  "initial",
  "zoom_godzilla",
  "around_godzilla",
  "focus_info",
];

export default function FigureRoom() {
  const [isActive, setIsActive] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [tInnerFocusState, setInnerFocusState] = useState(
    tInnerFocusStateTypes[0],
  );

  const { state, dispatch } = useSceneControl();

  const audio = useRef();
  const audio2 = useRef();

  const handleFocus = (payload, isActive) => {
    dispatch({ type: "TFOCUS", payload: payload });
    setIsActive(isActive);
  };

  const handleInnerZoom = (type, payload) => {
    dispatch({ type: "TINNERZOOM", payload: payload });
    setInnerFocusState(type);
  };

  const handleInnerZoomOut = (type) => {
    dispatch({ type: "TINNERZOOMOUT" });
    setInnerFocusState(type);
  };

  const handleInnerFocus = (type, payload) => {
    dispatch({ type: "TINNERFOCUS", payload: payload });
    setInnerFocusState(type);
  };

  const handleInnerLight = () => {
    dispatch({ type: "TINNERLIGHT" });
  };

  const handleInnerSound = () => {
    audio.current.play();
  };

  const handleAroundSound = () => {
    setPlaying((isPlaying) => {
      const playing = !isPlaying;

      if (playing) {
        audio2.current.play();
      } else {
        audio2.current.load();
      }

      return playing;
    });
  };

  const handleInnerAround = (type, payload) => {
    if (playing) {
      audio2.current.load();
    }
    dispatch({ type: "TINNERAROUND", payload: payload });
    setInnerFocusState(type);
  };

  return state.isTLocked ? (
    <>
      {tInnerFocusState === tInnerFocusStateTypes[0] &&
        (isActive ? (
          <FaArrowLeft
            className={`${styles.viewbtn} ${styles.left} ${styles.bounce}`}
            onClick={(event) => {
              event.stopPropagation();
              handleFocus([2, 16, -19.8], false);
            }}
          />
        ) : (
          <FaArrowRight
            className={`${styles.viewbtn} ${styles.right} ${styles.bounce}`}
            onClick={(event) => {
              event.stopPropagation();
              handleFocus([10, 12, 20], true);
            }}
          />
        ))}
      <div className={styles.clickablelist}>
        {/* Zoom Godzilla */}
        {(tInnerFocusState === tInnerFocusStateTypes[0] ||
          tInnerFocusState === tInnerFocusStateTypes[1]) && (
          <div
            className={styles.clickablebtn}
            onClick={(event) => {
              event.stopPropagation();
              handleInnerZoom(
                tInnerFocusStateTypes[1],
                state.tInnerZoom < 1.6
                  ? state.tInnerZoom + 0.3
                  : state.tInnerZoom,
              );
            }}
          >
            <BiSolidZoomIn size={30} />
          </div>
        )}
        {/* Around Godzilla */}
        {tInnerFocusState === tInnerFocusStateTypes[0] && (
          <div
            className={styles.clickablebtn}
            onClick={(event) => {
              event.stopPropagation();
              handleInnerAround(tInnerFocusStateTypes[2], {
                focus: { x: 4.3, y: 5, z: -23.6 },
                radius: 2,
              }); // focus - look, loc - pos, radius, time, down
            }}
          >
            <IoIosVideocam size={30} />
          </div>
        )}
        {/* Focus Info */}
        {tInnerFocusState === tInnerFocusStateTypes[0] && (
          <div
            className={styles.clickablebtn}
            onClick={(event) => {
              event.stopPropagation();
              dispatch({ type: "TINNERZOOM", payload: 2 });
              handleInnerFocus(tInnerFocusStateTypes[3], {
                look: { x: 30, y: 10, z: -4 },
                pos: { x: -5, y: 16, z: -19.8 },
              });
            }}
          >
            <BsFillInfoCircleFill size={25} />
          </div>
        )}
        {/* Lighting Control */}
        <div
          className={styles.clickablebtn}
          onClick={(event) => {
            event.stopPropagation();
            handleInnerLight();
          }}
        >
          <TiLightbulb size={30} />
        </div>
        {/* Sound Play */}
        {tInnerFocusState !== tInnerFocusStateTypes[2] && (
          <div
            className={styles.clickablebtn}
            onClick={(event) => {
              event.stopPropagation();
              handleInnerSound();
            }}
          >
            <AiFillSound size={30} />
          </div>
        )}
        {/* Around Godzilla Sound */}
        {tInnerFocusState === tInnerFocusStateTypes[2] && (
          <div
            className={styles.clickablebtn}
            onClick={(event) => {
              event.stopPropagation();
              handleAroundSound();
            }}
          >
            <BsMusicNoteList size={30} />
          </div>
        )}
        {/* Off Focus */}
        {tInnerFocusState === tInnerFocusStateTypes[3] && (
          <div
            className={styles.clickablebtn}
            onClick={(event) => {
              event.stopPropagation();
              dispatch({ type: "TINNERZOOMOUT" });
              handleInnerFocus(tInnerFocusStateTypes[0]);
            }}
          >
            <ImExit size={30} />
          </div>
        )}
        {/* Stop Around Godzilla */}
        {tInnerFocusState === tInnerFocusStateTypes[2] && (
          <div
            className={styles.clickablebtn}
            onClick={(event) => {
              event.stopPropagation();
              handleInnerAround(tInnerFocusStateTypes[0]);
            }}
          >
            <ImExit size={30} />
          </div>
        )}
        {/* Reset Zoom */}
        {tInnerFocusState === tInnerFocusStateTypes[1] && (
          <div
            className={styles.clickablebtn}
            onClick={(event) => {
              event.stopPropagation();
              handleInnerZoomOut(tInnerFocusStateTypes[0]);
            }}
          >
            <RiZoomOutFill size={30} />
          </div>
        )}
        <audio src="/assets/audio/shin-roar.mp3" ref={audio}></audio>
        <audio
          src="/assets/audio/godzilla-appear.mp3"
          ref={audio2}
          loop
        ></audio>
      </div>
    </>
  ) : (
    <></>
  );
}

import { MdMusicOff, MdMusicNote } from "react-icons/md";
import { useState, useEffect, useRef } from "react";
import { useChatControl } from "../hooks/useChatControl";
import { useSceneControl } from "../hooks/useSceneControl";

export default function Audio() {
  const [playing, setPlaying] = useState(false);

  const { state } = useSceneControl();
  const { chatState } = useChatControl();

  const audio = useRef();

  useEffect(() => {
    if (playing && audio) audio.current.play();
    else if (audio) audio.current.pause();
  }, [playing]);

  useEffect(() => {
    const handleMusic = (e) => {
      if ((e.key === "m" || e.code === 77) && !chatState.isOpen) {
        setPlaying((playing) => !playing);
      }
    };

    document.addEventListener("keydown", handleMusic);
    return () => {
      document.removeEventListener("keydown", handleMusic);
    };
  }, [chatState.isOpen, playing]);

  return (
    <div
      id="audio-overlay"
      style={{
        position: "fixed",
        width: "35px",
        height: "35px",
        top: "12px",
        right: "12px",
        background: "#FFB52E",
        borderRadius: "50%",
        color: "#fff",
        zIndex: 1,
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        opacity: 0,
      }}
      onClick={(event) => {
        event.stopPropagation();
        setPlaying((playing) => !playing);
      }}
    >
      <audio
        src={
          state.isTLocked
            ? "/assets/audio/sussus-toogus.mp3"
            : "/assets/audio/tokyo-walker.mp3"
        }
        ref={audio}
        loop
      ></audio>
      {playing ? <MdMusicNote size={30} /> : <MdMusicOff size={30} />}
    </div>
  );
}

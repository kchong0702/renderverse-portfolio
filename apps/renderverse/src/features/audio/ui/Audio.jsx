import { MdMusicOff, MdMusicNote } from "react-icons/md";
import { useState, useEffect, useRef } from "react";
import { useChatControl } from "@/features/ezbot";
import { useSceneControl } from "@/experience/state/useSceneControl";
import { useHotkey } from "@/shared/hooks/useHotkey";

export default function Audio() {
  const [playing, setPlaying] = useState(false);

  const { state } = useSceneControl();
  const { chatState } = useChatControl();

  const audio = useRef();

  const src = state.isTLocked
    ? "/assets/audio/sussus-toogus.mp3"
    : "/assets/audio/tokyo-walker.mp3";

  useEffect(() => {
    if (playing && audio)
      audio.current.play().catch((err) => {
        if (err.name !== "AbortError") setPlaying(false);
      });
    else if (audio) audio.current.pause();
  }, [playing, src]);

  useHotkey("KeyM", () => setPlaying((playing) => !playing), !chatState.isOpen);

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
      <audio src={src} ref={audio} loop></audio>
      {playing ? <MdMusicNote size={30} /> : <MdMusicOff size={30} />}
    </div>
  );
}

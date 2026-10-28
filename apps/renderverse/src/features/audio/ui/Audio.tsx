import { MdMusicOff, MdMusicNote } from "react-icons/md";
import { useState, useEffect, useRef } from "react";
import { useChatStore } from "@/features/ezbot";
import { useSceneStore } from "@/experience/state/sceneStore";
import { useHotkey } from "@/shared/hooks/useHotkey";

export default function Audio() {
  const [playing, setPlaying] = useState(false);

  const isTLocked = useSceneStore((s) => s.isTLocked);
  const isChatOpen = useChatStore((s) => s.isOpen);

  const audio = useRef<HTMLAudioElement>(null);

  const src = isTLocked
    ? "/assets/audio/sussus-toogus.mp3"
    : "/assets/audio/tokyo-walker.mp3";

  useEffect(() => {
    const el = audio.current;
    if (!el) return;
    if (playing)
      el.play().catch((err: Error) => {
        if (err.name !== "AbortError") setPlaying(false);
      });
    else el.pause();
  }, [playing, src]);

  useHotkey("KeyM", () => setPlaying((playing) => !playing), !isChatOpen);

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

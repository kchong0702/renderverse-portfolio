import { ImageIcon } from "lucide-react";
import type { Asset } from "../api/media";

export default function MediaThumb({ asset }: { asset: Asset | undefined }) {
  return (
    <span className="bg-chip border-hair flex h-10 w-16 shrink-0 items-center justify-center overflow-hidden rounded-md border">
      {asset?.media_type === "video/mp4" ? (
        <video
          src={`${asset.url}#t=0.1`}
          muted
          playsInline
          preload="metadata"
          aria-hidden="true"
          className="size-full object-cover"
        />
      ) : asset ? (
        <img src={asset.url} alt="" className="size-full object-cover" />
      ) : (
        <ImageIcon size={16} aria-hidden="true" className="text-ink-3" />
      )}
    </span>
  );
}

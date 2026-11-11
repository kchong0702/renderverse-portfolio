import i18n from "@/i18n";
import { ApiError, http } from "@/shared/api/http";

export type MediaSlot = "image" | "video";
export type MediaType = "image/png" | "image/jpeg" | "image/webp" | "video/mp4";

export const MEDIA_TYPES: Record<MediaSlot, MediaType[]> = {
  image: ["image/png", "image/jpeg", "image/webp"],
  video: ["video/mp4"],
};

export const MAX_BYTES: Record<MediaSlot, number> = {
  image: 10 * 1024 * 1024,
  video: 200 * 1024 * 1024,
};

export interface Asset {
  id: string;
  sha256: string;
  media_type: MediaType;
  size: number;
  filename: string;
  created_at: string;
  url: string;
  projects: { id: string; title: string }[];
}

interface UploadTarget {
  url: string;
  headers: Record<string, string>;
}

const URL = "/ops-api/v1/portfolio";

export const fetchAssets = (signal?: AbortSignal) =>
  http.get<Asset[]>(`${URL}/assets`, signal);

export const deleteAsset = (id: string) => http.delete(`${URL}/assets/${id}`);

export const chooseMedia = ({
  projectId,
  slot,
  assetId,
}: {
  projectId: string;
  slot: MediaSlot;
  assetId: string | null;
}) =>
  http.put<void>(`${URL}/projects/${projectId}/${slot}`, { asset_id: assetId });

export async function uploadAsset(
  file: File,
  onProgress: (fraction: number) => void,
): Promise<Asset> {
  const digest = await crypto.subtle.digest(
    "SHA-256",
    await file.arrayBuffer(),
  );
  const upload = {
    sha256: Array.from(new Uint8Array(digest), (byte) =>
      byte.toString(16).padStart(2, "0"),
    ).join(""),
    media_type: file.type,
    size: file.size,
    filename: file.name,
  };
  const target = await http.post<UploadTarget>(`${URL}/uploads`, upload);
  await new Promise<void>((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("PUT", target.url);
    for (const [name, value] of Object.entries(target.headers))
      request.setRequestHeader(name, value);
    request.upload.onprogress = (event) =>
      onProgress(event.loaded / event.total);
    request.onload = () =>
      request.status < 300
        ? resolve()
        : reject(
            new ApiError(
              request.status,
              i18n.t("errors.requestFailed", { status: request.status }),
            ),
          );
    request.onerror = () =>
      reject(new ApiError(0, i18n.t("portfolio.media.networkFailed")));
    request.send(file);
  });
  return http.post<Asset>(`${URL}/assets`, upload);
}

import {
  mutationOptions,
  queryOptions,
  type QueryClient,
} from "@tanstack/react-query";
import i18n from "@/i18n";
import { formatSize } from "@/shared/lib/size";
import {
  chooseMedia,
  deleteAsset,
  fetchAssets,
  MAX_BYTES,
  MEDIA_TYPES,
  uploadAsset,
  type Asset,
  type MediaSlot,
  type MediaType,
} from "../api/media";
import { draftQueryOptions } from "./portfolio";
import { entriesQueryOptions } from "./profile";

export const assetsQueryOptions = queryOptions({
  queryKey: ["portfolio", "assets"],
  queryFn: ({ signal }) => fetchAssets(signal),
});

const refresh = (client: QueryClient) =>
  Promise.all(
    [entriesQueryOptions, assetsQueryOptions, draftQueryOptions].map(
      ({ queryKey }) => client.invalidateQueries({ queryKey }),
    ),
  );

export interface MediaUpload {
  projectId: string;
  slot: MediaSlot;
  file: File;
  onProgress: (fraction: number) => void;
}

export const uploadMediaMutationOptions = mutationOptions({
  mutationFn: async ({ projectId, slot, file, onProgress }: MediaUpload) => {
    if (!MEDIA_TYPES[slot].includes(file.type as MediaType))
      throw new Error(
        i18n.t(`portfolio.media.wrongType.${slot}`, { name: file.name }),
      );
    if (file.size > MAX_BYTES[slot])
      throw new Error(
        i18n.t(`portfolio.media.tooLarge.${slot}`, {
          name: file.name,
          size: formatSize(file.size, i18n.language),
        }),
      );
    const asset = await uploadAsset(file, onProgress);
    await chooseMedia({ projectId, slot, assetId: asset.id });
  },
  onSettled: (_done, _error, _upload, _result, { client }) => refresh(client),
});

export const removeMediaMutationOptions = mutationOptions({
  mutationFn: ({ projectId, slot }: { projectId: string; slot: MediaSlot }) =>
    chooseMedia({ projectId, slot, assetId: null }),
  onSettled: (_done, _error, _remove, _result, { client }) => refresh(client),
});

export const deleteAssetMutationOptions = mutationOptions({
  mutationFn: deleteAsset,
  onMutate: async (id: string, { client }) => {
    const { queryKey } = assetsQueryOptions;
    await client.cancelQueries({ queryKey });
    const previous = client.getQueryData<Asset[]>(queryKey);
    if (previous)
      client.setQueryData(
        queryKey,
        previous.filter((asset) => asset.id !== id),
      );
    return { previous };
  },
  onError: (_error, _id, result, { client }) => {
    if (result?.previous)
      client.setQueryData(assetsQueryOptions.queryKey, result.previous);
  },
  onSettled: (_done, _error, _id, _result, { client }) =>
    client.invalidateQueries({ queryKey: assetsQueryOptions.queryKey }),
});

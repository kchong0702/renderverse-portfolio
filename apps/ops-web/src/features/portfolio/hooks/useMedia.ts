import { useMutation, useQuery } from "@tanstack/react-query";
import {
  assetsQueryOptions,
  deleteAssetMutationOptions,
  removeMediaMutationOptions,
  uploadMediaMutationOptions,
} from "../queries/media";

export function useAssets(enabled = true) {
  return useQuery({ ...assetsQueryOptions, enabled });
}

export function useUploadMedia() {
  return useMutation(uploadMediaMutationOptions);
}

export function useRemoveMedia() {
  return useMutation(removeMediaMutationOptions);
}

export function useDeleteAsset() {
  return useMutation(deleteAssetMutationOptions);
}

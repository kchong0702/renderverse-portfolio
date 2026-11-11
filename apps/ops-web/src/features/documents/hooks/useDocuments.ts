import { useMutation, useMutationState, useQuery } from "@tanstack/react-query";
import type { Edit } from "../api/documents";
import { overlaps, pathOf } from "../lib/changes";
import {
  cancelImportMutationOptions,
  changesetsQueryOptions,
  createDocumentMutationOptions,
  decideChangesetMutationOptions,
  deleteDocumentMutationOptions,
  designDocumentMutationOptions,
  documentQueryOptions,
  documentsQueryOptions,
  editDocumentMutationOptions,
  exportPdfMutationOptions,
  importsQueryOptions,
  readImportMutationOptions,
  setMasterMutationOptions,
  startImportMutationOptions,
  undoEditMutationOptions,
} from "../queries/documents";

export function useDocuments() {
  return useQuery(documentsQueryOptions);
}

export function useDocument(id: string) {
  return useQuery(documentQueryOptions(id));
}

export function useImports() {
  return useQuery(importsQueryOptions);
}

export function useCreateDocument() {
  return useMutation(createDocumentMutationOptions);
}

export function useEditDocument() {
  return useMutation(editDocumentMutationOptions);
}

export function useDesignDocument() {
  return useMutation(designDocumentMutationOptions);
}

export function useSaves(id: string) {
  return useMutationState({
    filters: {
      mutationKey: editDocumentMutationOptions.mutationKey,
      predicate: ({ state }) =>
        (state.variables as { id: string; edits: Edit[] }).id === id,
    },
    select: ({ state }) => ({ status: state.status, error: state.error }),
  });
}

export function useDeleteDocument() {
  return useMutation(deleteDocumentMutationOptions);
}

export function useSetMaster() {
  return useMutation(setMasterMutationOptions);
}

export function useExportPdf() {
  return useMutation(exportPdfMutationOptions);
}

export function useStartImport() {
  return useMutation(startImportMutationOptions);
}

export function useCancelImport() {
  return useMutation(cancelImportMutationOptions);
}

export function useReadImport() {
  return useMutation(readImportMutationOptions);
}

export function useChangesets(id: string) {
  return useQuery(changesetsQueryOptions(id));
}

export function usePendingChangeset(id: string) {
  return useChangesets(id).data?.find(
    ({ changeset }) => changeset.status === "pending",
  );
}

export function useDecideChangeset() {
  return useMutation(decideChangesetMutationOptions);
}

export function useUndoEdit() {
  return useMutation(undoEditMutationOptions);
}

export function useSave(id: string) {
  const { mutate: edit } = useEditDocument();
  const { mutate: undo } = useUndoEdit();
  const pending = usePendingChangeset(id);
  return (edits: Edit[]) => {
    const superseded = (pending?.changeset.edits ?? []).flatMap(
      (proposed, index) => {
        const path = pathOf(proposed);
        return path &&
          edits.some(
            (own) => own.kind === "update_field" && overlaps(own.path, path),
          )
          ? [index]
          : [];
      },
    );
    for (const index of superseded.reverse())
      undo({ id, changesetId: pending!.id, index });
    edit({ id, edits });
  };
}

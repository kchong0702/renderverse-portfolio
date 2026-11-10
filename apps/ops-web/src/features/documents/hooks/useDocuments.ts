import { useMutation, useMutationState, useQuery } from "@tanstack/react-query";
import type { DocumentKind, Edit } from "../api/documents";
import {
  answerEditMutationOptions,
  cancelImportMutationOptions,
  createDocumentMutationOptions,
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
  templatesQueryOptions,
} from "../queries/documents";

export function useDocuments() {
  return useQuery(documentsQueryOptions);
}

export function useDocument(id: string) {
  return useQuery(documentQueryOptions(id));
}

export function useTemplates(kind: DocumentKind) {
  return useQuery(templatesQueryOptions(kind));
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

export function useAnswerEdit() {
  return useMutation(answerEditMutationOptions);
}

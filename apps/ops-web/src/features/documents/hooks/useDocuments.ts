import { useMutation, useQuery } from "@tanstack/react-query";
import type { DocumentKind } from "../api/documents";
import {
  cancelImportMutationOptions,
  changesetsQueryOptions,
  createDocumentMutationOptions,
  decideChangesetMutationOptions,
  deleteDocumentMutationOptions,
  documentQueryOptions,
  documentsQueryOptions,
  editDocumentMutationOptions,
  importsQueryOptions,
  keepVersionMutationOptions,
  renameDocumentMutationOptions,
  renderQueryOptions,
  restoreVersionMutationOptions,
  setMasterMutationOptions,
  startImportMutationOptions,
  templatesQueryOptions,
  versionsQueryOptions,
} from "../queries/documents";

export function useDocuments() {
  return useQuery(documentsQueryOptions);
}

export function useDocument(id: string) {
  return useQuery(documentQueryOptions(id));
}

export function useRender(id: string, updatedAt: string) {
  return useQuery(renderQueryOptions(id, updatedAt));
}

export function useVersions(id: string) {
  return useQuery(versionsQueryOptions(id));
}

export function useChangesets(id: string) {
  return useQuery(changesetsQueryOptions(id));
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

export function useRenameDocument() {
  return useMutation(renameDocumentMutationOptions);
}

export function useEditDocument() {
  return useMutation(editDocumentMutationOptions);
}

export function useSetMaster() {
  return useMutation(setMasterMutationOptions);
}

export function useDeleteDocument() {
  return useMutation(deleteDocumentMutationOptions);
}

export function useKeepVersion() {
  return useMutation(keepVersionMutationOptions);
}

export function useRestoreVersion() {
  return useMutation(restoreVersionMutationOptions);
}

export function useDecideChangeset() {
  return useMutation(decideChangesetMutationOptions);
}

export function useStartImport() {
  return useMutation(startImportMutationOptions);
}

export function useCancelImport() {
  return useMutation(cancelImportMutationOptions);
}

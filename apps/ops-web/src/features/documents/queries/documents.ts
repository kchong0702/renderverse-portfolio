import {
  mutationOptions,
  queryOptions,
  type QueryClient,
} from "@tanstack/react-query";
import {
  cancelImport,
  createDocument,
  decideChangeset,
  deleteDocument,
  editDocument,
  fetchChangesets,
  fetchDocument,
  fetchDocuments,
  fetchImports,
  fetchRender,
  readImport,
  setMaster,
  startImport,
  undoChangesetEdit,
  type DocumentRecord,
} from "../api/documents";

export const documentsQueryOptions = queryOptions({
  queryKey: ["documents"],
  queryFn: ({ signal }) => fetchDocuments(signal),
});

export const documentQueryOptions = (id: string) =>
  queryOptions({
    queryKey: ["documents", id],
    queryFn: ({ signal }) => fetchDocument(id, signal),
  });

export const changesetsQueryOptions = (id: string) =>
  queryOptions({
    queryKey: ["documents", id, "changesets"],
    queryFn: ({ signal }) => fetchChangesets(id, signal),
  });

export const importsQueryOptions = queryOptions({
  queryKey: ["documents", "imports"],
  queryFn: ({ signal }) => fetchImports(signal),
  refetchInterval: ({ state }) =>
    state.data?.[0]?.status === "running" ? 5000 : false,
});

function storeDocument(client: QueryClient, document: DocumentRecord) {
  client.setQueryData(documentQueryOptions(document.id).queryKey, document);
  return client.invalidateQueries({
    queryKey: documentsQueryOptions.queryKey,
    exact: true,
  });
}

export const createDocumentMutationOptions = mutationOptions({
  mutationFn: createDocument,
  onSuccess: (document, _create, _result, { client }) =>
    storeDocument(client, document),
});

export const editDocumentMutationOptions = mutationOptions({
  mutationKey: ["documents", "edit"],
  mutationFn: editDocument,
  scope: { id: "documents:edit" },
  onSuccess: (document, _edit, _result, { client }) =>
    storeDocument(client, document),
});

export const designDocumentMutationOptions = mutationOptions({
  ...editDocumentMutationOptions,
  mutationKey: ["documents", "design"],
});

const refreshDocument = (client: QueryClient, id: string) =>
  client.invalidateQueries({ queryKey: documentQueryOptions(id).queryKey });

export const undoEditMutationOptions = mutationOptions({
  mutationKey: ["documents", "edit", "undo"],
  mutationFn: undoChangesetEdit,
  scope: { id: "documents:edit" },
  onSettled: (_undone, _error, { id }, _result, { client }) =>
    refreshDocument(client, id),
});

export const decideChangesetMutationOptions = mutationOptions({
  mutationFn: decideChangeset,
  scope: { id: "documents:edit" },
  onSettled: (_decided, _error, { id }, _result, { client }) =>
    Promise.all([
      refreshDocument(client, id),
      client.invalidateQueries({
        queryKey: documentsQueryOptions.queryKey,
        exact: true,
      }),
    ]),
});

export const deleteDocumentMutationOptions = mutationOptions({
  mutationFn: deleteDocument,
  onSuccess: (_deleted, _id, _result, { client }) =>
    client.invalidateQueries({
      queryKey: documentsQueryOptions.queryKey,
      exact: true,
    }),
});

export const setMasterMutationOptions = mutationOptions({
  mutationFn: setMaster,
  onSuccess: (_document, _id, _result, { client }) =>
    client.invalidateQueries({ queryKey: documentsQueryOptions.queryKey }),
});

export const exportPdfMutationOptions = mutationOptions({
  mutationFn: fetchRender,
});

export const startImportMutationOptions = mutationOptions({
  mutationFn: startImport,
  onSettled: (_import, _error, _file, _result, { client }) =>
    client.invalidateQueries({ queryKey: importsQueryOptions.queryKey }),
});

export const cancelImportMutationOptions = mutationOptions({
  mutationFn: cancelImport,
  onSettled: (_cancelled, _error, _id, _result, { client }) =>
    client.invalidateQueries({ queryKey: importsQueryOptions.queryKey }),
});

export const readImportMutationOptions = mutationOptions({
  mutationKey: ["documents", "imports", "read"],
  mutationFn: readImport,
  onSettled: (_import, _error, _id, _result, { client }) =>
    Promise.all([
      client.invalidateQueries({ queryKey: importsQueryOptions.queryKey }),
      client.invalidateQueries({
        queryKey: documentsQueryOptions.queryKey,
        exact: true,
      }),
    ]),
});

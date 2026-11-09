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
  fetchTemplates,
  fetchVersions,
  keepVersion,
  renameDocument,
  restoreVersion,
  setMaster,
  startImport,
  type DocumentKind,
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

export const renderQueryOptions = (id: string, updatedAt: string) =>
  queryOptions({
    queryKey: ["documents", id, "render", updatedAt],
    queryFn: ({ signal }) => fetchRender(id, signal),
    staleTime: Infinity,
    retry: false,
  });

export const versionsQueryOptions = (id: string) =>
  queryOptions({
    queryKey: ["documents", id, "versions"],
    queryFn: ({ signal }) => fetchVersions(id, signal),
  });

export const changesetsQueryOptions = (id: string) =>
  queryOptions({
    queryKey: ["documents", id, "changesets"],
    queryFn: ({ signal }) => fetchChangesets(id, signal),
  });

export const templatesQueryOptions = (kind: DocumentKind) =>
  queryOptions({
    queryKey: ["documents", "templates", kind],
    queryFn: ({ signal }) => fetchTemplates(kind, signal),
    staleTime: Infinity,
  });

export const importsQueryOptions = queryOptions({
  queryKey: ["documents", "imports"],
  queryFn: ({ signal }) => fetchImports(signal),
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

export const renameDocumentMutationOptions = mutationOptions({
  mutationFn: renameDocument,
  onSuccess: (document, _rename, _result, { client }) =>
    storeDocument(client, document),
});

export const editDocumentMutationOptions = mutationOptions({
  mutationFn: editDocument,
  onSuccess: (document, _edit, _result, { client }) =>
    storeDocument(client, document),
});

export const setMasterMutationOptions = mutationOptions({
  mutationFn: setMaster,
  onSuccess: (document, _id, _result, { client }) =>
    storeDocument(client, document),
});

export const deleteDocumentMutationOptions = mutationOptions({
  mutationFn: deleteDocument,
  onSettled: (_deleted, _error, _id, _result, { client }) =>
    client.invalidateQueries({
      queryKey: documentsQueryOptions.queryKey,
      exact: true,
    }),
});

export const keepVersionMutationOptions = mutationOptions({
  mutationFn: keepVersion,
  onSettled: (_version, _error, { id }, _result, { client }) =>
    client.invalidateQueries({ queryKey: versionsQueryOptions(id).queryKey }),
});

export const restoreVersionMutationOptions = mutationOptions({
  mutationFn: restoreVersion,
  onSuccess: (document, _restore, _result, { client }) =>
    storeDocument(client, document),
});

export const decideChangesetMutationOptions = mutationOptions({
  mutationFn: decideChangeset,
  onSuccess: (changeset, { id }, _result, { client }) => {
    const { queryKey } = changesetsQueryOptions(id);
    client.setQueryData(queryKey, (changesets) =>
      changesets?.map((c) => (c.id === changeset.id ? changeset : c)),
    );
  },
  onSettled: (_changeset, _error, { id }, _result, { client }) =>
    Promise.all([
      client.invalidateQueries({
        queryKey: documentQueryOptions(id).queryKey,
        exact: true,
      }),
      client.invalidateQueries({ queryKey: versionsQueryOptions(id).queryKey }),
      client.invalidateQueries({
        queryKey: documentsQueryOptions.queryKey,
        exact: true,
      }),
    ]),
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

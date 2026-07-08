"use client";

import { useRef, useState } from "react";
import { FileUp, Plus, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useWorkspaceStore } from "@/stores/workspace-store";

export default function DocumentsPage() {
  const documents = useWorkspaceStore((s) => s.documents);
  const addDocument = useWorkspaceStore((s) => s.addDocument);
  const searchWorkspace = useWorkspaceStore((s) => s.searchWorkspace);
  const [query, setQuery] = useState("");
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const results = query.trim() ? searchWorkspace(query).filter((r) => r.type === "document" || r.type === "memory") : [];

  async function uploadFile(file: File) {
    setUploading(true);
    try {
      const formData = new FormData();
      formData.set("file", file);
      const res = await fetch("/api/workspace/documents", { method: "POST", body: formData, credentials: "include" });
      if (res.ok) {
        const payload = (await res.json()) as { document?: { id: string; title: string; summary?: string } };
        if (payload.document) {
          addDocument({
            id: payload.document.id,
            title: payload.document.title,
            summary: payload.document.summary ?? "Indexed for semantic search.",
            type: file.name.endsWith(".pdf") ? "pdf" : "markdown",
            chunks: 0
          });
        }
      }
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-4 md:p-6">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <h1 className="text-2xl font-semibold">Documents</h1>
          <p className="mt-1 text-sm text-muted-foreground">Upload, index, and search your knowledge base.</p>
        </div>
        <div className="flex gap-2">
          <input
            ref={fileRef}
            type="file"
            className="hidden"
            accept=".pdf,.doc,.docx,.txt,.md,.markdown"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) void uploadFile(file);
              e.target.value = "";
            }}
          />
          <Button variant="primary" disabled={uploading} onClick={() => fileRef.current?.click()}>
            <FileUp size={16} />
            {uploading ? "Uploading..." : "Upload"}
          </Button>
        </div>
      </div>

      <div className="surface flex items-center gap-2 p-3">
        <Search size={16} className="text-primary" />
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Semantic search across documents and memory..."
          className="border-0 bg-transparent focus-visible:ring-0"
        />
      </div>

      {query.trim() ? (
        <div className="space-y-2">
          {results.length === 0 ? (
            <p className="text-sm text-muted-foreground">No matches found.</p>
          ) : (
            results.map((r) => (
              <div key={`${r.type}-${r.id}`} className="surface p-4">
                <div className="flex justify-between gap-2">
                  <span className="font-medium">{r.title}</span>
                  <span className="text-xs text-muted-foreground">{r.type}</span>
                </div>
                <p className="mt-1 text-sm text-muted-foreground">{r.snippet}</p>
              </div>
            ))
          )}
        </div>
      ) : (
        <div className="grid gap-3">
          {documents.length === 0 ? (
            <div className="surface flex flex-col items-center justify-center p-12 text-center">
              <FileUp className="mb-3 text-muted-foreground" size={32} />
              <p className="text-sm text-muted-foreground">Drop files here or use Upload to index documents.</p>
              <Button variant="outline" className="mt-4" onClick={() => fileRef.current?.click()}>
                <Plus size={16} />
                Upload document
              </Button>
            </div>
          ) : (
            documents.map((doc) => (
              <div key={doc.id} className="surface flex flex-col justify-between gap-2 p-4 sm:flex-row sm:items-center">
                <div>
                  <h3 className="font-medium">{doc.title}</h3>
                  <p className="mt-1 text-sm text-muted-foreground">{doc.summary}</p>
                </div>
                <div className="text-right text-xs text-muted-foreground">
                  <div>{doc.type.toUpperCase()}</div>
                  <div>{doc.chunks} chunks</div>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

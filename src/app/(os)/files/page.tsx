"use client";

import { useCallback, useEffect, useState, useMemo } from "react";
import { FileText, Download, Loader2 } from "lucide-react";
import { api, type ActionExecution } from "@/lib/api";
import { Page } from "@/components/design-system/workspace-primitives";

function getFileExtension(title: string): string {
  const parts = title.split(".");
  return parts.length > 1 ? parts[parts.length - 1].toLowerCase() : "file";
}

type ActionArtifact = {
  id?: string;
  filename?: string;
  file_name?: string;
  file_type?: string;
  file_size?: number;
};

export default function FilesPage() {
  const [executions, setExecutions] = useState<ActionExecution[]>([]);
  const [loading, setLoading] = useState(true);

  const loadExecutions = useCallback(async () => {
    try {
      const rows = await api.listActionExecutions();
      setExecutions(rows);
    } catch {
      setExecutions([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadExecutions();
  }, [loadExecutions]);

  const files = useMemo(() => {
    return executions
      .filter((e) => e.status === "completed")
      .flatMap((execution) => {
        const artifacts = Array.isArray(execution.metadata?.artifacts) ? execution.metadata.artifacts as ActionArtifact[] : [];
        return artifacts.filter((artifact) => artifact.id).map((artifact) => ({
          id: `${execution.id}-${artifact.id}`,
          artifactId: artifact.id as string,
          actionId: execution.id,
          name: artifact.filename || artifact.file_name || execution.title,
          type: getFileExtension(artifact.filename || artifact.file_name || execution.title),
          size: artifact.file_size,
          timestamp: execution.updated_at,
        }));
      })
      .sort(
        (a, b) =>
          new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
      );
  }, [executions]);

  return (
    <Page>
      <div className="mx-auto max-w-3xl px-5 py-12 sm:px-8 sm:py-16">
        <div className="mb-10">
          <p className="synzept-eyebrow mb-3">Memory</p>
          <h1 className="text-[1.875rem] font-semibold leading-tight tracking-[-0.035em] text-stone-950">What Synzept has made</h1>
          <p className="mt-2 text-[15px] leading-6 text-stone-600">Files and work products created from your conversations.</p>
        </div>

        {/* Files list */}
        <div className="mt-8">
          {loading ? (
            <div className="text-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-stone-400 mx-auto mb-4" />
              <p className="text-stone-600">Loading files...</p>
            </div>
          ) : files.length === 0 ? (
            <div className="border-y border-dashed border-stone-300 py-12 text-center">
              <FileText className="h-8 w-8 text-stone-400 mx-auto mb-3" />
              <p className="text-stone-600">No files yet</p>
              <p className="text-sm text-stone-500 mt-1">
                Files created by Synzept will appear here
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {files.map((file) => (
                <div
                  key={file.id}
                  className="flex items-center justify-between gap-4 border-t border-border/[0.08] py-4 transition-colors hover:bg-surface-overlay/50"
                >
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <div className="flex-shrink-0">
                      <div className="flex h-9 w-9 items-center justify-center rounded-md bg-surface-overlay">
                        <FileText className="h-5 w-5 text-stone-600" />
                      </div>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-stone-900 truncate">
                        {file.name}
                      </p>
                      <p className="text-xs text-stone-600 mt-0.5">
                        {file.type.toUpperCase()} · {new Date(file.timestamp).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  <a
                    href={api.actionArtifactUrl(file.actionId, file.artifactId)}
                    download
                    className="ml-3 flex h-9 w-9 shrink-0 items-center justify-center rounded-md text-stone-600 transition-colors hover:bg-stone-100"
                    aria-label={`Download ${file.name}`}
                  >
                    <Download className="h-4 w-4" />
                  </a>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </Page>
  );
}

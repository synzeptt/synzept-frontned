export type ResultArtifact = { name?: string; title?: string; content?: string; url?: string; href?: string; file_path?: string; download_url?: string; downloadUrl?: string };

export const DEFAULT_EXECUTION_DETAILS_EXPANDED = false;

export function resolveArtifactUrl(source: string): string {
  if (!source.startsWith("/api/")) return source;
  const apiBase = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/$/, "");
  return apiBase ? `${apiBase}${source}` : source;
}

export function isSimpleInformationalResult(execution: { action_type: string }): boolean {
  return execution.action_type === "gmail_unread";
}

export function hasUsableArtifact(artifact: ResultArtifact | undefined): boolean {
  return Boolean(artifact && (artifact.url || artifact.href || artifact.file_path || artifact.download_url || artifact.downloadUrl || artifact.content));
}

export function downloadResultArtifact(artifact: ResultArtifact | undefined, documentRef?: Document): boolean {
  if (!artifact || !documentRef || !hasUsableArtifact(artifact)) return false;
  const source = artifact.download_url || artifact.downloadUrl || artifact.url || artifact.href;
  const link = documentRef.createElement("a");
  link.href = source ? resolveArtifactUrl(source) : `data:text/plain;charset=utf-8,${encodeURIComponent(artifact.content || "")}`;
  link.download = artifact.name || artifact.title || "synzept-result.txt";
  link.target = "_blank";
  link.rel = "noreferrer";
  documentRef.body.appendChild(link);
  link.click();
  link.remove();
  return true;
}

export function openResultArtifact(artifact: ResultArtifact | undefined, windowRef?: Window): boolean {
  if (!artifact || !windowRef || !hasUsableArtifact(artifact)) return false;
  const source = artifact.url || artifact.href || artifact.file_path;
  windowRef.open(source ? resolveArtifactUrl(source) : `data:text/plain;charset=utf-8,${encodeURIComponent(artifact.content || "")}`, "_blank", "noopener,noreferrer");
  return true;
}

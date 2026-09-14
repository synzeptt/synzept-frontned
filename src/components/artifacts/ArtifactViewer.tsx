"use client";

import { useEffect, useState } from "react";
import { Markdown } from "@/components/chat/markdown";

type Artifact = {
  url?: string;
  href?: string;
  path?: string;
  content_type?: string;
  mime?: string;
  original?: {
    url?: string;
    content_type?: string;
  };
};

export default function ArtifactViewer({ artifact }: { artifact: Artifact | null | undefined }) {
  const [content, setContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!artifact) return;
    const url = artifact.url || artifact.href || artifact.path || artifact.original?.url;
    if (!url) return;
    setLoading(true);
    setError(null);
    void fetch(url, { credentials: "include" })
      .then(async (res) => {
        const ct = res.headers.get("content-type") || artifact.content_type || "text/plain";
        if (ct.includes("application/json")) {
          const json = await res.json();
          setContent(JSON.stringify(json, null, 2));
        } else if (ct.includes("text/") || ct.includes("markdown") || ct.includes("csv")) {
          const text = await res.text();
          setContent(text);
        } else {
          setContent(null);
        }
      })
      .catch(() => setError("Preview unavailable"))
      .finally(() => setLoading(false));
  }, [artifact]);

  if (!artifact) return <div className="text-sm text-stone-500">No artifact selected.</div>;

  const url = artifact.url || artifact.href || artifact.path || artifact.original?.url;
  const contentType = artifact.content_type || artifact.mime || (typeof artifact.original?.content_type === "string" ? artifact.original.content_type : null);

  if (loading) return <div className="text-sm text-stone-500">Loading preview…</div>;
  if (error) return <div className="text-sm text-rose-600">{error}</div>;

  if (contentType?.includes("markdown") || (content && /[#\-*`]/.test(content.slice(0, 120)))) {
    return <Markdown content={content || ""} className="prose-synzept max-w-none" />;
  }

  if (contentType?.includes("json") || (content && isJsonString(content))) {
    return (
      <pre className="whitespace-pre-wrap break-words text-sm text-stone-700">
        {content}
      </pre>
    );
  }

  if (content) {
    return <pre className="whitespace-pre-wrap break-words text-sm text-stone-700">{content}</pre>;
  }

  if (url) {
    return (
      <div className="text-sm text-stone-700">
        <p>Preview not available for this file type.</p>
        <p className="mt-3"><a className="text-accent underline" href={url} target="_blank" rel="noreferrer">Open or download</a></p>
      </div>
    );
  }

  return <div className="text-sm text-stone-500">No preview available.</div>;
}

function isJsonString(value: string) {
  try {
    JSON.parse(value);
    return true;
  } catch {
    return false;
  }
}

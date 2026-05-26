import { ImageResponse } from "next/og";

import { SITE_DESCRIPTION, SITE_NAME } from "@/lib/seo";

export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpenGraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          height: "100%",
          width: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "64px",
          background:
            "linear-gradient(135deg, #f8f6f1 0%, #efece3 55%, #dde7de 100%)",
          color: "#24231f",
          fontFamily: "Inter, Arial, sans-serif",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: "24px", maxWidth: "700px" }}>
          <div
            style={{
              display: "inline-flex",
              width: "fit-content",
              borderRadius: "999px",
              padding: "12px 18px",
              border: "1px solid rgba(63,95,74,0.18)",
              background: "rgba(255,255,255,0.78)",
              fontSize: "28px",
              color: "#3f5f4a",
            }}
          >
            Continuity-first AI workspace
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <div style={{ fontSize: "84px", fontWeight: 700, lineHeight: 1, letterSpacing: "-0.05em" }}>{SITE_NAME}</div>
            <div style={{ fontSize: "32px", lineHeight: 1.35, color: "#4f4b43" }}>{SITE_DESCRIPTION}</div>
          </div>
        </div>
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
            alignSelf: "stretch",
            minWidth: "300px",
            borderRadius: "28px",
            border: "1px solid rgba(36,35,31,0.08)",
            background: "rgba(255,255,255,0.82)",
            padding: "28px",
            boxShadow: "0 24px 80px rgba(36,35,31,0.08)",
          }}
        >
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            {[
              "Memory-powered organization",
              "Project continuity",
              "Clear daily momentum",
            ].map((item) => (
              <div
                key={item}
                style={{
                  borderRadius: "18px",
                  padding: "18px 20px",
                  background: "#f8f6f1",
                  border: "1px solid rgba(36,35,31,0.06)",
                  fontSize: "28px",
                  fontWeight: 600,
                }}
              >
                {item}
              </div>
            ))}
          </div>
          <div style={{ fontSize: "24px", color: "#6b655a" }}>synzept.com</div>
        </div>
      </div>
    ),
    size,
  );
}

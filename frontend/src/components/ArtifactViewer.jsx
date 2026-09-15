import { useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/*
 * Security note (see architecture.md "Artifact security"):
 * HTML artifacts are rendered inside an <iframe sandbox="allow-same-origin">.
 * We deliberately OMIT "allow-scripts" from the sandbox attribute, which
 * means any <script> that slipped past server-side sanitization still
 * cannot execute inside the iframe. This is defense-in-depth on top of the
 * prompt-level and server-side stripping already applied in
 * app/agent/skills/artifact_skill.py.
 */
function HtmlArtifactFrame({ content }) {
  const srcDoc = useMemo(
    () => `<!doctype html><html><head><meta charset="utf-8" />
      <style>body{font-family:system-ui,sans-serif;margin:16px;color:#1a1a1a;}</style>
      </head><body>${content}</body></html>`,
    [content]
  );
  return (
    <iframe
      title="artifact-preview"
      className="artifact-frame"
      sandbox="allow-same-origin"
      srcDoc={srcDoc}
    />
  );
}

export default function ArtifactViewer({ artifact, onClose }) {
  if (!artifact) {
    return (
      <div className="artifact-viewer empty">
        <p>Generated Markdown or HTML artifacts will appear here.</p>
        <p className="hint">
          Try: "Turn this into a Ship 30 for 30 essay" or "Generate an HTML artifact summarizing this"
        </p>
      </div>
    );
  }

  return (
    <div className="artifact-viewer">
      <div className="artifact-header">
        <div>
          <span className="artifact-kind-badge">{artifact.kind}</span>
          <strong className="artifact-title">{artifact.title}</strong>
        </div>
        <div className="artifact-actions">
          <button
            onClick={() => navigator.clipboard.writeText(artifact.content)}
            title="Copy raw content"
          >
            Copy
          </button>
          <button onClick={onClose} title="Close">
            ×
          </button>
        </div>
      </div>
      <div className="artifact-body">
        {artifact.kind === "html" ? (
          <HtmlArtifactFrame content={artifact.content} />
        ) : (
          <div className="markdown-render">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{artifact.content}</ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
}

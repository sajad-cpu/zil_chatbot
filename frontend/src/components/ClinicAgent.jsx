const CLINIC_AGENT_URL =
  import.meta.env.VITE_CLINIC_AGENT_URL ||
  (import.meta.env.DEV ? "http://localhost:8501" : "");

export default function ClinicAgent() {
  const hasAgentUrl = Boolean(CLINIC_AGENT_URL);

  return (
    <div className="clinic-page">
      <div className="clinic-shell">
        <div className="clinic-header">
          <div>
            <p className="clinic-eyebrow">CarePlus</p>
            <h1>Clinic AI Assistant</h1>
            <p className="clinic-subtitle">
              Book appointments and guide patients through the clinic flow.
            </p>
          </div>
          <a className="clinic-back-link" href="/">
            Open RAG Chatbot
          </a>
        </div>

        {hasAgentUrl ? (
          <>
            <div className="clinic-meta">
              <span>Embedded clinic agent</span>
              <a href={CLINIC_AGENT_URL} target="_blank" rel="noreferrer">
                Open in new tab
              </a>
            </div>
            <iframe
              className="clinic-frame"
              src={CLINIC_AGENT_URL}
              title="Clinic AI Assistant"
              allow="clipboard-write"
            />
          </>
        ) : (
          <div className="clinic-empty-state">
            <h2>Clinic agent URL not configured</h2>
            <p>
              Set <code>VITE_CLINIC_AGENT_URL</code> in the frontend environment
              to the deployed Streamlit or clinic-agent URL, then redeploy.
            </p>
            <p>
              Example: <code>VITE_CLINIC_AGENT_URL=https://your-clinic-app.example.com</code>
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

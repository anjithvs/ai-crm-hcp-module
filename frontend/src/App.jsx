import { useEffect, useState } from "react";
import { useDispatch } from "react-redux";
import "./App.css";
import AIAssistantChat from "./components/AIAssistantChat.jsx";
import InteractionForm from "./components/InteractionForm.jsx";
import { fetchInteraction, resetInteraction as resetInteractionApi } from "./api.js";
import { resetChat } from "./store/chatSlice.js";
import { resetInteraction, setInteraction } from "./store/interactionSlice.js";

const SESSION_STORAGE_KEY = "hcp_crm_session_id";

function getOrCreateSessionId() {
  let id = localStorage.getItem(SESSION_STORAGE_KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(SESSION_STORAGE_KEY, id);
  }
  return id;
}

export default function App() {
  const [sessionId] = useState(getOrCreateSessionId);
  const [backendStatus, setBackendStatus] = useState("checking");
  const dispatch = useDispatch();

  useEffect(() => {
    fetchInteraction(sessionId)
      .then((data) => {
        dispatch(setInteraction(data));
        setBackendStatus("ok");
      })
      .catch(() => setBackendStatus("error"));
  }, [sessionId]);

  async function handleNewInteraction() {
    dispatch(resetInteraction());
    dispatch(resetChat());
    try {
      await resetInteractionApi(sessionId);
    } catch {
    }
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-header__brand">
          <span className="app-header__logo">RX</span>
          <div>
            <h1>AI-First CRM · HCP Module</h1>
            <p>Log Interaction</p>
          </div>
        </div>
        <div className="app-header__actions">
          {backendStatus === "error" && (
            <span className="status-pill status-pill--error">Backend unreachable</span>
          )}
          <button className="btn btn--ghost" onClick={handleNewInteraction}>
            + New Interaction
          </button>
        </div>
      </header>

      <main className="app-split">
        <section className="app-split__panel app-split__panel--form">
          <InteractionForm />
        </section>
        <section className="app-split__panel app-split__panel--chat">
          <AIAssistantChat sessionId={sessionId} />
        </section>
      </main>
    </div>
  );
}
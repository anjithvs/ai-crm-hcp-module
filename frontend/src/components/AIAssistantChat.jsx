import { useEffect, useRef, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { sendChatMessage } from "../api.js";
import { addMessage, setLoading } from "../store/chatSlice.js";
import { setInteraction } from "../store/interactionSlice.js";
import "./AIAssistantChat.css";

export default function AIAssistantChat({ sessionId }) {
  const dispatch = useDispatch();
  const messages = useSelector((s) => s.chat.messages);
  const isLoading = useSelector((s) => s.chat.isLoading);
  const [draft, setDraft] = useState("");
  const listRef = useRef(null);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, isLoading]);

  async function handleSend() {
    const text = draft.trim();
    if (!text || isLoading) return;

    const history = messages
      .filter((m) => m.id !== "greeting")
      .map((m) => ({ role: m.role, content: m.content }));

    dispatch(addMessage({ role: "user", content: text }));
    setDraft("");
    dispatch(setLoading(true));

    try {
      const { reply, interaction } = await sendChatMessage(sessionId, text, history);
      dispatch(setInteraction(interaction));
      dispatch(addMessage({ role: "assistant", content: reply, tone: "success" }));
    } catch (err) {
      const detail = err?.response?.data?.detail || "Something went wrong reaching the AI assistant.";
      dispatch(addMessage({ role: "assistant", content: detail, tone: "error" }));
    } finally {
      dispatch(setLoading(false));
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="ai-chat">
      <div className="ai-chat__header">
        <span className="ai-chat__avatar">🤖</span>
        <div>
          <h2>AI Assistant</h2>
          <p>Log Interaction details here via chat</p>
        </div>
      </div>

      <div className="ai-chat__messages" ref={listRef}>
        {messages.map((m) => (
          <div key={m.id} className={`bubble bubble--${m.role} bubble--${m.tone || "default"}`}>
            {m.content}
          </div>
        ))}
        {isLoading && (
          <div className="bubble bubble--assistant bubble--default bubble--typing">
            <span className="dot" />
            <span className="dot" />
            <span className="dot" />
          </div>
        )}
      </div>

      <div className="ai-chat__composer">
        <textarea
          rows={2}
          placeholder="Describe Interaction…"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button className="btn btn--send" onClick={handleSend} disabled={isLoading || !draft.trim()}>
          Log
        </button>
      </div>
    </div>
  );
}
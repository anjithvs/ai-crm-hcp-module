import { useSelector } from "react-redux";
import "./InteractionForm.css";

const SENTIMENT_OPTIONS = [
  { value: "Positive", emoji: "🙂", color: "positive" },
  { value: "Neutral", emoji: "😐", color: "neutral" },
  { value: "Negative", emoji: "🙁", color: "negative" },
];

function noop() {}

function Field({ label, changed, children }) {
  return (
    <div className={`field ${changed ? "field--changed" : ""}`}>
      <label className="field__label">{label}</label>
      {children}
    </div>
  );
}

export default function InteractionForm() {
  const data = useSelector((s) => s.interaction.data);
  const changedFields = useSelector((s) => s.interaction.recentlyChangedFields);
  const changed = (key) => changedFields.includes(key);

  return (
    <div className="interaction-form">
      <div className="interaction-form__title-row">
        <div>
          <h2>Log HCP Interaction</h2>
          <p className="interaction-form__hint">
            🔒 This form is populated by the AI Assistant — describe the interaction in the chat panel to fill it in.
          </p>
        </div>
        {data.logged && <span className="badge badge--logged">✓ Logged</span>}
      </div>

      {data.compliance_flag && <div className="compliance-banner">{data.compliance_flag}</div>}

      <h3 className="section-heading">Interaction Details</h3>
      <div className="field-grid">
        <Field label="HCP Name" changed={changed("hcp_name")}>
          <input readOnly value={data.hcp_name ?? ""} placeholder="Awaiting AI input…" />
        </Field>
        <Field label="Interaction Type" changed={changed("interaction_type")}>
          <select disabled value={data.interaction_type ?? "Meeting"} onChange={noop}>
            {["Meeting", "Call", "Email", "Conference"].map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Date" changed={changed("date")}>
          <input readOnly value={data.date ?? ""} placeholder="—" />
        </Field>
        <Field label="Time" changed={changed("time")}>
          <input readOnly value={data.time ?? ""} placeholder="—" />
        </Field>
      </div>

      <Field label="Attendees" changed={changed("attendees")}>
        <div className="chip-row chip-row--empty-ok">
          {data.attendees.length === 0 && <span className="placeholder-text">Enter names or search…</span>}
          {data.attendees.map((name) => (
            <span className="chip" key={name}>
              {name}
            </span>
          ))}
        </div>
      </Field>

      <Field label="Topics Discussed" changed={changed("topics_discussed")}>
        <textarea readOnly value={data.topics_discussed ?? ""} placeholder="—" rows={3} />
      </Field>

      <h3 className="section-heading">Materials Shared / Samples Distributed</h3>
      <Field label="Materials Shared" changed={changed("materials_shared")}>
        <div className="chip-row">
          {data.materials_shared.length === 0 && <span className="placeholder-text">None recorded yet.</span>}
          {data.materials_shared.map((m) => (
            <span className="chip" key={m}>
              {m}
            </span>
          ))}
        </div>
        <button className="btn btn--disabled-hint" disabled title="Use the AI Assistant to add materials">
          🔍 Search/Add
        </button>
      </Field>

      <Field label="Samples Distributed" changed={changed("samples_distributed")}>
        <div className="chip-row">
          {data.samples_distributed.length === 0 && <span className="placeholder-text">No samples added.</span>}
          {data.samples_distributed.map((s, i) => (
            <span className="chip" key={`${s.name}-${i}`}>
              {s.name} × {s.quantity}
            </span>
          ))}
        </div>
        <button className="btn btn--disabled-hint" disabled title="Use the AI Assistant to log samples">
          + Add Sample
        </button>
      </Field>

      <Field label="Observed / Inferred HCP Sentiment" changed={changed("sentiment")}>
        <div className="sentiment-row">
          {SENTIMENT_OPTIONS.map((opt) => (
            <label key={opt.value} className={`sentiment-option sentiment-option--${opt.color}`}>
              <input
                type="radio"
                name="sentiment"
                checked={data.sentiment === opt.value}
                disabled
                onChange={noop}
              />
              <span>
                {opt.emoji} {opt.value}
              </span>
            </label>
          ))}
        </div>
      </Field>

      <Field label="Outcomes" changed={changed("outcomes")}>
        <textarea readOnly value={data.outcomes ?? ""} placeholder="Key outcomes or agreements…" rows={2} />
      </Field>

      <Field label="Follow-up Actions" changed={changed("follow_up_actions")}>
        <textarea
          readOnly
          value={data.follow_up_actions ?? ""}
          placeholder="Ask the AI Assistant to suggest a follow-up…"
          rows={2}
        />
      </Field>
    </div>
  );
}
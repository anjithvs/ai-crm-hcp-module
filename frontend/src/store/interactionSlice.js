import { createSlice } from "@reduxjs/toolkit";

export const EMPTY_INTERACTION = {
  hcp_name: null,
  interaction_type: "Meeting",
  date: null,
  time: null,
  attendees: [],
  topics_discussed: null,
  materials_shared: [],
  samples_distributed: [],
  sentiment: null,
  outcomes: null,
  follow_up_actions: null,
  compliance_flag: null,
  logged: false,
};

const initialState = {
  data: EMPTY_INTERACTION,
  recentlyChangedFields: [],
};

function diffFields(prev, next) {
  const changed = [];
  for (const key of Object.keys(EMPTY_INTERACTION)) {
    const before = JSON.stringify(prev[key] ?? null);
    const after = JSON.stringify(next[key] ?? null);
    if (before !== after) changed.push(key);
  }
  return changed;
}

const interactionSlice = createSlice({
  name: "interaction",
  initialState,
  reducers: {
    setInteraction(state, action) {
      const next = { ...EMPTY_INTERACTION, ...action.payload };
      state.recentlyChangedFields = diffFields(state.data, next);
      state.data = next;
    },
    clearRecentlyChanged(state) {
      state.recentlyChangedFields = [];
    },
    resetInteraction(state) {
      state.data = EMPTY_INTERACTION;
      state.recentlyChangedFields = [];
    },
  },
});

export const { setInteraction, clearRecentlyChanged, resetInteraction } = interactionSlice.actions;
export default interactionSlice.reducer;
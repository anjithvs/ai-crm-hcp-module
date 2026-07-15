import { createSlice } from "@reduxjs/toolkit";

const GREETING = {
  id: "greeting",
  role: "assistant",
  content:
    'Log interaction details here (e.g., "Met Dr. Smith, discussed Prodo-X efficacy, positive sentiment, shared brochure") or ask for help.',
  tone: "info",
};

const initialState = {
  messages: [GREETING],
  isLoading: false,
};

const chatSlice = createSlice({
  name: "chat",
  initialState,
  reducers: {
    addMessage: {
      reducer(state, action) {
        state.messages.push(action.payload);
      },
      prepare({ role, content, tone = "default" }) {
        return {
          payload: {
            id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
            role,
            content,
            tone,
          },
        };
      },
    },
    setLoading(state, action) {
      state.isLoading = action.payload;
    },
    resetChat(state) {
      state.messages = [GREETING];
      state.isLoading = false;
    },
  },
});

export const { addMessage, setLoading, resetChat } = chatSlice.actions;
export default chatSlice.reducer;
import { configureStore } from "@reduxjs/toolkit";
import chatReducer from "./chatSlice.js";
import interactionReducer from "./interactionSlice.js";

export const store = configureStore({
  reducer: {
    interaction: interactionReducer,
    chat: chatReducer,
  },
});
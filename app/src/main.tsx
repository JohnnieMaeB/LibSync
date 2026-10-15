import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./theme/tokens.css";
import "./theme/global.css";
import App from "./App.tsx";
import { initNativeShell, registerServiceWorker } from "./native";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);

void initNativeShell();
void registerServiceWorker();

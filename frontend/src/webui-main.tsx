import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import WebUIApp from "./webui/WebUIApp";
import "./webui/webui.css";

document.title = "Pixie — Eval Dashboard";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <WebUIApp />
  </StrictMode>,
);

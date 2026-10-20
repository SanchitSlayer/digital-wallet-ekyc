import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router";

import { App } from "./App";
import { AuthProvider } from "./features/auth/AuthContext";
import "./index.css";

const root = document.getElementById("root");
if (root === null) {
  throw new Error("index.html is missing the #root element the app mounts into");
}

createRoot(root).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
);

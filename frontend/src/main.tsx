import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import "./index.css";
import App from "./App";
import Landing from "./pages/Landing";
import Dashboard from "./pages/Dashboard";
import Ask from "./pages/Ask";
import AgentWorkspace from "./pages/AgentWorkspace";
import HumanReview from "./pages/HumanReview";
import FinalGuidance from "./pages/FinalGuidance";
import Setup from "./pages/Setup";
import ChatSimulator from "./pages/ChatSimulator";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route element={<App />}>
          <Route path="/" element={<Landing />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/chat-demo" element={<ChatSimulator />} />
          <Route path="/ask" element={<Ask />} />
          <Route path="/agents" element={<AgentWorkspace />} />
          <Route path="/agents/:questionId" element={<AgentWorkspace />} />
          <Route path="/review" element={<HumanReview />} />
          <Route path="/review/:questionId" element={<HumanReview />} />
          <Route path="/guidance" element={<FinalGuidance />} />
          <Route path="/guidance/:questionId" element={<FinalGuidance />} />
          <Route path="/setup" element={<Setup />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);

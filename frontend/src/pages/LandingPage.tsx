import "../styles/LandingPage.css";
import Button from "../components/Buttons";
import { createGuestSession } from "../services/auth";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function LandingPage() {
  const navigate = useNavigate();
  const [creating, setCreating] = useState(false);

  const handleLetsGo = async () => {
    if (creating) return;
    const existingSessionId = localStorage.getItem("guest_session_id");
    if (existingSessionId) {
      navigate("/dashboard");
      return;
    }

    setCreating(true);
    try {
      const guest = await createGuestSession();

      // Save session locally
      localStorage.setItem("guest_session_id", guest.session_id);

      // Navigate to dashboard
      navigate("/dashboard");
    } catch (err) {
      console.error(err);
      alert("Failed to start session. Please try again.");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="landing">
      <div className="landing-left">
        <h1 className="landing-title">Ask questions with confidence</h1>

        <p className="landing-desc">
          GroundedAI helps you ask questions and get answers that are strictly
          grounded in your own documents — no hallucinations, no guessing,
          just verifiable answers with citations.
        </p>

        <div className="landing-how">
          <h3>How it works</h3>
          <ul>
            <li>Upload your documents</li>
            <li>We extract, chunk, and embed the content</li>
            <li>Ask questions and get cited answers</li>
          </ul>
        </div>
      </div>

      <div className="landing-right">
        <div className="cta-card">
          <h2>Ready to know the answers?</h2>
          <p>Your documents already have them.</p>

          <Button
            label={creating ? "Starting..." : "Let's Go"}
            onClick={handleLetsGo}
            disabled={creating}
          />
        </div>
      </div>
    </div>
  );
}

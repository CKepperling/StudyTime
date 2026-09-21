import { useEffect, useState } from "react";
import { checkHealth } from "../api/health";

export default function Home() {
  const [status, setStatus] = useState("checking");

  useEffect(() => {
    checkHealth()
      .then(() => setStatus("connected"))
      .catch(() => setStatus("unreachable"));
  }, []);

  return (
    <div>
      <h1>Documents</h1>
      <p>
        Backend status:{" "}
        <strong style={{ color: status === "connected" ? "#2f6b3d" : "#9c3b2c" }}>
          {status}
        </strong>
      </p>
    </div>
  );
}

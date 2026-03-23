const express = require("express");
const http = require("http");
const { Server } = require("socket.io");
const cors = require("cors");
const fs = require("fs");
const path = require("path");

const app = express();
const server = http.createServer(app);

const PYTHON_URL = process.env.PYTHON_URL || "http://127.0.0.1:5000";
const PORT = process.env.PORT || 3001;

// Accept any localhost origin (works regardless of which port Vite uses)
const corsOptions = {
  origin: (origin, callback) => {
    if (!origin || /^http:\/\/localhost(:\d+)?$/.test(origin)) {
      callback(null, true);
    } else {
      callback(new Error("Not allowed by CORS"));
    }
  },
  methods: ["GET", "POST", "PUT"],
};

// --- CORS ---
app.use(cors(corsOptions));
app.use(express.json());

// --- Socket.IO ---
const io = new Server(server, {
  cors: corsOptions,
});

// --- Persistence ---
const DATA_FILE = path.join(__dirname, "debates_data.json");

function saveData() {
  try {
    fs.writeFileSync(DATA_FILE, JSON.stringify({ debates, sessions }, null, 2));
  } catch (err) {
    console.error("Could not save data:", err.message);
  }
}

function loadData() {
  try {
    if (fs.existsSync(DATA_FILE)) {
      const data = JSON.parse(fs.readFileSync(DATA_FILE, "utf8"));
      Object.assign(debates, data.debates || {});
      Object.assign(sessions, data.sessions || {});
      console.log(`Loaded ${Object.keys(debates).length} persisted debate(s).`);
    }
  } catch (err) {
    console.error("Could not load persisted data:", err.message);
  }
}

// --- In-Memory Store ---
const debates = {};        // debateId -> debate object
const sessions = {};       // debateId -> python session_id
const exchangeBuffers = {}; // debateId -> { forMessage, againstMessage }

loadData();

// ---------------------------------------------------------------
// REST ENDPOINTS
// ---------------------------------------------------------------

// GET / — Health check
app.get("/", (req, res) => {
  res.json({ status: "ok", message: "Debate Proctor API is running" });
});

// POST /api/debates — Create a new debate room
app.post("/api/debates", async (req, res) => {
  const { id, topic, debater1, position } = req.body;

  if (!id || !topic || !debater1) {
    return res.status(400).json({ error: "id, topic, and debater1 are required" });
  }

  const debate = {
    id,
    topic,
    debater1: { id: debater1.id, username: debater1.username, position: position || "for" },
    debater2: { id: "", username: "Waiting...", position: position === "for" ? "against" : "for" },
    status: "pending",
    currentRound: 1,
    totalRounds: 3,
    currentTurn: "debater1",
    timeRemaining: 600,
    startedAt: new Date().toISOString(),
    messages: [],
    scores: { debater1: 0, debater2: 0 },
  };

  debates[id] = debate;
  saveData();

  // Create a session on the Python AI backend (optional — graceful fallback)
  try {
    const response = await fetch(`${PYTHON_URL}/api/start_session`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic: topic.title }),
    });
    if (response.ok) {
      const data = await response.json();
      sessions[id] = data.session_id;
      saveData();
      console.log(`AI session created for debate ${id}: ${data.session_id}`);
    }
  } catch {
    console.log("Python backend unavailable — AI evaluation will be skipped.");
  }

  res.status(201).json(debate);
});

// GET /api/debates/:id — Get a debate by ID
app.get("/api/debates/:id", (req, res) => {
  const debate = debates[req.params.id];
  if (!debate) {
    return res.status(404).json({ error: "Debate not found" });
  }
  res.json(debate);
});

// PUT /api/debates/:id/join — Second debater joins a debate
app.put("/api/debates/:id/join", (req, res) => {
  const debate = debates[req.params.id];
  if (!debate) {
    return res.status(404).json({ error: "Debate not found" });
  }
  if (debate.debater2 && debate.debater2.id && debate.debater2.id !== "") {
    return res.status(400).json({ error: "Debate already has two debaters" });
  }

  const { debater2 } = req.body;
  const oppositePosition = debate.debater1.position === "for" ? "against" : "for";

  debate.debater2 = {
    id: debater2.id,
    username: debater2.username,
    position: oppositePosition,
  };
  debate.status = "live";

  debates[debate.id] = debate;
  saveData();

  // Notify everyone in the room that the second debater has joined
  io.to(debate.id).emit("debate-updated", debate);

  res.json(debate);
});

// ---------------------------------------------------------------
// SOCKET.IO
// ---------------------------------------------------------------

io.on("connection", (socket) => {
  console.log(`Client connected: ${socket.id}`);

  // Join a debate room
  socket.on("join-debate", (debateId) => {
    socket.join(debateId);
    console.log(`Socket ${socket.id} joined debate room: ${debateId}`);
  });

  // Receive and broadcast a message, with optional AI fact-check
  socket.on("sendMsg", async ({ debateId, message }) => {
    console.log(`Message received in debate ${debateId}:`, message.message);

    let factCheckStatus = message.factCheckStatus || "unverified";

    // Try AI evaluation if we have a Python session for this debate
    const sessionId = sessions[debateId];
    if (sessionId) {
      try {
        const debate = debates[debateId];
        // Determine if the debater is arguing in favour of the topic
        let inFavour = true;
        if (debate) {
          const isDebater1 = message.debaterId === debate.debater1.id;
          const position = isDebater1
            ? debate.debater1.position
            : debate.debater2.position;
          inFavour = position === "for";
        }

        const response = await fetch(`${PYTHON_URL}/api/evaluate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: sessionId,
            user_id: message.debaterId,
            statement: message.message,
            in_favour: inFavour,
          }),
        });

        if (response.ok) {
          const data = await response.json();
          const { factual_accuracy, relevance_score } = data.evaluation;
          if (factual_accuracy >= 70 && relevance_score >= 70) {
            factCheckStatus = "verified";
          } else if (factual_accuracy >= 40 || relevance_score >= 40) {
            factCheckStatus = "questionable";
          } else {
            factCheckStatus = "unverified";
          }
          console.log(
            `AI evaluation: accuracy=${factual_accuracy}, relevance=${relevance_score} → ${factCheckStatus}`
          );
        }
      } catch {
        console.log("AI evaluation failed — using client-side status.");
      }
    }

    // Determine whose turn is next so all clients can sync their turn state
    const debateForTurn = debates[debateId];
    let nextTurn = "debater2";
    if (debateForTurn && message.debaterId === debateForTurn.debater2?.id) {
      nextTurn = "debater1";
    }

    const broadcastMessage = { ...message, factCheckStatus, nextTurn };

    // Persist message and sync currentTurn in server state
    if (debates[debateId]) {
      debates[debateId].messages = debates[debateId].messages || [];
      debates[debateId].messages.push(broadcastMessage);
      debates[debateId].currentTurn = nextTurn;
      saveData();
    }

    io.to(debateId).emit("real-time-sync-message", broadcastMessage);

    // --- Exchange scoring: fire after each complete For+Against pair ---
    const exchDebate = debates[debateId];
    if (exchDebate && exchDebate.debater2?.id) {
      const isDebater1msg = message.debaterId === exchDebate.debater1.id;
      const senderPosition = isDebater1msg ? exchDebate.debater1.position : exchDebate.debater2.position;

      if (!exchangeBuffers[debateId]) {
        exchangeBuffers[debateId] = { forMessage: null, againstMessage: null };
      }

      if (senderPosition === "for") {
        exchangeBuffers[debateId].forMessage = broadcastMessage;
      } else {
        exchangeBuffers[debateId].againstMessage = broadcastMessage;
      }

      const { forMessage, againstMessage } = exchangeBuffers[debateId];
      if (forMessage && againstMessage) {
        // Full exchange collected — reset buffer first
        exchangeBuffers[debateId] = { forMessage: null, againstMessage: null };

        // Lazily create a Python session if one wasn't created at debate start
        if (!sessions[debateId]) {
          try {
            const sessRes = await fetch(`${PYTHON_URL}/api/start_session`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ topic: exchDebate.topic.title }),
            });
            if (sessRes.ok) {
              const sessData = await sessRes.json();
              sessions[debateId] = sessData.session_id;
              saveData();
              console.log(`Lazy AI session created for debate ${debateId}: ${sessData.session_id}`);
            }
          } catch {
            console.log("Python backend unavailable — exchange scoring skipped.");
          }
        }

        const sessionId2 = sessions[debateId];
        if (sessionId2) {
          try {
            const scoreRes = await fetch(`${PYTHON_URL}/api/score_exchange`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                session_id: sessionId2,
                for_user_id: forMessage.debaterId,
                for_statement: forMessage.message,
                against_user_id: againstMessage.debaterId,
                against_statement: againstMessage.message,
              }),
            });

            if (scoreRes.ok) {
              const scoreData = await scoreRes.json();
              const { for_points, against_points, exchange_winner, reasoning } = scoreData.score;

              // Map for/against scores back to debater1/debater2 slots
              const forIsDebater1 = forMessage.debaterId === exchDebate.debater1.id;
              debates[debateId].scores = debates[debateId].scores || { debater1: 0, debater2: 0 };
              if (forIsDebater1) {
                debates[debateId].scores.debater1 = Math.round((debates[debateId].scores.debater1 + for_points) * 10) / 10;
                debates[debateId].scores.debater2 = Math.round((debates[debateId].scores.debater2 + against_points) * 10) / 10;
              } else {
                debates[debateId].scores.debater1 = Math.round((debates[debateId].scores.debater1 + against_points) * 10) / 10;
                debates[debateId].scores.debater2 = Math.round((debates[debateId].scores.debater2 + for_points) * 10) / 10;
              }
              saveData();

              io.to(debateId).emit("exchange-scored", {
                scores: debates[debateId].scores,
                exchange: {
                  forUser: { id: forMessage.debaterId, points: for_points },
                  againstUser: { id: againstMessage.debaterId, points: against_points },
                  winner: exchange_winner,
                  reasoning,
                },
              });

              console.log(`Exchange scored [${debateId}]: for=${for_points}, against=${against_points}, winner=${exchange_winner}`);
            }
          } catch (err) {
            console.log("Exchange scoring failed:", err.message);
          }
        }
      }
    }
  });

  socket.on("disconnect", () => {
    console.log(`Client disconnected: ${socket.id}`);
  });
});

// ---------------------------------------------------------------
// START
// ---------------------------------------------------------------
server.listen(PORT, () => {
  console.log(`Debate Proctor backend running at http://localhost:${PORT}`);
  console.log(`Accepting requests from any localhost origin`);
  console.log(`Python AI backend expected at: ${PYTHON_URL}`);
});

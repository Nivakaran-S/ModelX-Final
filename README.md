# 🇱🇰 ModelX Intelligence Platform

**Real-Time Situational Awareness for Sri Lanka**

A multi-agent AI system that aggregates intelligence from 47+ data sources to provide risk analysis and opportunity detection for businesses operating in Sri Lanka.

---

## 🎯 Hackathon Features

✅ **6 Domain Agents** running in parallel:
- Social Media Monitor (Reddit, Twitter, Facebook)
- Political Intelligence (Gazette, Parliament)
- Economic Analysis (CSE Stock Market + Technical Indicators)
- Meteorological Alerts (DMC Weather)
- Intelligence Agent (Brand Monitoring)
- Data Retrieval Orchestrator (Web Scraping)

✅ **Real-Time Dashboard** with:
- Live Intelligence Feed
- Operational Risk Radar
- Market Predictions with Moving Averages
- Risk & Opportunity Classification

✅ **Technical Innovations**:
- Fan-Out/Fan-In Graph Architecture
- Custom State Reducers
- WebSocket Live Streaming
- Parallel Agent Execution

---

## 🚀 Quick Start (5 Minutes)

### Prerequisites
- Python 3.11+
- Node.js 18+
- Groq API Key ([Get Free Key](https://console.groq.com))

### Installation

```bash
# 1. Clone repository
git clone <your-repo>
cd modelx

# 2. Create .env file
cp .env.template .env
# Add your GROQ_API_KEY to .env

# 3. Make startup script executable
chmod +x start.sh

# 4. Launch platform
./start.sh
```

**That's it!** Open http://localhost:3000 in your browser.

---

## 📊 Architecture

```
┌─────────────────────────────────────────┐
│         Mother Graph (ModelX)            │
│  ┌─────────────────────────────────┐   │
│  │   Graph Initiator (Reset)       │   │
│  └──────────┬──────────────────────┘   │
│             │ Fan-Out                    │
│    ┌────────┼────────┬────────┐        │
│    ▼        ▼        ▼        ▼        │
│  Social  Economic  Political  Meteo    │
│  Agent    Agent    Agent     Agent     │
│    │        │        │        │        │
│    └────────┴────────┴────────┘        │
│             │ Fan-In                    │
│    ┌────────▼────────────┐             │
│    │  Feed Aggregator    │             │
│    │  (Rank & Dedupe)    │             │
│    └────────┬────────────┘             │
│    ┌────────▼────────────┐             │
│    │  Data Refresher     │             │
│    │  (Update Dashboard) │             │
│    └────────┬────────────┘             │
│    ┌────────▼────────────┐             │
│    │  Router (Loop/End)  │             │
│    └─────────────────────┘             │
└─────────────────────────────────────────┘
```

---

## 🔧 API Endpoints

### REST API
- `GET /api/status` - System health
- `GET /api/dashboard` - Risk metrics
- `GET /api/feed` - Latest events

### WebSocket
- `ws://localhost:8000/ws` - Real-time updates

---

## 📈 Dashboard Metrics Explained

### Operational Risk Radar
- **Logistics Friction**: Route risk from mobility data
- **Compliance Volatility**: Regulatory risk from political changes
- **Market Instability**: Volatility from economic indicators
- **Opportunity Index**: Growth signals from positive events

### Event Classification
- **Risk**: Negative market movements, compliance issues, disasters
- **Opportunity**: Growth signals, policy improvements, market uptrends

---

## 🎨 Technology Stack

### Backend
- **LangGraph**: Multi-agent orchestration
- **FastAPI**: Real-time API with WebSockets
- **Groq**: High-speed LLM inference
- **BeautifulSoup**: Web scraping

### Frontend
- **Next.js 14**: React framework
- **TailwindCSS**: UI styling
- **Framer Motion**: Animations
- **Recharts**: Data visualization

---

## 🏆 Hackathon Winning Features

### 1. **Mathematically Sound Analysis**
- Moving Average calculations for CSE stocks
- Statistical trend detection
- Confidence scoring with severity boosts

### 2. **Real Architecture**
- Custom state reducers for parallel execution
- Proper Fan-Out/Fan-In pattern
- Loop control with reset mechanism

### 3. **Live Demo Ready**
- WebSocket streaming for instant updates
- Graceful degradation (REST fallback)
- Production-ready error handling

### 4. **Sri Lankan Context**
- Localized to Sri Lankan data sources
- CSE market integration
- Government gazette monitoring
- DMC weather alerts

---

## 🐛 Troubleshooting

### Backend won't start
```bash
# Check if port 8000 is in use
lsof -ti:8000 | xargs kill -9

# Restart
python backend/api/main.py
```

### Frontend connection issues
```bash
# Verify backend is running
curl http://localhost:8000/api/status

# Check WebSocket
wscat -c ws://localhost:8000/ws
```

### No data appearing
- Graph takes 30-60 seconds for first run
- Check browser console for WebSocket connection
- Verify GROQ_API_KEY is set in .env

---

## 📝 Project Structure

```
modelx/
├── backend/
│   └── api/
│       └── main.py          # FastAPI server
├── frontend/
│   └── app/
│       ├── hooks/
│       │   └── use-modelx-data.ts  # Real-time data hook
│       └── components/
│           └── dashboard/
│               ├── DashboardOverview.tsx
│               └── StockPredictions.tsx
├── src/
│   ├── graphs/
│   │   └── ModelXGraph.py   # Mother graph
│   ├── nodes/               # Agent implementations
│   ├── states/              # State definitions
│   └── utils/
│       └── utils.py         # Scraping tools
├── docker-compose.yml
├── start.sh                 # Demo launcher
└── requirements.txt
```

---

## 🎯 Demo Script for Judges

1. **Show Real-Time Feed** (30 seconds)
   - Point to live WebSocket indicator
   - Highlight auto-updating timestamps
   - Show event classification (Risk/Opportunity)

2. **Explain Architecture** (1 minute)
   - Draw Fan-Out/Fan-In on whiteboard
   - Mention parallel execution
   - Highlight custom state reducers

3. **Show Market Analysis** (1 minute)
   - Point to Moving Average calculation
   - Explain bullish/bearish detection
   - Show opportunity classification

4. **Demonstrate Scalability** (30 seconds)
   - Show 6 agents running in parallel
   - Mention 47+ data sources
   - Highlight continuous loop mode

---

## 📄 License

MIT License - Built for Hackathon

---

## 🙏 Acknowledgments

- **Groq** for high-speed LLM inference
- **LangGraph** for agent orchestration
- Sri Lankan government for open data sources

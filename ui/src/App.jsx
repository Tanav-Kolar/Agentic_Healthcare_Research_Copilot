import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import ChatPanel from './components/ChatPanel';
import EvidencePanel from './components/EvidencePanel';
import EvidenceTable from './components/EvidenceTable';
import { AlertCircle, Terminal } from 'lucide-react';

const API_BASE_URL = 'http://localhost:8000';

function App() {
  const [messages, setMessages] = useState([]);
  const [filters, setFilters] = useState({
    year_from: 2022,
    study_types: ['RCT', 'Meta-analysis', 'Guideline']
  });
  const [loading, setLoading] = useState(false);
  const [activeResearch, setActiveResearch] = useState(null);

  const handleSendMessage = async (text) => {
    // Add user message to UI
    const userMsg = { role: 'user', content: text };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: text,
          filters: filters
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to fetch evidence. Ensure backend is running.');
      }

      const data = await response.json();

      // Add assistant response
      const assistantMsg = {
        role: 'assistant',
        content: data.answer
      };
      setMessages((prev) => [...prev, assistantMsg]);
      setActiveResearch(data);
    } catch (err) {
      setMessages((prev) => [...prev, {
        role: 'assistant',
        content: `❌ Error: ${err.message}`
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container">
      {/* Disclaimer Banner */}
      <div className="fixed top-0 left-0 right-0 h-8 bg-error/20 border-b border-error/30 z-50 flex items-center justify-center gap-2">
        <AlertCircle size={14} className="text-error" />
        <span className="text-[10px] font-bold text-error uppercase tracking-widest">
          Research & Education Only — Not for Clinical Decision Making
        </span>
      </div>

      {/* Main Layout (below banner) */}
      <div className="mt-8 contents">
        <Sidebar filters={filters} setFilters={setFilters} />

        <div className="main-content">
          <ChatPanel
            messages={messages}
            onSendMessage={handleSendMessage}
            loading={loading}
          />
          {activeResearch && <EvidenceTable evidence={activeResearch.evidence_table} />}
        </div>

        <EvidencePanel
          quotes={activeResearch?.quotes || []}
          recentChanges={activeResearch?.changed_in_last_24_months || []}
        />
      </div>

      {/* Backend Status Indicator */}
      <div className="fixed bottom-4 left-4 p-2 glass-panel flex items-center gap-2 opacity-50 hover:opacity-100 transition-opacity">
        <Terminal size={14} />
        <span className="text-[10px] font-mono">API: {API_BASE_URL}</span>
        <div className="w-2 h-2 rounded-full bg-success"></div>
      </div>
    </div>
  );
}

export default App;

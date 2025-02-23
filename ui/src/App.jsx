import React, { useState, useEffect } from 'react';
import axios from 'axios';
import io from 'socket.io-client';
import './App.css';

function App() {
  const [prompt, setPrompt] = useState('');
  const [promptHistory, setPromptHistory] = useState([]);
  const [fineTuneData, setFineTuneData] = useState({ manual_diffs: [], prompt_history: [] });

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!prompt) return;

    try {
      const response = await axios.post('http://localhost:5001/prompt', { prompt });
      setPromptHistory(response.data.prompt_history);
      setPrompt(''); // Clear input
    } catch (error) {
      console.error('Error submitting prompt:', error);
      alert('Failed to submit prompt. Check the server logs.');
    }
  };

  // WebSocket setup (unchanged for brevity)
  useEffect(() => {
    const socket = io('http://localhost:5001', {
      path: '/socket.io',
      transports: ['websocket'],
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000
    });

    socket.on('update_finetune', (data) => {
      console.log('update_finetune', data);
      setFineTuneData(data);
    });

    socket.on('connect', () => {
      console.log('Connected to WebSocket');
    });

    socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error);
    });

    return () => socket.disconnect();
  }, []);

  return (
    <div className="App">
      <div className="flex-container">
        {/* Lovable Monitor UI Header Block */}
        <header className="App-header">
          <h1>Lovable Monitor UI</h1>
          <p>Lovable is your superhuman full stack engineer.</p>
          <form onSubmit={handleSubmit} className="prompt-form">
            <input
              type="text"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Ask Lovable to create a dashboard to..."
              className="prompt-input"
            />
            <button type="submit" className="submit-button">Send</button>
          </form>
        </header>

        <div className="main-content">
          <div className="prompt-history">
            <h2>Current Prompts</h2>
            {promptHistory.map((p, index) => (
              <div key={index} className="prompt-card">
                <span className="prompt-number">#{index + 1}</span> - {p}
              </div>
            ))}
          </div>

          <div className="manual-changes">
            <h2>Manual Changes</h2>
            {fineTuneData.manual_diffs.map((diff, index) => (
              <div key={index} className="diff-card">
                {diff.map((item, i) => (
                  <div key={i}>{item}</div>
                ))}
              </div>
            ))}
            <h3>Associated Prompts</h3>
            {fineTuneData.prompt_history.map((p, index) => (
              <div key={index} className="manual-changes-prompt-card">
                <span className="prompt-number">#{index + 1}</span> - {p}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
import React, { useState } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [prompt, setPrompt] = useState('');
  const [promptHistory, setPromptHistory] = useState([]);

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

  return (
    <div className="App">
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
        <div className="prompt-history">
          <h2>Current Prompts</h2>
          {promptHistory.map((p, index) => (
            <div key={index} className="prompt-card">
              <span className="prompt-number">#{index + 1}</span> - {p}
            </div>
          ))}
        </div>
      </header>
    </div>
  );
}

export default App;
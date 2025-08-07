import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import reportWebVitals from './reportWebVitals';

// Import Django integration for standalone components
import './django-integration';

// Check if this is running in standalone mode (has root element) or Django integration mode
const rootElement = document.getElementById('root');

if (rootElement) {
  // Standalone React app mode (for development)
  const root = ReactDOM.createRoot(rootElement);
  root.render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  );
}

// Django integration is handled by the django-integration.ts file
// which sets up the global GMAReact object and auto-mounts components

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();

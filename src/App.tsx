import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import './App.css';
import LandingPage from './pages/landingpage';

function App(): JSX.Element {
  return (
    <Router>
      <Routes>
      <Route path="/" element={<LandingPage />} />
      </Routes>
    </Router>
  );
}

export default App; 
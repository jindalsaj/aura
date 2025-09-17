import React from 'react';
import { ThemeProvider } from '@mui/material/styles';
import { CssBaseline } from '@mui/material';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { theme } from './theme';
import Login from './components/Login';
import Register from './components/Register';
import AuthCallback from './components/AuthCallback';
import RootHandler from './components/RootHandler';
import Dashboard from './components/Dashboard';
import Chat from './components/Chat';
import Properties from './components/Properties';
import DataSources from './components/DataSources';
import Onboarding from './components/Onboarding';
import Layout from './components/Layout';
import PageTracker from './components/PageTracker';
import { AuthProvider, useAuth } from './contexts/AuthContext';

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated } = useAuth();
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" />;
};

const PublicRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated } = useAuth();
  return !isAuthenticated ? <>{children}</> : <Navigate to="/app/dashboard" />;
};

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AuthProvider>
        <Router>
          <PageTracker />
          <Routes>
            <Route path="/login" element={
              <PublicRoute>
                <Login />
              </PublicRoute>
            } />
            <Route path="/register" element={
              <PublicRoute>
                <Register />
              </PublicRoute>
            } />
            <Route path="/auth/callback" element={<AuthCallback />} />
            <Route path="/callback" element={<AuthCallback />} />
            <Route path="/dashboard" element={<Navigate to="/app/dashboard" />} />
            <Route path="/" element={<RootHandler />} />
            <Route path="/app" element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }>
              <Route index element={<Navigate to="/app/dashboard" />} />
              <Route path="dashboard" element={<Dashboard />} />
              <Route path="chat" element={<Chat />} />
              <Route path="properties" element={<Properties />} />
              <Route path="data-sources" element={<DataSources />} />
            </Route>
            <Route path="/onboarding" element={
              <ProtectedRoute>
                <Onboarding />
              </ProtectedRoute>
            } />
          </Routes>
        </Router>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
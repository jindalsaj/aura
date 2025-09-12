import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { Container, Box, Typography, CircularProgress, Alert } from '@mui/material';
import api from '../services/api';
import { useAuth } from '../contexts/AuthContext';

const RootHandler: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const handleCallback = async () => {
      const code = searchParams.get('code');
      const error = searchParams.get('error');

      // If there's an OAuth error, show it
      if (error) {
        setError('Authentication was cancelled or failed');
        setLoading(false);
        return;
      }

      // If there's a code, handle OAuth callback
      if (code) {
        try {
          // Exchange code for token
          const redirectUri = `${window.location.origin}/`;
          const response = await api.post('/api/auth/google/callback', {
            code,
            redirect_uri: redirectUri
          });

          const { access_token } = response.data;
          localStorage.setItem('access_token', access_token);

          // Redirect to dashboard
          navigate('/app/dashboard');
        } catch (err: any) {
          console.error('Auth callback error:', err);
          setError(err.response?.data?.detail || 'Authentication failed');
          setLoading(false);
        }
        return;
      }

      // If user is already authenticated, redirect to dashboard
      if (isAuthenticated) {
        navigate('/app/dashboard');
        return;
      }

      // Otherwise, redirect to login
      navigate('/login');
    };

    handleCallback();
  }, [searchParams, navigate, isAuthenticated]);

  if (loading) {
    return (
      <Container component="main" maxWidth="sm">
        <Box
          sx={{
            marginTop: 8,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            minHeight: '50vh',
          }}
        >
          <CircularProgress size={60} />
          <Typography variant="h6" sx={{ mt: 2 }}>
            Loading...
          </Typography>
        </Box>
      </Container>
    );
  }

  if (error) {
    return (
      <Container component="main" maxWidth="sm">
        <Box
          sx={{
            marginTop: 8,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            minHeight: '50vh',
          }}
        >
          <Alert severity="error" sx={{ width: '100%', mb: 2 }}>
            {error}
          </Alert>
          <Typography variant="body2" color="text.secondary">
            You can try signing in again or contact support if the problem persists.
          </Typography>
        </Box>
      </Container>
    );
  }

  return null;
};

export default RootHandler;

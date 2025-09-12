import React, { useState, useEffect, useRef } from 'react';
import {
  Container,
  Typography,
  Box,
  TextField,
  Button,
  Paper,
  List,
  ListItem,
  Avatar,
  Chip,
  Alert,
} from '@mui/material';
import {
  Send as SendIcon,
  Person as PersonIcon,
  SmartToy as BotIcon,
} from '@mui/icons-material';
import api from '../services/api';
import { ChatMessage, ChatSession, ChatQuery, ChatResponse } from '../types';

const Chat: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [session, setSession] = useState<ChatSession | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    createOrGetSession();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const createOrGetSession = async () => {
    try {
      // Try to get existing sessions first
      const sessionsResponse = await api.get('/api/chat/sessions');
      const sessions = sessionsResponse.data;
      
      if (sessions.length > 0) {
        // Use the most recent session
        const recentSession = sessions[0];
        setSession(recentSession);
        setMessages(recentSession.messages || []);
      } else {
        // Create a new session
        const newSessionResponse = await api.post('/api/chat/sessions', {
          session_name: 'Main Chat',
        });
        setSession(newSessionResponse.data);
        setMessages([]);
      }
    } catch (error) {
      console.error('Error creating/getting session:', error);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim() || !session) return;

    const userMessage: ChatMessage = {
      id: Date.now(), // Temporary ID
      session_id: session.id,
      role: 'user',
      content: inputMessage,
      created_at: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setLoading(true);

    try {
      const query: ChatQuery = {
        message: inputMessage,
        session_id: session.id,
      };

      const response = await api.post<ChatResponse>('/api/chat/query', query);
      
      const assistantMessage: ChatMessage = {
        id: Date.now() + 1, // Temporary ID
        session_id: session.id,
        role: 'assistant',
        content: response.data.response,
        metadata: {
          sources: response.data.sources,
          confidence: response.data.confidence,
        },
        created_at: new Date().toISOString(),
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage: ChatMessage = {
        id: Date.now() + 1,
        session_id: session.id,
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        created_at: new Date().toISOString(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const formatMessage = (message: ChatMessage) => {
    return message.content.split('\n').map((line, index) => (
      <span key={index}>
        {line}
        {index < message.content.split('\n').length - 1 && <br />}
      </span>
    ));
  };

  return (
    <Container maxWidth="md">
      <Typography variant="h4" component="h1" gutterBottom>
        Chat with Aura
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Ask me anything about your properties, expenses, or documents
      </Typography>

      {messages.length === 0 && (
        <Alert severity="info" sx={{ mb: 3 }}>
          Start by asking me about your properties or connecting your data sources to get more personalized responses.
        </Alert>
      )}

      <Paper
        sx={{
          height: '60vh',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        <Box
          sx={{
            flex: 1,
            overflow: 'auto',
            p: 2,
          }}
        >
          <List>
            {messages.map((message) => (
              <ListItem
                key={message.id}
                sx={{
                  flexDirection: 'column',
                  alignItems: message.role === 'user' ? 'flex-end' : 'flex-start',
                  mb: 2,
                }}
              >
                <Box
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    mb: 1,
                    flexDirection: message.role === 'user' ? 'row-reverse' : 'row',
                  }}
                >
                  <Avatar
                    sx={{
                      bgcolor: message.role === 'user' ? 'primary.main' : 'secondary.main',
                      width: 32,
                      height: 32,
                      mr: message.role === 'user' ? 0 : 1,
                      ml: message.role === 'user' ? 1 : 0,
                    }}
                  >
                    {message.role === 'user' ? <PersonIcon /> : <BotIcon />}
                  </Avatar>
                  <Typography variant="caption" color="text.secondary">
                    {message.role === 'user' ? 'You' : 'Aura'}
                  </Typography>
                </Box>
                <Paper
                  sx={{
                    p: 2,
                    maxWidth: '70%',
                    bgcolor: message.role === 'user' ? 'primary.main' : 'background.paper',
                    color: message.role === 'user' ? 'white' : 'text.primary',
                    border: message.role === 'assistant' ? '1px solid' : 'none',
                    borderColor: 'divider',
                  }}
                >
                  <Typography variant="body1">
                    {formatMessage(message)}
                  </Typography>
                  {message.metadata?.sources && message.metadata.sources.length > 0 && (
                    <Box sx={{ mt: 1 }}>
                      <Typography variant="caption" color="text.secondary">
                        Sources:
                      </Typography>
                      {message.metadata.sources.map((source: any, index: number) => (
                        <Chip
                          key={index}
                          label={source.title || source.type}
                          size="small"
                          sx={{ ml: 1, mb: 0.5 }}
                        />
                      ))}
                    </Box>
                  )}
                </Paper>
              </ListItem>
            ))}
            {loading && (
              <ListItem>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <Avatar sx={{ bgcolor: 'secondary.main', mr: 1 }}>
                    <BotIcon />
                  </Avatar>
                  <Typography variant="body2" color="text.secondary">
                    Aura is typing...
                  </Typography>
                </Box>
              </ListItem>
            )}
            <div ref={messagesEndRef} />
          </List>
        </Box>

        <Box
          component="form"
          onSubmit={handleSendMessage}
          sx={{
            p: 2,
            borderTop: '1px solid',
            borderColor: 'divider',
            display: 'flex',
            gap: 1,
          }}
        >
          <TextField
            fullWidth
            variant="outlined"
            placeholder="Ask me about your properties, expenses, or documents..."
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            disabled={loading}
            size="small"
          />
          <Button
            type="submit"
            variant="contained"
            disabled={!inputMessage.trim() || loading}
            sx={{ minWidth: 'auto', px: 2 }}
          >
            <SendIcon />
          </Button>
        </Box>
      </Paper>
    </Container>
  );
};

export default Chat;

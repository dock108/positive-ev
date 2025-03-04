import React, { useState, useEffect, useRef } from 'react';
import {
  Container,
  Box,
  Typography,
  TextField,
  Button,
  Paper,
  List,
  ListItem,
  ListItemText,
  Divider,
  CircularProgress,
  Alert,
  IconButton,
  Snackbar,
  Tooltip,
} from '@mui/material';
import { 
  Send as SendIcon, 
  Info as InfoIcon, 
  Refresh as RefreshIcon,
  ErrorOutline as ErrorIcon,
  WifiOff as WifiOffIcon
} from '@mui/icons-material';
import axios from 'axios';
import { v4 as uuidv4 } from 'uuid';
import { useAuth } from '../context/AuthContext';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'bot';
  timestamp: Date;
  status?: 'sending' | 'sent' | 'error';
  retryCount?: number;
}

const MAX_RETRY_ATTEMPTS = 3;
const RETRY_DELAY = 2000; // 2 seconds

const Chat: React.FC = () => {
  const { user } = useAuth();
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessionId, setSessionId] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [recommendationCount, setRecommendationCount] = useState(0);
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');
  const [isInitialLoad, setIsInitialLoad] = useState(true);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  
  // Monitor online status
  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      setSnackbarMessage('You are back online');
      setSnackbarOpen(true);
      // Retry any failed messages
      retryFailedMessages();
    };
    
    const handleOffline = () => {
      setIsOnline(false);
      setSnackbarMessage('You are offline. Messages will be sent when you reconnect.');
      setSnackbarOpen(true);
    };
    
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);
  
  // Generate a session ID when the component mounts
  useEffect(() => {
    const newSessionId = uuidv4();
    setSessionId(newSessionId);
    
    // Load chat history for this session
    loadChatHistory(newSessionId);
    
    // Focus on input field
    setTimeout(() => {
      inputRef.current?.focus();
    }, 500);
  }, []);
  
  // Scroll to bottom when messages change
  useEffect(() => {
    if (messages.length > 0) {
      scrollToBottom();
    }
  }, [messages]);
  
  const scrollToBottom = () => {
    // Use requestAnimationFrame for smoother scrolling
    requestAnimationFrame(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    });
  };
  
  const loadChatHistory = async (sid: string) => {
    setIsInitialLoad(true);
    try {
      const response = await axios.get(`/api/chat/history?session_id=${sid}`);
      if (response.data.messages && response.data.messages.length > 0) {
        setMessages(response.data.messages);
        setRecommendationCount(response.data.recommendation_count || 0);
      } else {
        // Add welcome message if no history
        setMessages([
          {
            id: uuidv4(),
            text: "Welcome to the Betting Chatbot! How can I help you with your sports betting today?",
            sender: 'bot',
            timestamp: new Date(),
            status: 'sent'
          },
        ]);
      }
    } catch (error) {
      console.error('Error loading chat history:', error);
      setSnackbarMessage('Failed to load chat history. Please refresh the page.');
      setSnackbarOpen(true);
    } finally {
      setIsInitialLoad(false);
    }
  };
  
  const retryFailedMessages = () => {
    const failedMessages = messages.filter(msg => msg.status === 'error' && msg.sender === 'user');
    
    failedMessages.forEach(msg => {
      if ((msg.retryCount || 0) < MAX_RETRY_ATTEMPTS) {
        sendMessage(msg.text, msg.id);
      }
    });
  };
  
  const sendMessage = async (text: string, existingId?: string) => {
    const messageId = existingId || uuidv4();
    const retryCount = existingId 
      ? (messages.find(m => m.id === existingId)?.retryCount || 0) + 1 
      : 0;
    
    // Update the message status to sending
    setMessages(prevMessages => 
      prevMessages.map(m => 
        m.id === messageId 
          ? { ...m, status: 'sending', retryCount } 
          : m
      )
    );
    
    try {
      const response = await axios.post('/api/chat/send', {
        message: text,
        session_id: sessionId,
      });
      
      // Update the user message status to sent
      setMessages(prevMessages => 
        prevMessages.map(m => 
          m.id === messageId 
            ? { ...m, status: 'sent' } 
            : m
        )
      );
      
      // Add the bot response
      const botMessage: Message = {
        id: uuidv4(),
        text: response.data.response,
        sender: 'bot',
        timestamp: new Date(),
        status: 'sent'
      };
      
      setMessages(prevMessages => [...prevMessages, botMessage]);
      setRecommendationCount(response.data.recommendation_count);
      
      // Check for violations or timeouts
      if (response.data.is_violation) {
        setError('Your message violated our chat rules. Please avoid asking directly for top bets.');
        setTimeout(() => setError(''), 5000); // Clear error after 5 seconds
      }
      
      if (response.data.is_timed_out) {
        setError('Your account is temporarily timed out due to multiple violations. Please try again later.');
      }
      
    } catch (err: any) {
      console.error('Error sending message:', err);
      
      // Update the message status to error
      setMessages(prevMessages => 
        prevMessages.map(m => 
          m.id === messageId 
            ? { ...m, status: 'error', retryCount } 
            : m
        )
      );
      
      const errorMessage = err.response?.data?.error || 'Failed to send message. Please try again.';
      setError(errorMessage);
      
      // If we haven't exceeded retry attempts and we're online, retry after delay
      if (retryCount < MAX_RETRY_ATTEMPTS && isOnline) {
        setTimeout(() => {
          sendMessage(text, messageId);
        }, RETRY_DELAY);
      }
    }
  };
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!message.trim()) return;
    
    // Check if we're online
    if (!isOnline) {
      setSnackbarMessage('You are offline. Your message will be sent when you reconnect.');
      setSnackbarOpen(true);
    }
    
    const userMessage: Message = {
      id: uuidv4(),
      text: message,
      sender: 'user',
      timestamp: new Date(),
      status: isOnline ? 'sending' : 'error',
      retryCount: 0
    };
    
    setMessages(prevMessages => [...prevMessages, userMessage]);
    const currentMessage = message;
    setMessage('');
    setIsLoading(true);
    
    // Clear any previous errors
    setError('');
    
    if (isOnline) {
      try {
        await sendMessage(currentMessage, userMessage.id);
      } finally {
        setIsLoading(false);
      }
    } else {
      setIsLoading(false);
    }
  };
  
  const handleRetry = (messageId: string) => {
    const messageToRetry = messages.find(m => m.id === messageId);
    if (messageToRetry) {
      sendMessage(messageToRetry.text, messageId);
    }
  };
  
  const formatTime = (date: Date) => {
    return new Date(date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };
  
  const handleCloseSnackbar = () => {
    setSnackbarOpen(false);
  };
  
  const getMessageStatusIcon = (status?: string) => {
    switch (status) {
      case 'sending':
        return <CircularProgress size={12} sx={{ ml: 1 }} />;
      case 'error':
        return <ErrorIcon color="error" fontSize="small" sx={{ ml: 1 }} />;
      default:
        return null;
    }
  };
  
  return (
    <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
      <Paper elevation={3} sx={{ borderRadius: 2, overflow: 'hidden' }}>
        <Box sx={{ p: 2, bgcolor: 'primary.main', color: 'white', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6">Betting Chatbot</Typography>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            {!isOnline && (
              <Tooltip title="You are offline">
                <WifiOffIcon sx={{ mr: 1, color: 'error.light' }} />
              </Tooltip>
            )}
            {user?.plan === 'free' && (
              <Box sx={{ display: 'flex', alignItems: 'center', ml: 1 }}>
                <InfoIcon fontSize="small" sx={{ mr: 1 }} />
                <Typography variant="body2">
                  {recommendationCount}/3 daily recommendations
                </Typography>
              </Box>
            )}
          </Box>
        </Box>
        
        <Divider />
        
        {error && (
          <Alert severity="error" sx={{ m: 2 }} onClose={() => setError('')}>
            {error}
          </Alert>
        )}
        
        <Box
          ref={chatContainerRef}
          sx={{
            height: '60vh',
            overflowY: 'auto',
            p: 2,
            bgcolor: 'background.default',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          {isInitialLoad ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
              <CircularProgress />
            </Box>
          ) : (
            <List sx={{ width: '100%' }}>
              {messages.map((msg) => (
                <ListItem
                  key={msg.id}
                  sx={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: msg.sender === 'user' ? 'flex-end' : 'flex-start',
                    mb: 2,
                    padding: 0,
                  }}
                  className="chat-message"
                >
                  <Box
                    sx={{
                      maxWidth: '80%',
                      bgcolor: msg.sender === 'user' ? 'primary.main' : 'background.paper',
                      color: msg.sender === 'user' ? 'white' : 'text.primary',
                      borderRadius: 2,
                      p: 2,
                      boxShadow: 1,
                      position: 'relative',
                    }}
                  >
                    <ListItemText
                      primary={msg.text}
                      primaryTypographyProps={{
                        component: 'div',
                        style: { whiteSpace: 'pre-wrap', wordBreak: 'break-word' },
                      }}
                    />
                    {msg.sender === 'user' && msg.status === 'error' && (
                      <Tooltip title="Retry sending this message">
                        <IconButton
                          size="small"
                          color="inherit"
                          onClick={() => handleRetry(msg.id)}
                          sx={{ position: 'absolute', right: -8, bottom: -8, bgcolor: 'background.paper', '&:hover': { bgcolor: 'background.default' } }}
                        >
                          <RefreshIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    )}
                  </Box>
                  <Box sx={{ display: 'flex', alignItems: 'center', mt: 0.5 }}>
                    <Typography variant="caption" color="text.secondary">
                      {msg.sender === 'user' ? 'You' : 'Betting Chatbot'} • {formatTime(msg.timestamp)}
                    </Typography>
                    {getMessageStatusIcon(msg.status)}
                  </Box>
                </ListItem>
              ))}
              <div ref={messagesEndRef} />
            </List>
          )}
        </Box>
        
        <Divider />
        
        <Box
          component="form"
          onSubmit={handleSubmit}
          sx={{
            p: 2,
            display: 'flex',
            alignItems: 'center',
            bgcolor: 'background.paper',
          }}
        >
          <TextField
            fullWidth
            placeholder="Type your message..."
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            disabled={isLoading}
            variant="outlined"
            size="small"
            sx={{ mr: 1 }}
            inputRef={inputRef}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (message.trim()) {
                  handleSubmit(e);
                }
              }
            }}
          />
          <IconButton
            color="primary"
            type="submit"
            disabled={isLoading || !message.trim()}
            sx={{ p: 1 }}
          >
            {isLoading ? <CircularProgress size={24} /> : <SendIcon />}
          </IconButton>
        </Box>
        
        {user?.plan === 'free' && recommendationCount >= 3 && (
          <Box sx={{ p: 2, bgcolor: 'warning.light', color: 'warning.contrastText' }}>
            <Typography variant="body2" sx={{ display: 'flex', alignItems: 'center' }}>
              <InfoIcon fontSize="small" sx={{ mr: 1 }} />
              You've reached your daily limit of 3 recommendations.
              <Button
                variant="outlined"
                size="small"
                color="inherit"
                sx={{ ml: 2 }}
                component="a"
                href="/profile"
              >
                Upgrade to Premium
              </Button>
            </Typography>
          </Box>
        )}
      </Paper>
      
      <Snackbar
        open={snackbarOpen}
        autoHideDuration={6000}
        onClose={handleCloseSnackbar}
        message={snackbarMessage}
      />
    </Container>
  );
};

export default Chat; 
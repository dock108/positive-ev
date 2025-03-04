import React, { useState } from 'react';
import {
  Container,
  Box,
  Typography,
  TextField,
  Button,
  Paper,
  Grid,
  IconButton,
  Divider,
  Alert,
  CircularProgress,
  Tooltip,
  Card,
  CardContent,
  Chip,
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Info as InfoIcon,
  Calculate as CalculateIcon,
} from '@mui/icons-material';
import axios from 'axios';

interface BetInput {
  id: number;
  description: string;
  odds: string;
  probability: string;
}

interface ParlayResult {
  decimal_odds: number;
  american_odds: number;
  implied_probability: number;
  true_probability: number;
  ev_percent: number;
  kelly_fraction: number;
  edge: number;
  correlated_warning: boolean;
}

interface ParsedBet {
  description: string;
  odds: number;
  win_probability: number;
  ev_percent: number;
}

const ParlayCalculator: React.FC = () => {
  const [bets, setBets] = useState<BetInput[]>([
    { id: 1, description: '', odds: '', probability: '' },
    { id: 2, description: '', odds: '', probability: '' },
  ]);
  
  const [result, setResult] = useState<ParlayResult | null>(null);
  const [parsedBets, setParsedBets] = useState<ParsedBet[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  
  const handleAddBet = () => {
    const newBet: BetInput = {
      id: Date.now(),
      description: '',
      odds: '',
      probability: '',
    };
    setBets([...bets, newBet]);
  };
  
  const handleRemoveBet = (id: number) => {
    if (bets.length <= 2) {
      setError('A parlay requires at least two bets');
      return;
    }
    setBets(bets.filter((bet) => bet.id !== id));
  };
  
  const handleBetChange = (id: number, field: keyof BetInput, value: string) => {
    setBets(
      bets.map((bet) => (bet.id === id ? { ...bet, [field]: value } : bet))
    );
  };
  
  const validateInputs = (): boolean => {
    // Check if at least two bets are provided
    if (bets.length < 2) {
      setError('A parlay requires at least two bets');
      return false;
    }
    
    // Check if all required fields are filled
    for (const bet of bets) {
      if (!bet.description.trim()) {
        setError('Please provide a description for all bets');
        return false;
      }
      
      if (!bet.odds.trim()) {
        setError('Please provide odds for all bets');
        return false;
      }
      
      // Validate odds format
      const oddsValue = parseInt(bet.odds);
      if (isNaN(oddsValue)) {
        setError('Odds must be a valid number (e.g., -110, +150)');
        return false;
      }
      
      // Validate probability if provided
      if (bet.probability.trim()) {
        const probValue = parseFloat(bet.probability);
        if (isNaN(probValue) || probValue <= 0 || probValue >= 100) {
          setError('Win probability must be between 0 and 100');
          return false;
        }
      }
    }
    
    return true;
  };
  
  const handleCalculate = async () => {
    if (!validateInputs()) {
      return;
    }
    
    setError('');
    setIsLoading(true);
    
    try {
      // Format bets for API
      const betStrings = bets.map((bet) => {
        const description = bet.description.trim();
        const odds = bet.odds.trim();
        const probability = bet.probability.trim() ? `${bet.probability.trim()}%` : '';
        
        return `${description} (${odds}) ${probability}`;
      });
      
      const response = await axios.post('/api/parlay/calculate', {
        bets: betStrings,
      });
      
      setResult(response.data.result);
      setParsedBets(response.data.parsed_bets);
      
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to calculate parlay. Please check your inputs.');
      console.error('Error calculating parlay:', err);
    } finally {
      setIsLoading(false);
    }
  };
  
  const formatOdds = (odds: number): string => {
    return odds >= 0 ? `+${odds}` : `${odds}`;
  };
  
  const formatPercentage = (value: number): string => {
    return `${value.toFixed(2)}%`;
  };
  
  return (
    <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
      <Paper elevation={3} sx={{ p: 3, borderRadius: 2 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Parlay Calculator
        </Typography>
        
        <Typography variant="body1" color="text.secondary" paragraph>
          Calculate true odds, probabilities, and expected value for your parlay bets.
        </Typography>
        
        {error && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}
        
        <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Enter Your Bets
          </Typography>
          
          {bets.map((bet, index) => (
            <Box key={bet.id} sx={{ mb: 2 }}>
              <Grid container spacing={2} alignItems="center">
                <Grid item xs={12} sm={5}>
                  <TextField
                    fullWidth
                    label="Bet Description"
                    placeholder="e.g., Lakers -5.5"
                    value={bet.description}
                    onChange={(e) => handleBetChange(bet.id, 'description', e.target.value)}
                    variant="outlined"
                    size="small"
                  />
                </Grid>
                <Grid item xs={6} sm={3}>
                  <TextField
                    fullWidth
                    label="American Odds"
                    placeholder="e.g., -110, +150"
                    value={bet.odds}
                    onChange={(e) => handleBetChange(bet.id, 'odds', e.target.value)}
                    variant="outlined"
                    size="small"
                  />
                </Grid>
                <Grid item xs={6} sm={3}>
                  <TextField
                    fullWidth
                    label="Win Probability (%)"
                    placeholder="e.g., 60"
                    value={bet.probability}
                    onChange={(e) => handleBetChange(bet.id, 'probability', e.target.value)}
                    variant="outlined"
                    size="small"
                  />
                </Grid>
                <Grid item xs={12} sm={1}>
                  <IconButton
                    color="error"
                    onClick={() => handleRemoveBet(bet.id)}
                    disabled={bets.length <= 2}
                  >
                    <DeleteIcon />
                  </IconButton>
                </Grid>
              </Grid>
              
              {index < bets.length - 1 && (
                <Divider sx={{ my: 2 }} />
              )}
            </Box>
          ))}
          
          <Box sx={{ mt: 2, display: 'flex', justifyContent: 'space-between' }}>
            <Button
              startIcon={<AddIcon />}
              onClick={handleAddBet}
              variant="outlined"
            >
              Add Bet
            </Button>
            
            <Button
              startIcon={isLoading ? <CircularProgress size={20} /> : <CalculateIcon />}
              onClick={handleCalculate}
              variant="contained"
              disabled={isLoading}
            >
              Calculate Parlay
            </Button>
          </Box>
        </Paper>
        
        {result && (
          <Card variant="outlined" sx={{ mb: 3 }}>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">Parlay Results</Typography>
                
                {result.correlated_warning && (
                  <Tooltip title="These bets may be correlated, which could affect the accuracy of the calculations.">
                    <Chip
                      icon={<InfoIcon />}
                      label="Possible Correlation"
                      color="warning"
                      size="small"
                    />
                  </Tooltip>
                )}
              </Box>
              
              <Grid container spacing={2}>
                <Grid item xs={6} sm={3}>
                  <Typography variant="body2" color="text.secondary">
                    American Odds
                  </Typography>
                  <Typography variant="h6" color={result.american_odds > 0 ? 'success.main' : 'error.main'}>
                    {formatOdds(result.american_odds)}
                  </Typography>
                </Grid>
                
                <Grid item xs={6} sm={3}>
                  <Typography variant="body2" color="text.secondary">
                    Decimal Odds
                  </Typography>
                  <Typography variant="h6">
                    {result.decimal_odds.toFixed(2)}
                  </Typography>
                </Grid>
                
                <Grid item xs={6} sm={3}>
                  <Typography variant="body2" color="text.secondary">
                    True Probability
                  </Typography>
                  <Typography variant="h6">
                    {formatPercentage(result.true_probability * 100)}
                  </Typography>
                </Grid>
                
                <Grid item xs={6} sm={3}>
                  <Typography variant="body2" color="text.secondary">
                    Implied Probability
                  </Typography>
                  <Typography variant="h6">
                    {formatPercentage(result.implied_probability * 100)}
                  </Typography>
                </Grid>
                
                <Grid item xs={6} sm={4}>
                  <Typography variant="body2" color="text.secondary">
                    Expected Value (EV)
                  </Typography>
                  <Typography variant="h6" color={result.ev_percent > 0 ? 'success.main' : 'error.main'}>
                    {formatPercentage(result.ev_percent)}
                  </Typography>
                </Grid>
                
                <Grid item xs={6} sm={4}>
                  <Typography variant="body2" color="text.secondary">
                    Kelly Fraction
                  </Typography>
                  <Typography variant="h6">
                    {formatPercentage(result.kelly_fraction * 100)}
                  </Typography>
                </Grid>
                
                <Grid item xs={6} sm={4}>
                  <Typography variant="body2" color="text.secondary">
                    Edge
                  </Typography>
                  <Typography variant="h6" color={result.edge > 0 ? 'success.main' : 'error.main'}>
                    {formatPercentage(result.edge)}
                  </Typography>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        )}
        
        {parsedBets.length > 0 && (
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Parsed Bets
            </Typography>
            
            <Grid container spacing={2}>
              {parsedBets.map((bet, index) => (
                <Grid item xs={12} key={index}>
                  <Paper variant="outlined" sx={{ p: 2 }}>
                    <Grid container spacing={2}>
                      <Grid item xs={12} sm={6}>
                        <Typography variant="body2" color="text.secondary">
                          Description
                        </Typography>
                        <Typography variant="body1">
                          {bet.description}
                        </Typography>
                      </Grid>
                      
                      <Grid item xs={4} sm={2}>
                        <Typography variant="body2" color="text.secondary">
                          Odds
                        </Typography>
                        <Typography variant="body1" color={bet.odds > 0 ? 'success.main' : 'error.main'}>
                          {formatOdds(bet.odds)}
                        </Typography>
                      </Grid>
                      
                      <Grid item xs={4} sm={2}>
                        <Typography variant="body2" color="text.secondary">
                          Win Probability
                        </Typography>
                        <Typography variant="body1">
                          {formatPercentage(bet.win_probability)}
                        </Typography>
                      </Grid>
                      
                      <Grid item xs={4} sm={2}>
                        <Typography variant="body2" color="text.secondary">
                          EV
                        </Typography>
                        <Typography variant="body1" color={bet.ev_percent > 0 ? 'success.main' : 'error.main'}>
                          {formatPercentage(bet.ev_percent)}
                        </Typography>
                      </Grid>
                    </Grid>
                  </Paper>
                </Grid>
              ))}
            </Grid>
          </Paper>
        )}
      </Paper>
    </Container>
  );
};

export default ParlayCalculator; 
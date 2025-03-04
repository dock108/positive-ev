import React, { useState } from 'react';
import {
  Container,
  Paper,
  Typography,
  Box,
  Grid,
  Button,
  Card,
  CardContent,
  Divider,
  TextField,
  Alert,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Chip,
} from '@mui/material';
import {
  Person as PersonIcon,
  Email as EmailIcon,
  VpnKey as VpnKeyIcon,
  CreditCard as CreditCardIcon,
  History as HistoryIcon,
} from '@mui/icons-material';
import { useAuth } from '../context/AuthContext';

const Profile: React.FC = () => {
  const { user, upgradeAccount, logout } = useAuth();
  
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [passwordSuccess, setPasswordSuccess] = useState('');
  const [isPasswordLoading, setIsPasswordLoading] = useState(false);
  
  const [openUpgradeDialog, setOpenUpgradeDialog] = useState(false);
  const [isUpgrading, setIsUpgrading] = useState(false);
  const [upgradeError, setUpgradeError] = useState('');
  
  const [openDeleteDialog, setOpenDeleteDialog] = useState(false);
  const [deleteConfirmation, setDeleteConfirmation] = useState('');
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState('');
  
  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Reset states
    setPasswordError('');
    setPasswordSuccess('');
    
    // Validate passwords
    if (!currentPassword) {
      setPasswordError('Current password is required');
      return;
    }
    
    if (!newPassword) {
      setPasswordError('New password is required');
      return;
    }
    
    if (newPassword !== confirmPassword) {
      setPasswordError('New passwords do not match');
      return;
    }
    
    if (newPassword.length < 8) {
      setPasswordError('Password must be at least 8 characters long');
      return;
    }
    
    setIsPasswordLoading(true);
    
    try {
      // Call API to change password
      const response = await fetch('/api/user/change-password', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          currentPassword,
          newPassword,
        }),
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.error || 'Failed to change password');
      }
      
      // Clear form and show success message
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setPasswordSuccess('Password changed successfully');
      
    } catch (error: any) {
      setPasswordError(error.message || 'Failed to change password');
    } finally {
      setIsPasswordLoading(false);
    }
  };
  
  const handleUpgradeAccount = async () => {
    setIsUpgrading(true);
    setUpgradeError('');
    
    try {
      await upgradeAccount();
      setOpenUpgradeDialog(false);
    } catch (error: any) {
      setUpgradeError(error.message || 'Failed to upgrade account');
    } finally {
      setIsUpgrading(false);
    }
  };
  
  const handleDeleteAccount = async () => {
    if (deleteConfirmation !== user?.email) {
      setDeleteError('Please enter your email correctly to confirm deletion');
      return;
    }
    
    setIsDeleting(true);
    setDeleteError('');
    
    try {
      const response = await fetch('/api/user/delete-account', {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.error || 'Failed to delete account');
      }
      
      // Log out the user after successful deletion
      logout();
      
    } catch (error: any) {
      setDeleteError(error.message || 'Failed to delete account');
      setIsDeleting(false);
    }
  };
  
  const getPlanLabel = (plan: string) => {
    switch (plan) {
      case 'free':
        return 'Free Plan';
      case 'premium':
        return 'Premium Plan';
      case 'pro':
        return 'Pro Plan';
      default:
        return 'Unknown Plan';
    }
  };
  
  const getPlanColor = (plan: string) => {
    switch (plan) {
      case 'free':
        return 'default';
      case 'premium':
        return 'primary';
      case 'pro':
        return 'secondary';
      default:
        return 'default';
    }
  };
  
  return (
    <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
      <Paper elevation={3} sx={{ p: 3, borderRadius: 2 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Your Profile
        </Typography>
        
        <Grid container spacing={4}>
          {/* User Info Section */}
          <Grid item xs={12} md={6}>
            <Card variant="outlined" sx={{ height: '100%' }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <PersonIcon sx={{ mr: 1 }} />
                  <Typography variant="h6">Account Information</Typography>
                </Box>
                
                <Divider sx={{ mb: 2 }} />
                
                <Box sx={{ mb: 2 }}>
                  <Typography variant="body2" color="text.secondary">
                    Email
                  </Typography>
                  <Typography variant="body1" sx={{ display: 'flex', alignItems: 'center' }}>
                    <EmailIcon fontSize="small" sx={{ mr: 1, opacity: 0.7 }} />
                    {user?.email || 'Not available'}
                  </Typography>
                </Box>
                
                <Box sx={{ mb: 2 }}>
                  <Typography variant="body2" color="text.secondary">
                    Account Type
                  </Typography>
                  <Box sx={{ mt: 0.5 }}>
                    <Chip
                      label={getPlanLabel(user?.plan || 'free')}
                      color={getPlanColor(user?.plan || 'free') as any}
                      size="small"
                    />
                  </Box>
                </Box>
                
                <Box sx={{ mb: 2 }}>
                  <Typography variant="body2" color="text.secondary">
                    Member Since
                  </Typography>
                  <Typography variant="body1">
                    {user?.createdAt
                      ? new Date(user.createdAt).toLocaleDateString()
                      : 'Not available'}
                  </Typography>
                </Box>
                
                {user?.plan === 'free' && (
                  <Button
                    variant="contained"
                    color="primary"
                    startIcon={<CreditCardIcon />}
                    fullWidth
                    onClick={() => setOpenUpgradeDialog(true)}
                    sx={{ mt: 2 }}
                  >
                    Upgrade Account
                  </Button>
                )}
              </CardContent>
            </Card>
          </Grid>
          
          {/* Password Change Section */}
          <Grid item xs={12} md={6}>
            <Card variant="outlined" sx={{ height: '100%' }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <VpnKeyIcon sx={{ mr: 1 }} />
                  <Typography variant="h6">Change Password</Typography>
                </Box>
                
                <Divider sx={{ mb: 2 }} />
                
                {passwordError && (
                  <Alert severity="error" sx={{ mb: 2 }}>
                    {passwordError}
                  </Alert>
                )}
                
                {passwordSuccess && (
                  <Alert severity="success" sx={{ mb: 2 }}>
                    {passwordSuccess}
                  </Alert>
                )}
                
                <form onSubmit={handlePasswordChange}>
                  <TextField
                    label="Current Password"
                    type="password"
                    fullWidth
                    margin="normal"
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                  />
                  
                  <TextField
                    label="New Password"
                    type="password"
                    fullWidth
                    margin="normal"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                  />
                  
                  <TextField
                    label="Confirm New Password"
                    type="password"
                    fullWidth
                    margin="normal"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                  />
                  
                  <Button
                    type="submit"
                    variant="contained"
                    color="primary"
                    fullWidth
                    disabled={isPasswordLoading}
                    sx={{ mt: 2 }}
                  >
                    {isPasswordLoading ? (
                      <CircularProgress size={24} />
                    ) : (
                      'Update Password'
                    )}
                  </Button>
                </form>
              </CardContent>
            </Card>
          </Grid>
          
          {/* Usage Stats Section */}
          <Grid item xs={12}>
            <Card variant="outlined">
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <HistoryIcon sx={{ mr: 1 }} />
                  <Typography variant="h6">Usage Statistics</Typography>
                </Box>
                
                <Divider sx={{ mb: 2 }} />
                
                <Grid container spacing={3}>
                  <Grid item xs={12} sm={4}>
                    <Box sx={{ textAlign: 'center', p: 2 }}>
                      <Typography variant="h4" color="primary">
                        {user?.stats?.totalChats || 0}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Total Chats
                      </Typography>
                    </Box>
                  </Grid>
                  
                  <Grid item xs={12} sm={4}>
                    <Box sx={{ textAlign: 'center', p: 2 }}>
                      <Typography variant="h4" color="primary">
                        {user?.stats?.totalMessages || 0}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Total Messages
                      </Typography>
                    </Box>
                  </Grid>
                  
                  <Grid item xs={12} sm={4}>
                    <Box sx={{ textAlign: 'center', p: 2 }}>
                      <Typography variant="h4" color="primary">
                        {user?.stats?.parlayCalculations || 0}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Parlay Calculations
                      </Typography>
                    </Box>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Grid>
          
          {/* Danger Zone */}
          <Grid item xs={12}>
            <Card variant="outlined" sx={{ borderColor: 'error.main' }}>
              <CardContent>
                <Typography variant="h6" color="error">
                  Danger Zone
                </Typography>
                
                <Divider sx={{ my: 2 }} />
                
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Box>
                    <Typography variant="body1" fontWeight="bold">
                      Delete Account
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      This action cannot be undone. All your data will be permanently deleted.
                    </Typography>
                  </Box>
                  
                  <Button
                    variant="outlined"
                    color="error"
                    onClick={() => setOpenDeleteDialog(true)}
                  >
                    Delete Account
                  </Button>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Paper>
      
      {/* Upgrade Account Dialog */}
      <Dialog open={openUpgradeDialog} onClose={() => setOpenUpgradeDialog(false)}>
        <DialogTitle>Upgrade Your Account</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Upgrade to our Premium plan to get unlimited access to all features, including:
          </DialogContentText>
          
          <Box sx={{ mt: 2 }}>
            <Typography variant="body1" sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
              • Unlimited chat messages
            </Typography>
            <Typography variant="body1" sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
              • Advanced betting recommendations
            </Typography>
            <Typography variant="body1" sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
              • Detailed analytics and insights
            </Typography>
            <Typography variant="body1" sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
              • Priority support
            </Typography>
          </Box>
          
          {upgradeError && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {upgradeError}
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenUpgradeDialog(false)}>Cancel</Button>
          <Button
            onClick={handleUpgradeAccount}
            variant="contained"
            color="primary"
            disabled={isUpgrading}
          >
            {isUpgrading ? <CircularProgress size={24} /> : 'Upgrade Now - $9.99/month'}
          </Button>
        </DialogActions>
      </Dialog>
      
      {/* Delete Account Dialog */}
      <Dialog open={openDeleteDialog} onClose={() => setOpenDeleteDialog(false)}>
        <DialogTitle>Delete Your Account</DialogTitle>
        <DialogContent>
          <DialogContentText>
            This action cannot be undone. All your data, including chat history and saved bets, will be permanently deleted.
          </DialogContentText>
          
          <DialogContentText sx={{ mt: 2 }}>
            To confirm, please enter your email address: <strong>{user?.email}</strong>
          </DialogContentText>
          
          <TextField
            autoFocus
            margin="dense"
            label="Confirm Email"
            type="email"
            fullWidth
            value={deleteConfirmation}
            onChange={(e) => setDeleteConfirmation(e.target.value)}
            error={!!deleteError}
          />
          
          {deleteError && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {deleteError}
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDeleteDialog(false)}>Cancel</Button>
          <Button
            onClick={handleDeleteAccount}
            variant="contained"
            color="error"
            disabled={isDeleting || deleteConfirmation !== user?.email}
          >
            {isDeleting ? <CircularProgress size={24} /> : 'Delete Account'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default Profile; 
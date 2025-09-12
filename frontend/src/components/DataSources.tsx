import React, { useState, useEffect } from 'react';
import {
  Container,
  Typography,
  Card,
  CardContent,
  CardActions,
  Button,
  Grid,
  Box,
  Switch,
  FormControlLabel,
  Alert,
  LinearProgress,
  Chip,
} from '@mui/material';
import {
  Email as EmailIcon,
  WhatsApp as WhatsAppIcon,
  AccountBalance as BankIcon,
  Cloud as DriveIcon,
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
} from '@mui/icons-material';
import api from '../services/api';
import { DataSource } from '../types';

const DataSources: React.FC = () => {
  const [dataSources, setDataSources] = useState<DataSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncStatus, setSyncStatus] = useState<Record<string, any>>({});

  const sourceTypes = [
    {
      type: 'gmail',
      name: 'Gmail',
      description: 'Connect your Gmail to analyze emails and attachments',
      icon: <EmailIcon />,
      color: 'error' as const,
    },
    {
      type: 'whatsapp',
      name: 'WhatsApp',
      description: 'Connect WhatsApp to analyze messages and contacts',
      icon: <WhatsAppIcon />,
      color: 'success' as const,
    },
    {
      type: 'bank',
      name: 'Bank Account',
      description: 'Connect your bank account via Plaid for transaction data',
      icon: <BankIcon />,
      color: 'primary' as const,
    },
    {
      type: 'drive',
      name: 'Google Drive',
      description: 'Connect Google Drive to analyze documents and files',
      icon: <DriveIcon />,
      color: 'warning' as const,
    },
  ];

  useEffect(() => {
    fetchDataSources();
    fetchSyncStatus();
    
    // Poll for sync status updates every 2 seconds
    const interval = setInterval(fetchSyncStatus, 2000);
    
    return () => clearInterval(interval);
  }, []);

  const fetchDataSources = async () => {
    try {
      const response = await api.get('/api/data-sources/');
      setDataSources(response.data);
    } catch (error) {
      console.error('Error fetching data sources:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchSyncStatus = async () => {
    try {
      const response = await api.get('/api/data-sources/sync/status');
      setSyncStatus(response.data);
    } catch (error) {
      console.error('Error fetching sync status:', error);
    }
  };

  const handleToggle = async (dataSourceId: number) => {
    try {
      await api.put(`/api/data-sources/${dataSourceId}/toggle`);
      fetchDataSources();
    } catch (error) {
      console.error('Error toggling data source:', error);
    }
  };

  const handleSync = async (sourceType: string) => {
    try {
      let response;
      
      switch (sourceType) {
        case 'gmail':
          response = await api.post('/api/data-sources/sync/gmail');
          break;
        case 'drive':
          response = await api.post('/api/data-sources/sync/drive');
          break;
        case 'whatsapp':
          response = await api.post('/api/whatsapp/sync');
          break;
        case 'bank':
          response = await api.post('/api/plaid/sync');
          break;
        default:
          alert(`Sync for ${sourceType} not implemented yet`);
          return;
      }
      
      alert(`Successfully synced ${sourceType}: ${response.data.message}`);
      fetchDataSources();
      fetchSyncStatus();
    } catch (error) {
      console.error('Error syncing data source:', error);
      alert('Failed to sync data. Please try again.');
    }
  };

  const handleSyncAll = async () => {
    try {
      setLoading(true);
      const response = await api.post('/api/data-sources/sync/all');
      alert(response.data.message);
      await fetchDataSources();
      fetchSyncStatus();
    } catch (error: any) {
      console.error('Error syncing all data sources:', error);
      alert(error.response?.data?.detail || 'Failed to sync all data sources. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleConnect = async (sourceType: string) => {
    try {
      // Check if this is a Google service that's already connected via OAuth
      const isGoogleService = ['gmail', 'drive'].includes(sourceType);
      const connectionStatus = getConnectionStatus(sourceType);
      
      if (isGoogleService && connectionStatus.isConnected) {
        alert(`${sourceType.charAt(0).toUpperCase() + sourceType.slice(1)} is already connected via Google OAuth. You can sync your data using the Sync button.`);
        return;
      }
      
      let response;
      
      switch (sourceType) {
        case 'gmail':
          if (!connectionStatus.isConnected) {
            response = await api.get('/api/gmail/auth-url');
            window.open(response.data.auth_url, '_blank');
          }
          break;
        case 'whatsapp':
          response = await api.get('/api/whatsapp/auth-url');
          window.open(response.data.auth_url, '_blank');
          break;
        case 'bank':
          response = await api.get('/api/plaid/link-token');
          // In a real implementation, you'd use Plaid Link here
          alert('Plaid Link integration will be implemented with the Plaid Link component');
          break;
        case 'drive':
          if (!connectionStatus.isConnected) {
            response = await api.get('/api/drive/auth-url');
            window.open(response.data.auth_url, '_blank');
          }
          break;
        default:
          alert(`Connect ${sourceType} - OAuth flow not implemented yet`);
      }
    } catch (error) {
      console.error('Error connecting data source:', error);
      alert('Failed to initiate connection. Please try again.');
    }
  };

  const getDataSourceStatus = (sourceType: string) => {
    return dataSources.find(ds => ds.source_type === sourceType);
  };

  const getConnectionStatus = (sourceType: string) => {
    const dataSource = getDataSourceStatus(sourceType);
    const isConnected = !!dataSource;
    const isActive = dataSource?.is_active;
    
    // Check if this is a Google service that might be auto-connected
    const isGoogleService = ['gmail', 'drive'].includes(sourceType);
    
    return {
      isConnected,
      isActive,
      isGoogleService,
      status: isConnected && isActive ? 'connected' : isConnected ? 'inactive' : 'disconnected'
    };
  };

  return (
    <Container maxWidth="lg">
      <Typography variant="h4" component="h1" gutterBottom>
        Data Sources
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Connect your accounts to give Aura access to your data
      </Typography>

      <Alert severity="success" sx={{ mb: 4 }}>
        Google OAuth integration is now available! Gmail and Google Drive are automatically connected when you sign in with Google.
      </Alert>

      <Box sx={{ mb: 3, display: 'flex', gap: 2, alignItems: 'center' }}>
        <Button
          variant="contained"
          onClick={handleSyncAll}
          disabled={loading}
          sx={{ minWidth: 120 }}
        >
          {loading ? 'Syncing...' : 'Sync All'}
        </Button>
        <Typography variant="body2" color="text.secondary">
          Sync all connected data sources
        </Typography>
      </Box>

      <Grid container spacing={3}>
        {sourceTypes.map((source) => {
          const connectionStatus = getConnectionStatus(source.type);
          const { isConnected, isActive, isGoogleService, status } = connectionStatus;
          const dataSource = getDataSourceStatus(source.type);

          return (
            <Grid size={{ xs: 12, sm: 6, md: 4 }} key={source.type}>
              <Card>
                <CardContent>
                  <Box display="flex" alignItems="center" mb={2}>
                    <Box
                      sx={{
                        p: 1,
                        borderRadius: 1,
                        backgroundColor: `${source.color}.main`,
                        color: 'white',
                        mr: 2,
                      }}
                    >
                      {source.icon}
                    </Box>
                    <Typography variant="h6">{source.name}</Typography>
                  </Box>
                  
                  <Typography variant="body2" color="text.secondary" paragraph>
                    {source.description}
                  </Typography>

                  <Box display="flex" alignItems="center" mb={2}>
                    {status === 'connected' ? (
                      <>
                        <CheckIcon color="success" sx={{ mr: 1 }} />
                        <Typography variant="body2" color="success.main">
                          {isGoogleService ? 'Auto-Connected via Google' : 'Connected'}
                        </Typography>
                      </>
                    ) : status === 'inactive' ? (
                      <>
                        <ErrorIcon color="warning" sx={{ mr: 1 }} />
                        <Typography variant="body2" color="warning.main">
                          Connected but Inactive
                        </Typography>
                      </>
                    ) : (
                      <>
                        <ErrorIcon color="error" sx={{ mr: 1 }} />
                        <Typography variant="body2" color="error.main">
                          Not Connected
                        </Typography>
                      </>
                    )}
                  </Box>

                  {isConnected && (
                    <Box display="flex" alignItems="center" mb={2}>
                      <FormControlLabel
                        control={
                          <Switch
                            checked={isActive}
                            onChange={() => handleToggle(dataSource?.id || 0)}
                            color="primary"
                          />
                        }
                        label={isActive ? 'Active' : 'Inactive'}
                      />
                    </Box>
                  )}

                  {/* Sync Status Display */}
                  {syncStatus[source.type] && (
                    <Box sx={{ mb: 2 }}>
                      <Box display="flex" alignItems="center" justifyContent="space-between" mb={1}>
                        <Typography variant="caption" color="text.secondary">
                          Sync Status:
                        </Typography>
                        <Chip
                          label={syncStatus[source.type].status}
                          size="small"
                          color={
                            syncStatus[source.type].status === 'syncing' ? 'primary' :
                            syncStatus[source.type].status === 'completed' ? 'success' :
                            syncStatus[source.type].status === 'error' ? 'error' : 'default'
                          }
                        />
                      </Box>
                      {syncStatus[source.type].status === 'syncing' && (
                        <Box>
                          <LinearProgress 
                            variant="determinate" 
                            value={syncStatus[source.type].progress} 
                            sx={{ mb: 1 }}
                          />
                          <Typography variant="caption" color="text.secondary">
                            {syncStatus[source.type].progress}% complete
                          </Typography>
                        </Box>
                      )}
                      {syncStatus[source.type].last_sync && (
                        <Typography variant="caption" color="text.secondary">
                          Last sync: {new Date(syncStatus[source.type].last_sync).toLocaleDateString()}
                        </Typography>
                      )}
                    </Box>
                  )}
                  
                  {!syncStatus[source.type] && dataSource?.last_sync && (
                    <Typography variant="caption" color="text.secondary">
                      Last sync: {new Date(dataSource.last_sync).toLocaleDateString()}
                    </Typography>
                  )}
                </CardContent>
                <CardActions>
                  {isConnected ? (
                    <Box sx={{ display: 'flex', gap: 1, width: '100%' }}>
                      <Button
                        size="small"
                        variant="outlined"
                        onClick={() => handleSync(source.type)}
                        sx={{ flex: 1 }}
                      >
                        Sync
                      </Button>
                      <Button
                        size="small"
                        color="error"
                        onClick={() => {
                          if (window.confirm('Are you sure you want to disconnect this data source?')) {
                            // TODO: Implement disconnect
                            alert('Disconnect functionality will be implemented');
                          }
                        }}
                      >
                        Disconnect
                      </Button>
                    </Box>
                  ) : (
                    <Button
                      size="small"
                      variant="contained"
                      onClick={() => handleConnect(source.type)}
                      fullWidth
                    >
                      Connect
                    </Button>
                  )}
                </CardActions>
              </Card>
            </Grid>
          );
        })}
      </Grid>
    </Container>
  );
};

export default DataSources;

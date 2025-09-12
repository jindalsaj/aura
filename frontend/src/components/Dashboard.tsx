import React, { useState, useEffect } from 'react';
import {
  Container,
  Typography,
  Grid,
  Card,
  CardContent,
  CardActions,
  Button,
  Box,
  Chip,
} from '@mui/material';
import {
  Home as HomeIcon,
  Storage as StorageIcon,
  Chat as ChatIcon,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { Property, DataSource } from '../types';

const Dashboard: React.FC = () => {
  const [properties, setProperties] = useState<Property[]>([]);
  const [dataSources, setDataSources] = useState<DataSource[]>([]);
  const [, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [propertiesRes, dataSourcesRes] = await Promise.all([
          api.get('/api/properties/'),
          api.get('/api/data-sources/'),
        ]);
        setProperties(propertiesRes.data);
        setDataSources(dataSourcesRes.data);
      } catch (error) {
        console.error('Error fetching dashboard data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const connectedSources = dataSources.filter(ds => ds.is_active).length;
  const totalSources = dataSources.length;

  return (
    <Container maxWidth="lg">
      <Typography variant="h4" component="h1" gutterBottom>
        Welcome to Aura
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Your personal home and property assistant
      </Typography>

      <Grid container spacing={3}>
        {/* Properties Overview */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <HomeIcon sx={{ mr: 1, color: 'primary.main' }} />
                <Typography variant="h6">Properties</Typography>
              </Box>
              <Typography variant="h3" color="primary.main">
                {properties.length}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Properties managed
              </Typography>
            </CardContent>
            <CardActions>
              <Button
                size="small"
                onClick={() => navigate('/properties')}
              >
                Manage Properties
              </Button>
            </CardActions>
          </Card>
        </Grid>

        {/* Data Sources Overview */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <StorageIcon sx={{ mr: 1, color: 'secondary.main' }} />
                <Typography variant="h6">Data Sources</Typography>
              </Box>
              <Typography variant="h3" color="secondary.main">
                {connectedSources}/{totalSources}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Connected sources
              </Typography>
            </CardContent>
            <CardActions>
              <Button
                size="small"
                onClick={() => navigate('/data-sources')}
              >
                Connect Sources
              </Button>
            </CardActions>
          </Card>
        </Grid>

        {/* Quick Actions */}
        <Grid size={{ xs: 12 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Quick Actions
              </Typography>
              <Grid container spacing={2}>
                <Grid>
                  <Button
                    variant="contained"
                    startIcon={<ChatIcon />}
                    onClick={() => navigate('/chat')}
                    sx={{ mr: 2 }}
                  >
                    Start Chat
                  </Button>
                </Grid>
                <Grid>
                  <Button
                    variant="outlined"
                    startIcon={<HomeIcon />}
                    onClick={() => navigate('/properties')}
                    sx={{ mr: 2 }}
                  >
                    Add Property
                  </Button>
                </Grid>
                <Grid>
                  <Button
                    variant="outlined"
                    startIcon={<StorageIcon />}
                    onClick={() => navigate('/data-sources')}
                  >
                    Connect Data
                  </Button>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* Recent Properties */}
        {properties.length > 0 && (
          <Grid size={{ xs: 12 }}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Your Properties
                </Typography>
                <Grid container spacing={2}>
                  {properties.slice(0, 3).map((property) => (
                    <Grid size={{ xs: 12, sm: 6, md: 4 }} key={property.id}>
                      <Card variant="outlined">
                        <CardContent>
                          <Typography variant="h6" gutterBottom>
                            {property.name}
                          </Typography>
                          <Typography variant="body2" color="text.secondary" gutterBottom>
                            {property.address}
                          </Typography>
                          {property.property_type && (
                            <Chip
                              label={property.property_type}
                              size="small"
                              color="primary"
                              variant="outlined"
                            />
                          )}
                        </CardContent>
                      </Card>
                    </Grid>
                  ))}
                </Grid>
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* Getting Started */}
        {properties.length === 0 && (
          <Grid size={{ xs: 12 }}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Get Started
                </Typography>
                <Typography variant="body1" color="text.secondary" paragraph>
                  Welcome to Aura! To get started, you'll want to:
                </Typography>
                <Box component="ol" sx={{ pl: 2 }}>
                  <li>Add your first property</li>
                  <li>Connect your data sources (Gmail, Bank, WhatsApp, Google Drive)</li>
                  <li>Start chatting with your personal assistant</li>
                </Box>
                <Button
                  variant="contained"
                  onClick={() => navigate('/properties')}
                  sx={{ mt: 2 }}
                >
                  Add Your First Property
                </Button>
              </CardContent>
            </Card>
          </Grid>
        )}
      </Grid>
    </Container>
  );
};

export default Dashboard;

import React, { useState, useEffect } from 'react';
import {
  Container,
  Paper,
  Typography,
  Button,
  Box,
  Stepper,
  Step,
  StepLabel,
  TextField,
  FormControl,
  RadioGroup,
  FormControlLabel,
  Radio,
  Checkbox,
  FormGroup,
  Card,
  CardContent,
  LinearProgress,
  Alert,
  Chip,
  IconButton,
  Fade,
  Slide,
  Zoom,
} from '@mui/material';
import {
  Home as HomeIcon,
  Email as EmailIcon,
  CalendarToday as CalendarIcon,
  CloudUpload as DriveIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
  CheckCircle as CheckCircleIcon,
  Sync as SyncIcon,
  SmartToy as AIIcon,
  ArrowForward as ArrowForwardIcon,
  ArrowBack as ArrowBackIcon,
} from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { onboardingApi } from '../services/onboardingApi';

interface Property {
  id: string;
  name: string;
  address: string;
}

interface GmailSyncOption {
  id: string;
  label: string;
  description: string;
  value: string;
}

interface DriveItem {
  id: string;
  name: string;
  type: 'folder' | 'document';
  selected: boolean;
}

const Onboarding: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  
  // Onboarding state
  const [activeStep, setActiveStep] = useState(0);
  const [completed, setCompleted] = useState<{ [k: number]: boolean }>({});
  
  // Property management
  const [properties, setProperties] = useState<Property[]>([
    { id: '1', name: '', address: '' }
  ]);
  
  // Service selection
  const [selectedServices, setSelectedServices] = useState<string[]>(['gmail']);
  const [gmailSyncOption, setGmailSyncOption] = useState('last_30_days');
  const [driveItems, setDriveItems] = useState<DriveItem[]>([]);
  
  // Sync status
  const [syncStatus, setSyncStatus] = useState<{ [key: string]: any }>({});
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncComplete, setSyncComplete] = useState(false);

  const steps = [
    {
      label: 'Welcome to Aura',
      description: 'Let\'s get to know your properties',
      icon: <HomeIcon />,
    },
    {
      label: 'Connect Services',
      description: 'Choose what to sync',
      icon: <SyncIcon />,
    },
    {
      label: 'Sync & Analyze',
      description: 'We\'re setting everything up',
      icon: <AIIcon />,
    },
    {
      label: 'Ready to Go!',
      description: 'Your AI assistant is ready',
      icon: <CheckCircleIcon />,
    },
  ];

  const gmailSyncOptions: GmailSyncOption[] = [
    {
      id: 'all',
      label: 'All Emails',
      description: 'Sync your entire email history',
      value: 'all'
    },
    {
      id: 'last_30_days',
      label: 'Last 30 Days',
      description: 'Recent emails for quick insights',
      value: 'last_30_days'
    },
    {
      id: 'last_90_days',
      label: 'Last 90 Days',
      description: 'Quarterly view of your communications',
      value: 'last_90_days'
    },
    {
      id: 'attachments_only',
      label: 'Emails with Attachments',
      description: 'Focus on documents and important files',
      value: 'attachments_only'
    }
  ];

  const serviceOptions = [
    {
      id: 'gmail',
      name: 'Gmail',
      description: 'Email communications and attachments',
      icon: <EmailIcon />,
      color: '#ea4335'
    },
    {
      id: 'calendar',
      name: 'Google Calendar',
      description: 'Events, meetings, and appointments',
      icon: <CalendarIcon />,
      color: '#4285f4'
    },
    {
      id: 'drive',
      name: 'Google Drive',
      description: 'Documents, files, and folders',
      icon: <DriveIcon />,
      color: '#34a853'
    }
  ];

  // Property management functions
  const addProperty = () => {
    const newProperty: Property = {
      id: Date.now().toString(),
      name: '',
      address: ''
    };
    setProperties([...properties, newProperty]);
  };

  const removeProperty = (id: string) => {
    if (properties.length > 1) {
      setProperties(properties.filter(p => p.id !== id));
    }
  };

  const updateProperty = (id: string, field: keyof Property, value: string) => {
    setProperties(properties.map(p => 
      p.id === id ? { ...p, [field]: value } : p
    ));
  };

  // Service selection functions
  const toggleService = (serviceId: string) => {
    setSelectedServices(prev => 
      prev.includes(serviceId) 
        ? prev.filter(id => id !== serviceId)
        : [...prev, serviceId]
    );
  };

  // Step navigation
  const handleNext = async () => {
    // Save properties when moving from step 0 to step 1
    if (activeStep === 0) {
      try {
        await onboardingApi.saveProperties({
          properties: properties.map(p => ({
            name: p.name,
            address: p.address,
            property_type: 'apartment' // Default type
          }))
        });
      } catch (error) {
        console.error('Error saving properties:', error);
        // Continue anyway
      }
    }
    
    setCompleted(prev => ({ ...prev, [activeStep]: true }));
    setActiveStep(prev => prev + 1);
  };

  const handleBack = () => {
    setActiveStep(prev => prev - 1);
  };

  const handleStepClick = (step: number) => {
    if (step <= activeStep || completed[step]) {
      setActiveStep(step);
    }
  };

  // Validation
  const canProceedFromStep = (step: number): boolean => {
    switch (step) {
      case 0:
        return properties.every(p => p.name.trim() && p.address.trim());
      case 1:
        return selectedServices.length > 0;
      case 2:
        return syncComplete;
      default:
        return true;
    }
  };

  // Real sync with API
  const startSync = async () => {
    setIsSyncing(true);
    setSyncStatus({});
    
    try {
      // Start the sync process
      await onboardingApi.startSync({
        properties: properties.map(p => ({
          name: p.name,
          address: p.address,
          property_type: 'apartment' // Default type
        })),
        selected_services: selectedServices,
        gmail_sync_option: gmailSyncOption,
        drive_selected_items: driveItems.filter(item => item.selected).map(item => item.id)
      });
      
      // Poll for sync status
      const pollStatus = async () => {
        try {
          const statusResponse = await onboardingApi.getSyncStatus();
          const services = statusResponse.services;
          
          // Update sync status
          const newStatus: { [key: string]: any } = {};
          services.forEach(service => {
            newStatus[service.source_type] = {
              status: service.status,
              progress: service.progress
            };
          });
          setSyncStatus(newStatus);
          
          // Check if all services are completed
          const allCompleted = services.every(s => s.status === 'completed');
          const anyError = services.some(s => s.status === 'error');
          
          if (allCompleted) {
            setIsSyncing(false);
            setSyncComplete(true);
            setTimeout(() => handleNext(), 1500);
          } else if (anyError) {
            setIsSyncing(false);
            // Handle error state
            console.error('Sync failed for some services');
          } else {
            // Continue polling
            setTimeout(pollStatus, 2000);
          }
        } catch (error) {
          console.error('Error polling sync status:', error);
          setIsSyncing(false);
        }
      };
      
      // Start polling
      setTimeout(pollStatus, 1000);
      
    } catch (error) {
      console.error('Error starting sync:', error);
      setIsSyncing(false);
    }
  };

  // Load drive items (mock)
  useEffect(() => {
    if (selectedServices.includes('drive') && activeStep === 1) {
      // Mock drive items
      setDriveItems([
        { id: '1', name: 'Documents', type: 'folder', selected: true },
        { id: '2', name: 'Property Files', type: 'folder', selected: true },
        { id: '3', name: 'Tax Documents', type: 'folder', selected: false },
        { id: '4', name: 'Lease Agreement.pdf', type: 'document', selected: true },
        { id: '5', name: 'Property Photos', type: 'folder', selected: false },
      ]);
    }
  }, [selectedServices, activeStep]);

  const renderWelcomeStep = () => (
    <Fade in={activeStep === 0} timeout={800}>
      <Box>
        <Box textAlign="center" mb={4}>
          <Zoom in timeout={1000}>
            <Box
              sx={{
                width: 80,
                height: 80,
                borderRadius: '50%',
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 24px',
                boxShadow: '0 8px 32px rgba(102, 126, 234, 0.3)'
              }}
            >
              <HomeIcon sx={{ fontSize: 40, color: 'white' }} />
            </Box>
          </Zoom>
          <Typography variant="h4" gutterBottom sx={{ fontWeight: 600, color: 'primary.main' }}>
            Welcome to Aura{user?.name ? `, ${user.name}` : ''}! 🏠
          </Typography>
          <Typography variant="h6" color="text.secondary" sx={{ mb: 3 }}>
            Your Personal Home & Property Assistant
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ maxWidth: 600, mx: 'auto' }}>
            Let's start by learning about your properties. This helps Aura provide personalized insights 
            and organize your property-related information intelligently.
          </Typography>
        </Box>

        <Box sx={{ maxWidth: 600, mx: 'auto' }}>
          {properties.map((property, index) => (
            <Slide direction="up" in timeout={600 + index * 200} key={property.id}>
              <Card sx={{ mb: 2, border: '2px solid', borderColor: 'grey.200' }}>
                <CardContent>
                  <Box display="flex" alignItems="center" mb={2}>
                    <HomeIcon sx={{ mr: 1, color: 'primary.main' }} />
                    <Typography variant="h6">
                      Property {index + 1}
                    </Typography>
                    {properties.length > 1 && (
                      <IconButton 
                        onClick={() => removeProperty(property.id)}
                        sx={{ ml: 'auto', color: 'error.main' }}
                      >
                        <DeleteIcon />
                      </IconButton>
                    )}
                  </Box>
                  
                  <TextField
                    fullWidth
                    label="Property Name"
                    placeholder="e.g., My Apartment, Rental Property, Vacation Home"
                    value={property.name}
                    onChange={(e) => updateProperty(property.id, 'name', e.target.value)}
                    sx={{ mb: 2 }}
                  />
                  
                  <TextField
                    fullWidth
                    label="Address"
                    placeholder="123 Main St, City, State, ZIP"
                    value={property.address}
                    onChange={(e) => updateProperty(property.id, 'address', e.target.value)}
                    multiline
                    rows={2}
                  />
                </CardContent>
              </Card>
            </Slide>
          ))}

          <Box textAlign="center" mt={3}>
            <Button
              variant="outlined"
              startIcon={<AddIcon />}
              onClick={addProperty}
              sx={{ 
                borderStyle: 'dashed',
                borderWidth: 2,
                py: 1.5,
                px: 3
              }}
            >
              Add Another Property
            </Button>
          </Box>
        </Box>
      </Box>
    </Fade>
  );

  const renderServicesStep = () => (
    <Fade in={activeStep === 1} timeout={800}>
      <Box>
        <Box textAlign="center" mb={4}>
          <Typography variant="h4" gutterBottom sx={{ fontWeight: 600, color: 'primary.main' }}>
            Connect Your Services 🔗
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ maxWidth: 600, mx: 'auto' }}>
            Choose which Google services you'd like Aura to analyze. We'll only sync data 
            relevant to your properties and keep everything secure.
          </Typography>
        </Box>

        <Box sx={{ maxWidth: 800, mx: 'auto' }}>
          {/* Service Selection */}
          <Typography variant="h6" gutterBottom sx={{ mb: 3 }}>
            Select Services to Connect
          </Typography>
          
          <Box display="flex" flexDirection="column" gap={2} mb={4}>
            {serviceOptions.map((service) => (
              <Slide direction="up" in timeout={600} key={service.id}>
                <Card 
                  sx={{ 
                    border: selectedServices.includes(service.id) ? '2px solid' : '1px solid',
                    borderColor: selectedServices.includes(service.id) ? 'primary.main' : 'grey.300',
                    cursor: 'pointer',
                    transition: 'all 0.3s ease',
                    '&:hover': {
                      borderColor: 'primary.main',
                      boxShadow: 2
                    }
                  }}
                  onClick={() => toggleService(service.id)}
                >
                  <CardContent>
                    <Box display="flex" alignItems="center">
                      <Box
                        sx={{
                          width: 48,
                          height: 48,
                          borderRadius: '12px',
                          backgroundColor: service.color,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          mr: 2
                        }}
                      >
                        {service.icon}
                      </Box>
                      <Box flex={1}>
                        <Typography variant="h6" gutterBottom>
                          {service.name}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {service.description}
                        </Typography>
                      </Box>
                      <Checkbox
                        checked={selectedServices.includes(service.id)}
                        onChange={() => toggleService(service.id)}
                        sx={{ ml: 2 }}
                      />
                    </Box>
                  </CardContent>
                </Card>
              </Slide>
            ))}
          </Box>

          {/* Gmail Sync Options */}
          {selectedServices.includes('gmail') && (
            <Slide direction="up" in timeout={800}>
              <Box mb={4}>
                <Typography variant="h6" gutterBottom>
                  Gmail Sync Options
                </Typography>
                <FormControl component="fieldset">
                  <RadioGroup
                    value={gmailSyncOption}
                    onChange={(e) => setGmailSyncOption(e.target.value)}
                  >
                    {gmailSyncOptions.map((option) => (
                      <FormControlLabel
                        key={option.id}
                        value={option.value}
                        control={<Radio />}
                        label={
                          <Box>
                            <Typography variant="body1" sx={{ fontWeight: 500 }}>
                              {option.label}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                              {option.description}
                            </Typography>
                          </Box>
                        }
                        sx={{ mb: 1 }}
                      />
                    ))}
                  </RadioGroup>
                </FormControl>
              </Box>
            </Slide>
          )}

          {/* Drive Selection */}
          {selectedServices.includes('drive') && driveItems.length > 0 && (
            <Slide direction="up" in timeout={1000}>
              <Box>
                <Typography variant="h6" gutterBottom>
                  Select Drive Folders & Documents
                </Typography>
                <Card>
                  <CardContent>
                    <FormGroup>
                      {driveItems.map((item) => (
                        <FormControlLabel
                          key={item.id}
                          control={
                            <Checkbox
                              checked={item.selected}
                              onChange={(e) => setDriveItems(prev => 
                                prev.map(d => d.id === item.id ? { ...d, selected: e.target.checked } : d)
                              )}
                            />
                          }
                          label={
                            <Box display="flex" alignItems="center">
                              {item.type === 'folder' ? <DriveIcon /> : <EmailIcon />}
                              <Typography sx={{ ml: 1 }}>
                                {item.name}
                              </Typography>
                              <Chip 
                                label={item.type} 
                                size="small" 
                                sx={{ ml: 1 }}
                                color={item.type === 'folder' ? 'primary' : 'secondary'}
                              />
                            </Box>
                          }
                        />
                      ))}
                    </FormGroup>
                  </CardContent>
                </Card>
              </Box>
            </Slide>
          )}
        </Box>
      </Box>
    </Fade>
  );

  const renderSyncStep = () => (
    <Fade in={activeStep === 2} timeout={800}>
      <Box>
        <Box textAlign="center" mb={4}>
          <Typography variant="h4" gutterBottom sx={{ fontWeight: 600, color: 'primary.main' }}>
            Syncing Your Data 🤖
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ maxWidth: 600, mx: 'auto' }}>
            Aura is analyzing your data and using AI to identify property-related information. 
            This usually takes just a few moments.
          </Typography>
        </Box>

        <Box sx={{ maxWidth: 600, mx: 'auto' }}>
          {selectedServices.map((serviceId, index) => {
            const service = serviceOptions.find(s => s.id === serviceId);
            const status = syncStatus[serviceId];
            
            return (
              <Slide direction="up" in timeout={600 + index * 200} key={serviceId}>
                <Card sx={{ mb: 2 }}>
                  <CardContent>
                    <Box display="flex" alignItems="center" mb={2}>
                      <Box
                        sx={{
                          width: 40,
                          height: 40,
                          borderRadius: '8px',
                          backgroundColor: service?.color,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          mr: 2
                        }}
                      >
                        {service?.icon}
                      </Box>
                      <Box flex={1}>
                        <Typography variant="h6">
                          {service?.name}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {status?.status === 'completed' ? 'Sync completed' : 'Syncing...'}
                        </Typography>
                      </Box>
                      {status?.status === 'completed' && (
                        <CheckCircleIcon sx={{ color: 'success.main' }} />
                      )}
                    </Box>
                    
                    {status && (
                      <LinearProgress 
                        variant="determinate" 
                        value={status.progress} 
                        sx={{ height: 8, borderRadius: 4 }}
                      />
                    )}
                  </CardContent>
                </Card>
              </Slide>
            );
          })}

          {!isSyncing && !syncComplete && (
            <Box textAlign="center" mt={4}>
              <Button
                variant="contained"
                size="large"
                onClick={startSync}
                startIcon={<SyncIcon />}
                sx={{ py: 1.5, px: 4 }}
              >
                Start Sync
              </Button>
            </Box>
          )}

          {syncComplete && (
            <Zoom in timeout={800}>
              <Alert severity="success" sx={{ mt: 3 }}>
                <Typography variant="h6" gutterBottom>
                  🎉 Sync Complete!
                </Typography>
                <Typography>
                  Aura has successfully analyzed your data and identified property-related information. 
                  You're ready to start chatting with your AI assistant!
                </Typography>
              </Alert>
            </Zoom>
          )}
        </Box>
      </Box>
    </Fade>
  );

  const renderCompletionStep = () => (
    <Fade in={activeStep === 3} timeout={800}>
      <Box textAlign="center">
        <Zoom in timeout={1000}>
          <Box
            sx={{
              width: 120,
              height: 120,
              borderRadius: '50%',
              background: 'linear-gradient(135deg, #4caf50 0%, #8bc34a 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 32px',
              boxShadow: '0 12px 40px rgba(76, 175, 80, 0.3)'
            }}
          >
            <CheckCircleIcon sx={{ fontSize: 60, color: 'white' }} />
          </Box>
        </Zoom>
        
        <Typography variant="h3" gutterBottom sx={{ fontWeight: 600, color: 'primary.main' }}>
          You're All Set! 🚀
        </Typography>
        
        <Typography variant="h6" color="text.secondary" sx={{ mb: 4, maxWidth: 600, mx: 'auto' }}>
          Aura is now your personal property assistant. Ask questions about your properties, 
          get insights from your emails and documents, and manage everything in one place.
        </Typography>

        <Box sx={{ maxWidth: 400, mx: 'auto', mb: 4 }}>
          <Alert severity="info" sx={{ mb: 3 }}>
            <Typography variant="body2">
              💡 <strong>Try asking:</strong> "What's in my recent emails about my properties?" 
              or "Show me my property documents"
            </Typography>
          </Alert>
        </Box>

        <Button
          variant="contained"
          size="large"
          endIcon={<ArrowForwardIcon />}
          onClick={() => navigate('/app/chat')}
          sx={{ 
            py: 2, 
            px: 6,
            fontSize: '1.1rem',
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            '&:hover': {
              background: 'linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%)',
            }
          }}
        >
          Start Chatting with Aura
        </Button>
      </Box>
    </Fade>
  );

  const renderStepContent = () => {
    switch (activeStep) {
      case 0:
        return renderWelcomeStep();
      case 1:
        return renderServicesStep();
      case 2:
        return renderSyncStep();
      case 3:
        return renderCompletionStep();
      default:
        return null;
    }
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Paper elevation={3} sx={{ p: 4, borderRadius: 3 }}>
        {/* Progress Stepper */}
        <Stepper activeStep={activeStep} alternativeLabel sx={{ mb: 6 }}>
          {steps.map((step, index) => (
            <Step key={step.label} completed={completed[index]}>
              <StepLabel
                onClick={() => handleStepClick(index)}
                sx={{ cursor: 'pointer' }}
                StepIconComponent={({ active, completed }) => (
                  <Box
                    sx={{
                      width: 40,
                      height: 40,
                      borderRadius: '50%',
                      backgroundColor: completed ? 'success.main' : active ? 'primary.main' : 'grey.300',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: 'white',
                      transition: 'all 0.3s ease'
                    }}
                  >
                    {completed ? <CheckCircleIcon /> : step.icon}
                  </Box>
                )}
              >
                <Typography variant="h6" sx={{ fontWeight: 600 }}>
                  {step.label}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {step.description}
                </Typography>
              </StepLabel>
            </Step>
          ))}
        </Stepper>

        {/* Step Content */}
        <Box sx={{ minHeight: 500 }}>
          {renderStepContent()}
        </Box>

        {/* Navigation */}
        {activeStep < 3 && (
          <Box display="flex" justifyContent="space-between" mt={6}>
            <Button
              onClick={handleBack}
              disabled={activeStep === 0}
              startIcon={<ArrowBackIcon />}
              sx={{ py: 1.5, px: 3 }}
            >
              Back
            </Button>
            
            <Button
              variant="contained"
              onClick={handleNext}
              disabled={!canProceedFromStep(activeStep)}
              endIcon={<ArrowForwardIcon />}
              sx={{ py: 1.5, px: 4 }}
            >
              {activeStep === 2 ? 'Complete Setup' : 'Continue'}
            </Button>
          </Box>
        )}
      </Paper>
    </Container>
  );
};

export default Onboarding;

import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  Alert,
  Checkbox,
  FormControlLabel,
} from '@mui/material';
import { Security as SecurityIcon } from '@mui/icons-material';

interface PrivacyNoticeProps {
  open: boolean;
  onAccept: () => void;
  onDecline: () => void;
}

const PrivacyNotice: React.FC<PrivacyNoticeProps> = ({ open, onAccept, onDecline }) => {
  const [accepted, setAccepted] = useState(false);

  return (
    <Dialog open={open} maxWidth="md" fullWidth>
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <SecurityIcon color="primary" />
        Data Privacy & Security Notice
      </DialogTitle>
      
      <DialogContent>
        <Alert severity="info" sx={{ mb: 2 }}>
          Your privacy and data security are our top priorities. Here's how we protect your information:
        </Alert>

        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            🔒 Data Protection Measures
          </Typography>
          <Typography variant="body2" paragraph>
            • <strong>No Training Data Usage:</strong> OpenAI is configured to NOT use your data for AI model training
          </Typography>
          <Typography variant="body2" paragraph>
            • <strong>Data Sanitization:</strong> Personal information (emails, phone numbers, SSNs) is automatically masked before processing
          </Typography>
          <Typography variant="body2" paragraph>
            • <strong>Content Limiting:</strong> Only relevant portions of your data are sent to the AI service
          </Typography>
          <Typography variant="body2" paragraph>
            • <strong>Secure Transmission:</strong> All data is encrypted in transit using HTTPS
          </Typography>
        </Box>

        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            🤖 How AI Processing Works
          </Typography>
          <Typography variant="body2" paragraph>
            When you ask questions, Aura:
          </Typography>
          <Typography variant="body2" component="div" sx={{ pl: 2 }}>
            1. Analyzes your query to determine what data is relevant<br/>
            2. Retrieves only the necessary information from your synced accounts<br/>
            3. Sanitizes personal data before sending to OpenAI<br/>
            4. Generates intelligent responses based on your data<br/>
            5. Never stores your data in OpenAI's systems
          </Typography>
        </Box>

        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            📊 What Data is Processed
          </Typography>
          <Typography variant="body2" paragraph>
            • <strong>Emails:</strong> Subject lines, sender info (masked), and content previews (sanitized)
          </Typography>
          <Typography variant="body2" paragraph>
            • <strong>Documents:</strong> Titles, types, and content previews (sanitized)
          </Typography>
          <Typography variant="body2" paragraph>
            • <strong>Properties:</strong> Names, addresses, and types
          </Typography>
          <Typography variant="body2" paragraph>
            • <strong>Expenses:</strong> Amounts, categories, and descriptions
          </Typography>
        </Box>

        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            ⚡ Your Control
          </Typography>
          <Typography variant="body2" paragraph>
            • You can disconnect data sources at any time<br/>
            • You can delete your account and all associated data<br/>
            • You can ask questions without specific personal details<br/>
            • All processing happens in real-time, no data is permanently stored by AI services
          </Typography>
        </Box>

        <FormControlLabel
          control={
            <Checkbox
              checked={accepted}
              onChange={(e) => setAccepted(e.target.checked)}
              color="primary"
            />
          }
          label="I understand how my data is protected and agree to use AI-powered features"
        />
      </DialogContent>

      <DialogActions>
        <Button onClick={onDecline} color="secondary">
          Decline AI Features
        </Button>
        <Button 
          onClick={onAccept} 
          variant="contained" 
          disabled={!accepted}
          color="primary"
        >
          Accept & Continue
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default PrivacyNotice;

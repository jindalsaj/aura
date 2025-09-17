import React, { useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import amplitudeService from '../services/amplitudeService';

const PageTracker: React.FC = () => {
  const location = useLocation();
  const { user } = useAuth();

  useEffect(() => {
    // Set user ID and email for Amplitude tracking
    if (user?.id) {
      amplitudeService.setUserInfo(user.id.toString(), user.email || null);
    }

    // Track page visit
    const trackPageVisit = async () => {
      const pathname = location.pathname;
      let pageName = 'Unknown';

      // Map routes to page names
      switch (pathname) {
        case '/':
          pageName = 'Home';
          break;
        case '/login':
          pageName = 'Login';
          break;
        case '/register':
          pageName = 'Register';
          break;
        case '/app/dashboard':
          pageName = 'Dashboard';
          break;
        case '/app/chat':
          pageName = 'Chat';
          break;
        case '/app/properties':
          pageName = 'Properties';
          break;
        case '/app/data-sources':
          pageName = 'Data Sources';
          break;
        case '/onboarding':
          pageName = 'Onboarding';
          break;
        default:
          pageName = pathname.replace('/', '').replace(/\//g, ' - ') || 'Home';
      }

      await amplitudeService.trackPageVisit(pageName);
    };

    trackPageVisit();
  }, [location.pathname, user?.id]);

  return null; // This component doesn't render anything
};

export default PageTracker;

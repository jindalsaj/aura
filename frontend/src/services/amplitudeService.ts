// Amplitude tracking service for frontend
const AMPLITUDE_API_KEY = '32508d20fbb76ee720aade9a896e02e0';
const AMPLITUDE_ENDPOINT = 'https://api2.amplitude.com/2/httpapi';

interface AmplitudeEvent {
  event_type: string;
  user_id?: string;
  device_id?: string;
  event_properties?: Record<string, any>;
  user_properties?: Record<string, any>;
  insert_id?: string;
  time?: number;
}

interface AmplitudePayload {
  api_key: string;
  events: AmplitudeEvent[];
  user_properties?: Record<string, any>;
}

class AmplitudeService {
  private deviceId: string;
  private userId: string | null = null;
  private userEmail: string | null = null;

  constructor() {
    // Generate or retrieve device ID
    this.deviceId = this.getOrCreateDeviceId();
  }

  private getOrCreateDeviceId(): string {
    const stored = localStorage.getItem('amplitude_device_id');
    if (stored) {
      return stored;
    }
    
    // Generate a new device ID
    const deviceId = 'web_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
    localStorage.setItem('amplitude_device_id', deviceId);
    return deviceId;
  }

  setUserId(userId: string | null) {
    this.userId = userId;
  }

  setUserEmail(email: string | null) {
    this.userEmail = email;
  }

  setUserInfo(userId: string | null, email: string | null) {
    this.userId = userId;
    this.userEmail = email;
  }

  private generateInsertId(): string {
    return 'web_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
  }

  async trackEvent(
    eventType: string,
    eventProperties?: Record<string, any>,
    userProperties?: Record<string, any>
  ): Promise<boolean> {
    try {
      const event: AmplitudeEvent = {
        event_type: eventType,
        device_id: this.deviceId,
        time: Date.now(),
        insert_id: this.generateInsertId()
      };

      if (this.userId) {
        event.user_id = this.userId;
      }

      if (eventProperties) {
        event.event_properties = eventProperties;
      }

      // Add email to event properties if available
      if (this.userEmail && event.event_properties) {
        event.event_properties.user_email = this.userEmail;
      }

      const payload: AmplitudePayload = {
        api_key: AMPLITUDE_API_KEY,
        events: [event]
      };

      // Always include email in user properties if available
      const finalUserProperties = { ...userProperties };
      if (this.userEmail) {
        finalUserProperties.email = this.userEmail;
        finalUserProperties.user_email = this.userEmail;
      }

      if (Object.keys(finalUserProperties).length > 0) {
        payload.user_properties = finalUserProperties;
      }

      const response = await fetch(AMPLITUDE_ENDPOINT, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': '*/*'
        },
        body: JSON.stringify(payload)
      });

      if (response.ok) {
        console.log(`Amplitude event tracked: ${eventType}`);
        return true;
      } else {
        console.error(`Failed to track Amplitude event: ${response.status}`);
        return false;
      }
    } catch (error) {
      console.error('Error tracking Amplitude event:', error);
      return false;
    }
  }

  // Specific tracking methods
  async trackPageVisit(pageName: string): Promise<boolean> {
    return this.trackEvent('Page Visit', {
      page_name: pageName,
      timestamp: new Date().toISOString()
    });
  }

  async trackGoogleSignInAttempt(): Promise<boolean> {
    return this.trackEvent('Google Sign In Attempt', {
      signin_method: 'google'
    });
  }

  async trackDataSyncStart(sourceType: string, itemsCount?: number): Promise<boolean> {
    const properties: Record<string, any> = {
      source_type: sourceType,
      sync_status: 'started'
    };
    
    if (itemsCount !== undefined) {
      properties.items_count = itemsCount;
    }

    return this.trackEvent('Data Source Sync', properties);
  }

  async trackDataSyncComplete(sourceType: string, itemsCount?: number): Promise<boolean> {
    const properties: Record<string, any> = {
      source_type: sourceType,
      sync_status: 'completed'
    };
    
    if (itemsCount !== undefined) {
      properties.items_count = itemsCount;
    }

    return this.trackEvent('Data Source Sync', properties);
  }

  async trackDataSyncError(sourceType: string, error: string): Promise<boolean> {
    return this.trackEvent('Data Source Sync', {
      source_type: sourceType,
      sync_status: 'error',
      error_message: error
    });
  }

  async trackUserRegistration(email: string, name: string): Promise<boolean> {
    return this.trackEvent('User Registration', {
      email: email,
      name: name,
      user_email: email
    }, {
      email: email,
      name: name,
      user_email: email
    });
  }
}

// Export singleton instance
export const amplitudeService = new AmplitudeService();
export default amplitudeService;

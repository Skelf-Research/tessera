import React, { useState } from 'react';
import {
  TouchableOpacity,
  View,
  Text,
  ActivityIndicator,
  StyleSheet,
  ViewStyle,
  TextStyle,
} from 'react-native';
import { TesseraClient, VerifiedCallDestination, OutboundCallResult } from './index';

interface VerifiedCallButtonProps {
  phoneNumber: string;
  destinationId: string;
  destinationName?: string;
  config?: VerifiedCallButtonConfig;
  onCallInitiated?: (result: OutboundCallResult) => void;
  onError?: (error: string) => void;
  style?: ViewStyle;
}

interface VerifiedCallButtonConfig {
  buttonText?: string;
  buttonColor?: string;
  buttonHeight?: number;
  cornerRadius?: number;
  showInfoText?: boolean;
  showDestination?: boolean;
}

type ButtonState = 'ready' | 'generating' | 'broadcasting' | 'readyToDial' | 'error';

export const VerifiedSenderButton: React.FC<VerifiedCallButtonProps> = ({
  phoneNumber,
  destinationId,
  destinationName = 'Organization',
  config = {},
  onCallInitiated,
  onError,
  style,
}) => {
  const [buttonState, setButtonState] = useState<ButtonState>('ready');
  const [errorMessage, setErrorMessage] = useState<string>('');

  const {
    buttonText = 'Call with Verification',
    buttonColor = '#1976D2',
    buttonHeight = 56,
    cornerRadius = 12,
    showInfoText = true,
    showDestination = true,
  } = config;

  const getButtonColor = (): string => {
    switch (buttonState) {
      case 'readyToDial':
        return '#4CAF50';
      case 'error':
        return '#F44336';
      default:
        return buttonColor;
    }
  };

  const initiateVerifiedCall = async () => {
    if (buttonState !== 'ready') return;

    setButtonState('generating');

    try {
      const client = TesseraClient.getInstance();

      const destination: VerifiedCallDestination = {
        destinationId,
        destinationName,
        phoneNumber,
      };

      const result = await client.prepareVerifiedCall(destination);

      setButtonState('broadcasting');

      // Short delay to show broadcasting state
      await new Promise(resolve => setTimeout(resolve, 300));

      setButtonState('readyToDial');

      // Open phone dialer
      await new Promise(resolve => setTimeout(resolve, 500));
      await client.openDialer(phoneNumber);

      onCallInitiated?.(result);

      // Reset after dial
      await new Promise(resolve => setTimeout(resolve, 1000));
      setButtonState('ready');

    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      setButtonState('error');
      setErrorMessage(message);
      onError?.(message);

      // Reset after error display
      await new Promise(resolve => setTimeout(resolve, 3000));
      setButtonState('ready');
    }
  };

  const renderButtonContent = () => {
    switch (buttonState) {
      case 'ready':
        return (
          <View style={styles.buttonContent}>
            <Text style={styles.buttonIcon}>🛡️</Text>
            <Text style={styles.buttonText}>{buttonText}</Text>
          </View>
        );
      case 'generating':
        return (
          <View style={styles.buttonContent}>
            <ActivityIndicator size="small" color="#FFFFFF" />
            <Text style={styles.buttonText}>Generating proof...</Text>
          </View>
        );
      case 'broadcasting':
        return (
          <View style={styles.buttonContent}>
            <ActivityIndicator size="small" color="#FFFFFF" />
            <Text style={styles.buttonText}>Broadcasting...</Text>
          </View>
        );
      case 'readyToDial':
        return (
          <View style={styles.buttonContent}>
            <Text style={styles.buttonIcon}>✓</Text>
            <Text style={styles.buttonText}>Opening dialer...</Text>
          </View>
        );
      case 'error':
        return (
          <View style={styles.buttonContent}>
            <Text style={styles.buttonIcon}>⚠️</Text>
            <Text style={styles.buttonTextSmall}>{errorMessage.substring(0, 30)}</Text>
          </View>
        );
    }
  };

  return (
    <View style={[styles.container, style]}>
      <TouchableOpacity
        onPress={initiateVerifiedCall}
        disabled={buttonState !== 'ready'}
        style={[
          styles.button,
          {
            backgroundColor: getButtonColor(),
            height: buttonHeight,
            borderRadius: cornerRadius,
          },
        ]}
        activeOpacity={0.8}
      >
        {renderButtonContent()}
      </TouchableOpacity>

      {showInfoText && (
        <Text style={styles.infoText}>
          Your identity will be cryptographically verified
        </Text>
      )}

      {showDestination && (
        <View style={styles.destinationContainer}>
          <Text style={styles.destinationText}>
            📞 {destinationName}: {phoneNumber}
          </Text>
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
  },
  button: {
    width: '100%',
    justifyContent: 'center',
    alignItems: 'center',
  },
  buttonContent: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  buttonIcon: {
    fontSize: 16,
    marginRight: 8,
  },
  buttonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '500',
  },
  buttonTextSmall: {
    color: '#FFFFFF',
    fontSize: 14,
  },
  infoText: {
    marginTop: 8,
    fontSize: 12,
    color: '#666666',
  },
  destinationContainer: {
    marginTop: 4,
    flexDirection: 'row',
    alignItems: 'center',
  },
  destinationText: {
    fontSize: 11,
    color: '#888888',
  },
});

export default VerifiedSenderButton;

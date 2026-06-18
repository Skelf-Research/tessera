import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Animated,
  ActivityIndicator,
  TouchableOpacity,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import CryptoJS from 'react-native-crypto-js';

// Types
export interface TesseraConfig {
  baseUrl?: string;
  apiKey?: string;
  cacheTimeout?: number;
  enableLogging?: boolean;
  maxRetries?: number;
}

export enum CallType {
  VOICE_CALL = 'VOICE_CALL',
  VIDEO_CALL = 'VIDEO_CALL',
  VOIP_CALL = 'VOIP_CALL',
  IN_APP_CALL = 'IN_APP_CALL',
  CONFERENCE_CALL = 'CONFERENCE_CALL',
  EMERGENCY_CALL = 'EMERGENCY_CALL',
  UNKNOWN = 'UNKNOWN',
}

export interface CallContext {
  callerId: string;
  calleeId?: string;
  callType: CallType;
  sessionId?: string;
  timestamp?: number;
  metadata?: Record<string, any>;
  appContext?: string;
  networkInfo?: NetworkInfo;
}

export interface NetworkInfo {
  ipAddress?: string;
  userAgent?: string;
  platform: string;
}

export interface VerificationResult {
  isVerified: boolean;
  callerInfo?: CallerInfo;
  confidence: VerificationConfidence;
  callType: CallType;
  timestamp: number;
  metadata?: Record<string, any>;
  error?: string;
}

export interface CallerInfo {
  displayName?: string;
  organization?: string;
  verified: boolean;
  trustScore: number;
  verificationLevel?: VerificationLevel;
  profileImage?: string;
}

export enum VerificationConfidence {
  NONE = 'NONE',
  LOW = 'LOW',
  MEDIUM = 'MEDIUM',
  HIGH = 'HIGH',
  ABSOLUTE = 'ABSOLUTE',
}

export enum VerificationLevel {
  BASIC = 'BASIC',
  PHONE = 'PHONE',
  EMAIL = 'EMAIL',
  DOCUMENT = 'DOCUMENT',
  ENTERPRISE = 'ENTERPRISE',
}

export interface TesseraWidgetConfig {
  showTrustScore?: boolean;
  showOrganization?: boolean;
  showVerificationBadge?: boolean;
  autoVerify?: boolean;
  theme?: 'light' | 'dark' | 'auto';
  position?: 'top' | 'bottom' | 'center';
  size?: 'small' | 'medium' | 'large';
}

// Tessera Client Class
export class TesseraClient {
  private static instance: TesseraClient | null = null;
  private config: TesseraConfig;
  private verificationCache: Map<string, VerificationResult> = new Map();

  private constructor(config: TesseraConfig) {
    this.config = {
      baseUrl: 'https://api.tessera.com',
      cacheTimeout: 5 * 60 * 1000, // 5 minutes
      enableLogging: false,
      maxRetries: 3,
      ...config,
    };
  }

  public static initialize(config: TesseraConfig): TesseraClient {
    if (!TesseraClient.instance) {
      TesseraClient.instance = new TesseraClient(config);
    }
    return TesseraClient.instance;
  }

  public static getInstance(): TesseraClient {
    if (!TesseraClient.instance) {
      throw new Error('TesseraClient not initialized');
    }
    return TesseraClient.instance;
  }

  public async generateCallProof(callContext: CallContext): Promise<any> {
    try {
      // Generate zero-knowledge proof
      const identity = await this.getOrCreateIdentity();
      const proof = await this.createProof(identity, callContext);

      // Register with network
      const response = await fetch(`${this.config.baseUrl}/api/register-proof`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(this.config.apiKey && { Authorization: `Bearer ${this.config.apiKey}` }),
        },
        body: JSON.stringify(proof),
      });

      if (!response.ok) {
        throw new Error(`Failed to register proof: ${response.status}`);
      }

      this.log('Proof generated and registered');
      return proof;
    } catch (error) {
      this.log('Error generating proof:', error);
      throw error;
    }
  }

  public async verifyIncomingCall(callContext: CallContext): Promise<VerificationResult> {
    try {
      const cacheKey = this.generateCacheKey(callContext);

      // Check cache first
      const cached = this.verificationCache.get(cacheKey);
      if (cached && Date.now() - cached.timestamp < (this.config.cacheTimeout || 300000)) {
        return cached;
      }

      // Look up proof from network
      const response = await fetch(
        `${this.config.baseUrl}/api/lookup-proof?` +
          new URLSearchParams({
            callerId: callContext.callerId,
            callType: callContext.callType,
            timestamp: (callContext.timestamp || Date.now()).toString(),
          }),
        {
          headers: {
            ...(this.config.apiKey && { Authorization: `Bearer ${this.config.apiKey}` }),
          },
        }
      );

      let result: VerificationResult;

      if (response.ok) {
        const proof = await response.json();
        const isValid = await this.verifyProof(proof, callContext);

        result = {
          isVerified: isValid,
          callerInfo: isValid ? this.extractCallerInfo(proof) : undefined,
          confidence: isValid ? VerificationConfidence.HIGH : VerificationConfidence.NONE,
          callType: callContext.callType,
          timestamp: Date.now(),
          metadata: proof.metadata,
        };
      } else {
        result = {
          isVerified: false,
          callerInfo: undefined,
          confidence: VerificationConfidence.NONE,
          callType: callContext.callType,
          timestamp: Date.now(),
        };
      }

      // Cache result
      this.verificationCache.set(cacheKey, result);

      this.log('Verification complete:', result.isVerified);
      return result;
    } catch (error) {
      this.log('Error verifying call:', error);
      return {
        isVerified: false,
        callerInfo: undefined,
        confidence: VerificationConfidence.NONE,
        callType: callContext.callType,
        timestamp: Date.now(),
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  private async getOrCreateIdentity(): Promise<any> {
    try {
      const stored = await AsyncStorage.getItem('@tessera_identity');
      if (stored) {
        return JSON.parse(stored);
      }

      // Generate new identity
      const identity = {
        privateKey: CryptoJS.lib.WordArray.random(32).toString(),
        publicKey: CryptoJS.lib.WordArray.random(64).toString(),
        created: Date.now(),
      };

      await AsyncStorage.setItem('@tessera_identity', JSON.stringify(identity));
      return identity;
    } catch (error) {
      throw new Error('Failed to get or create identity');
    }
  }

  private async createProof(identity: any, callContext: CallContext): Promise<any> {
    // Simplified proof generation (real implementation would use proper cryptography)
    const message = JSON.stringify({
      callerId: callContext.callerId,
      callType: callContext.callType,
      timestamp: callContext.timestamp || Date.now(),
    });

    const signature = CryptoJS.HmacSHA256(message, identity.privateKey).toString();

    return {
      proofId: CryptoJS.lib.WordArray.random(16).toString(),
      publicKey: identity.publicKey,
      signature,
      commitment: CryptoJS.SHA256(message).toString(),
      callContext,
      timestamp: Date.now(),
    };
  }

  private async verifyProof(proof: any, callContext: CallContext): Promise<boolean> {
    // Simplified proof verification
    try {
      const message = JSON.stringify({
        callerId: callContext.callerId,
        callType: callContext.callType,
        timestamp: callContext.timestamp || Date.now(),
      });

      const expectedCommitment = CryptoJS.SHA256(message).toString();
      return proof.commitment === expectedCommitment;
    } catch {
      return false;
    }
  }

  private extractCallerInfo(proof: any): CallerInfo | undefined {
    if (!proof.metadata) return undefined;

    return {
      displayName: proof.metadata.displayName,
      organization: proof.metadata.organization,
      verified: true,
      trustScore: this.calculateTrustScore(proof),
      verificationLevel: VerificationLevel.BASIC,
      profileImage: proof.metadata.profileImage,
    };
  }

  private calculateTrustScore(proof: any): number {
    let score = 0.5;

    if (proof.metadata?.organization) score += 0.2;
    if (proof.metadata?.verified_domain) score += 0.3;

    return Math.min(1.0, score);
  }

  private generateCacheKey(callContext: CallContext): string {
    return `${callContext.callerId}_${callContext.callType}_${callContext.sessionId || 'unknown'}`;
  }

  private log(...args: any[]): void {
    if (this.config.enableLogging) {
      console.log('[Tessera]', ...args);
    }
  }

  public clearCache(): void {
    this.verificationCache.clear();
  }
}

// React Hook
export const useTesseraVerification = (
  callContext: CallContext,
  config?: TesseraWidgetConfig
) => {
  const [verificationResult, setVerificationResult] = useState<VerificationResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const verify = useCallback(async () => {
    if (!callContext || isLoading) return;

    setIsLoading(true);
    setError(null);

    try {
      const client = TesseraClient.getInstance();
      const result = await client.verifyIncomingCall(callContext);
      setVerificationResult(result);

      if (result.error) {
        setError(result.error);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Verification failed';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, [callContext, isLoading]);

  useEffect(() => {
    if (config?.autoVerify !== false) {
      verify();
    }
  }, [verify, config?.autoVerify]);

  return {
    verificationResult,
    isLoading,
    error,
    verify,
  };
};

// React Component
export interface CallVerificationWidgetProps {
  callContext: CallContext;
  config?: TesseraWidgetConfig;
  onVerificationComplete?: (result: VerificationResult) => void;
  style?: any;
}

export const SenderVerificationWidget: React.FC<CallVerificationWidgetProps> = ({
  callContext,
  config = {},
  onVerificationComplete,
  style,
}) => {
  const { verificationResult, isLoading, error } = useTesseraVerification(callContext, config);
  const [fadeAnim] = useState(new Animated.Value(0));

  useEffect(() => {
    Animated.timing(fadeAnim, {
      toValue: 1,
      duration: 300,
      useNativeDriver: true,
    }).start();
  }, [fadeAnim]);

  useEffect(() => {
    if (verificationResult && onVerificationComplete) {
      onVerificationComplete(verificationResult);
    }
  }, [verificationResult, onVerificationComplete]);

  const getStatusColor = () => {
    if (error) return '#F44336';
    if (verificationResult?.isVerified) return '#4CAF50';
    if (verificationResult && !verificationResult.isVerified) return '#FF9800';
    return '#9E9E9E';
  };

  const getStatusText = () => {
    if (isLoading) return `Verifying ${getCallTypeDisplayName(callContext.callType)}...`;
    if (error) return 'Verification Error';
    if (verificationResult?.isVerified) return '✓ Verified Call';
    if (verificationResult) return 'Unverified Call';
    return 'Tessera';
  };

  const getSubtext = () => {
    if (isLoading) return 'Tessera Security Check';
    if (error) return error;
    if (verificationResult?.isVerified && verificationResult.callerInfo?.organization) {
      return verificationResult.callerInfo.organization;
    }
    if (verificationResult && !verificationResult.isVerified) {
      return `This ${getCallTypeDisplayName(callContext.callType)} could not be verified`;
    }
    return '';
  };

  return (
    <Animated.View style={[styles.container, { opacity: fadeAnim }, style]}>
      <View style={[styles.card, { borderLeftColor: getStatusColor() }]}>
        <View style={styles.content}>
          <View style={styles.header}>
            {isLoading && <ActivityIndicator size="small" color={getStatusColor()} />}
            <Text style={[styles.statusText, { color: getStatusColor() }]}>
              {getStatusText()}
            </Text>
            {config.showVerificationBadge && verificationResult?.confidence && (
              <View style={[styles.badge, { backgroundColor: getStatusColor() }]}>
                <Text style={styles.badgeText}>{verificationResult.confidence}</Text>
              </View>
            )}
          </View>

          {getSubtext() && (
            <Text style={styles.subtext} numberOfLines={2}>
              {getSubtext()}
            </Text>
          )}

          {config.showTrustScore && verificationResult?.callerInfo?.trustScore && (
            <View style={styles.trustScore}>
              <Text style={styles.trustScoreLabel}>Trust Score:</Text>
              <View style={styles.trustScoreBar}>
                <View
                  style={[
                    styles.trustScoreFill,
                    {
                      width: `${verificationResult.callerInfo.trustScore * 100}%`,
                      backgroundColor: getStatusColor(),
                    },
                  ]}
                />
              </View>
              <Text style={styles.trustScoreText}>
                {Math.round(verificationResult.callerInfo.trustScore * 100)}%
              </Text>
            </View>
          )}

          <Text style={styles.poweredBy}>Tessera Protected</Text>
        </View>
      </View>
    </Animated.View>
  );
};

// Helper function
const getCallTypeDisplayName = (callType: CallType): string => {
  switch (callType) {
    case CallType.VOICE_CALL:
      return 'voice call';
    case CallType.VIDEO_CALL:
      return 'video call';
    case CallType.VOIP_CALL:
      return 'VoIP call';
    case CallType.IN_APP_CALL:
      return 'app call';
    case CallType.CONFERENCE_CALL:
      return 'conference call';
    case CallType.EMERGENCY_CALL:
      return 'emergency call';
    default:
      return 'call';
  }
};

// Styles
const styles = StyleSheet.create({
  container: {
    margin: 8,
  },
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    borderLeftWidth: 4,
    shadowColor: '#000000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 4,
  },
  content: {
    padding: 16,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  statusText: {
    fontSize: 16,
    fontWeight: 'bold',
    marginLeft: 8,
    flex: 1,
  },
  badge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
  },
  badgeText: {
    color: '#FFFFFF',
    fontSize: 10,
    fontWeight: 'bold',
  },
  subtext: {
    fontSize: 12,
    color: '#666666',
    marginBottom: 8,
  },
  trustScore: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  trustScoreLabel: {
    fontSize: 10,
    color: '#666666',
    marginRight: 8,
  },
  trustScoreBar: {
    flex: 1,
    height: 4,
    backgroundColor: '#E0E0E0',
    borderRadius: 2,
    marginRight: 8,
  },
  trustScoreFill: {
    height: '100%',
    borderRadius: 2,
  },
  trustScoreText: {
    fontSize: 10,
    color: '#666666',
  },
  poweredBy: {
    fontSize: 10,
    color: '#999999',
    textAlign: 'right',
  },
});

export default SenderVerificationWidget;
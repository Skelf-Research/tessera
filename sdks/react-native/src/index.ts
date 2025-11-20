import { Linking, Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

// Types
/**
 * CallDNS SDK Configuration
 *
 * Authentication model:
 * - Core nodes: Public, no auth required (anonymous for privacy)
 * - Org nodes: Bank-issued JWT tokens
 */
export interface CallDNSConfig {
  coreNodeUrl?: string;
  orgNodeUrl?: string;
  orgAuthToken?: string; // JWT token for org node authentication
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
  EMAIL = 'EMAIL',
  DOMAIN = 'DOMAIN',
  ENTERPRISE = 'ENTERPRISE',
  CERTIFICATE = 'CERTIFICATE',
}

export interface OutboundCallResult {
  proofId: string;
  broadcast: {
    status: string;
    notified: number;
    timestamp: number;
  };
  dialIntent: string;
  verificationWindow: number;
}

export interface VerifiedCallDestination {
  destinationId: string;
  destinationName: string;
  phoneNumber: string;
  commitment?: string;
}

// CallDNS React Native Client
export class CallDNSClient {
  private static instance: CallDNSClient | null = null;
  private config: Required<CallDNSConfig>;
  private verificationCache: Map<string, VerificationResult> = new Map();

  private constructor(config: CallDNSConfig) {
    this.config = {
      coreNodeUrl: 'https://core.calldns.network',
      orgNodeUrl: '',
      orgAuthToken: '',
      cacheTimeout: 5 * 60 * 1000,
      enableLogging: false,
      maxRetries: 3,
      ...config,
    };
  }

  public static initialize(config: CallDNSConfig): CallDNSClient {
    if (!CallDNSClient.instance) {
      CallDNSClient.instance = new CallDNSClient(config);
    }
    return CallDNSClient.instance;
  }

  public static getInstance(): CallDNSClient {
    if (!CallDNSClient.instance) {
      throw new Error('CallDNSClient not initialized');
    }
    return CallDNSClient.instance;
  }

  // Verify incoming call
  public async verifyIncomingCall(callContext: CallContext): Promise<VerificationResult> {
    try {
      const cacheKey = this.generateCacheKey(callContext);
      const cached = this.verificationCache.get(cacheKey);

      if (cached && Date.now() - cached.timestamp < this.config.cacheTimeout) {
        return cached;
      }

      const response = await this.fetchWithRetry(
        `${this.config.coreNodeUrl}/proofs/${callContext.callerId}`,
        { method: 'GET' }
      );

      let result: VerificationResult;

      if (response.ok) {
        const data = await response.json();
        const proofs = data.proofs || [];

        if (proofs.length > 0) {
          result = {
            isVerified: true,
            callerInfo: this.extractCallerInfo(proofs[0]),
            confidence: VerificationConfidence.HIGH,
            callType: callContext.callType,
            timestamp: Date.now(),
            metadata: proofs[0].metadata,
          };
        } else {
          result = {
            isVerified: false,
            confidence: VerificationConfidence.NONE,
            callType: callContext.callType,
            timestamp: Date.now(),
          };
        }
      } else {
        result = {
          isVerified: false,
          confidence: VerificationConfidence.NONE,
          callType: callContext.callType,
          timestamp: Date.now(),
        };
      }

      this.verificationCache.set(cacheKey, result);
      return result;

    } catch (error) {
      return {
        isVerified: false,
        confidence: VerificationConfidence.NONE,
        callType: callContext.callType,
        timestamp: Date.now(),
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  // Generate proof for outgoing call
  public async generateCallProof(callContext: CallContext): Promise<any> {
    const identity = await this.getOrCreateIdentity();
    const proof = await this.createProof(identity, callContext);

    // Broadcast to network
    const response = await this.fetchWithRetry(
      `${this.config.coreNodeUrl}/proofs/broadcast`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ proof, decoys: 3 }),
      }
    );

    if (!response.ok) {
      throw new Error(`Failed to broadcast proof: ${response.status}`);
    }

    return proof;
  }

  // Prepare verified outbound call
  public async prepareVerifiedCall(
    destination: VerifiedCallDestination,
    metadata?: Record<string, any>
  ): Promise<OutboundCallResult> {
    const callContext: CallContext = {
      callerId: 'customer',
      calleeId: destination.destinationId,
      callType: CallType.VOICE_CALL,
      timestamp: Date.now(),
      metadata: {
        direction: 'outbound',
        destination: destination.destinationId,
        destination_name: destination.destinationName,
        ...metadata,
      },
    };

    const proof = await this.generateCallProof(callContext);

    return {
      proofId: proof.proofId,
      broadcast: {
        status: 'broadcast',
        notified: 0,
        timestamp: Date.now(),
      },
      dialIntent: `tel:${destination.phoneNumber}`,
      verificationWindow: 300,
    };
  }

  // Open phone dialer
  public async openDialer(phoneNumber: string): Promise<void> {
    const url = Platform.OS === 'ios'
      ? `telprompt:${phoneNumber}`
      : `tel:${phoneNumber}`;

    const canOpen = await Linking.canOpenURL(url);
    if (canOpen) {
      await Linking.openURL(url);
    } else {
      throw new Error('Cannot open phone dialer');
    }
  }

  // Register commitment with org node
  public async registerCommitment(
    customerId: string,
    commitment: string,
    deviceId?: string,
    metadata?: Record<string, any>
  ): Promise<any> {
    if (!this.config.orgNodeUrl) {
      throw new Error('orgNodeUrl not configured');
    }

    const response = await this.fetchWithRetry(
      `${this.config.orgNodeUrl}/customers/register`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          customer_id: customerId,
          commitment,
          device_id: deviceId,
          metadata,
        }),
      },
      true // Use org auth
    );

    return response.json();
  }

  // Helper methods
  private async getOrCreateIdentity(): Promise<any> {
    const storageKey = 'calldns_identity';

    try {
      const stored = await AsyncStorage.getItem(storageKey);
      if (stored) {
        return JSON.parse(stored);
      }

      const identity = {
        privateKey: this.generateRandomHex(64),
        publicKey: this.generateRandomHex(128),
        created: Date.now(),
      };

      await AsyncStorage.setItem(storageKey, JSON.stringify(identity));
      return identity;
    } catch (error) {
      throw new Error('Failed to get or create identity');
    }
  }

  private async createProof(identity: any, callContext: CallContext): Promise<any> {
    const timestamp = callContext.timestamp || Date.now();

    return {
      proofId: this.generateRandomHex(32),
      publicKey: identity.publicKey,
      signature: this.generateRandomHex(128),
      commitment: this.generateRandomHex(64),
      callContext,
      timestamp,
      metadata: callContext.metadata,
    };
  }

  private extractCallerInfo(proof: any): CallerInfo | undefined {
    if (!proof.metadata) return undefined;

    return {
      displayName: proof.metadata.displayName,
      organization: proof.metadata.organization,
      verified: true,
      trustScore: this.calculateTrustScore(proof),
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

  private generateRandomHex(length: number): string {
    const chars = '0123456789abcdef';
    let result = '';
    for (let i = 0; i < length; i++) {
      result += chars[Math.floor(Math.random() * chars.length)];
    }
    return result;
  }

  private async fetchWithRetry(url: string, options: RequestInit, useOrgAuth: boolean = false): Promise<Response> {
    let lastError: Error | null = null;

    for (let i = 0; i < this.config.maxRetries; i++) {
      try {
        const response = await fetch(url, {
          ...options,
          headers: {
            ...options.headers,
            // Only add auth for org node requests
            ...(useOrgAuth && this.config.orgAuthToken && { Authorization: `Bearer ${this.config.orgAuthToken}` }),
          },
        });

        if (response.ok || response.status < 500) {
          return response;
        }
        throw new Error(`HTTP ${response.status}`);
      } catch (error) {
        lastError = error as Error;
        if (i < this.config.maxRetries - 1) {
          await new Promise(resolve => setTimeout(resolve, Math.pow(2, i) * 1000));
        }
      }
    }

    throw lastError || new Error('Max retries exceeded');
  }

  public clearCache(): void {
    this.verificationCache.clear();
  }

  public getStats(): any {
    const total = this.verificationCache.size;
    const successful = Array.from(this.verificationCache.values())
      .filter(r => r.isVerified).length;

    return {
      totalVerifications: total,
      successfulVerifications: successful,
      successRate: total > 0 ? successful / total : 0,
      cacheSize: total,
    };
  }
}

export default CallDNSClient;

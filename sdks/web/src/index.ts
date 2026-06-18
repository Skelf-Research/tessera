import CryptoJS from 'crypto-js';

// Types
/**
 * Tessera SDK Configuration
 *
 * Authentication model:
 * - Core nodes: Public, no auth required (anonymous for privacy)
 * - Org nodes: Bank-issued JWT tokens
 */
export interface TesseraConfig {
  coreNodeUrl?: string;
  orgNodeUrl?: string; // Bank's org node for registration
  orgAuthToken?: string; // JWT token for org node authentication
  cacheTimeout?: number;
  enableLogging?: boolean;
  maxRetries?: number;
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

export enum CallType {
  VOICE_CALL = 'VOICE_CALL',
  VIDEO_CALL = 'VIDEO_CALL',
  VOIP_CALL = 'VOIP_CALL',
  WEBRTC_CALL = 'WEBRTC_CALL',
  IN_APP_CALL = 'IN_APP_CALL',
  CONFERENCE_CALL = 'CONFERENCE_CALL',
  SCREEN_SHARE = 'SCREEN_SHARE',
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
  webrtcInfo?: WebRTCInfo;
}

export interface NetworkInfo {
  ipAddress?: string;
  userAgent?: string;
  platform: string;
  browser?: string;
  browserVersion?: string;
}

export interface WebRTCInfo {
  localSDP?: string;
  remoteSDP?: string;
  iceServers?: RTCIceServer[];
  mediaConstraints?: MediaStreamConstraints;
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
  domain?: string;
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

export interface TesseraWidgetConfig {
  showTrustScore?: boolean;
  showOrganization?: boolean;
  showVerificationBadge?: boolean;
  autoVerify?: boolean;
  theme?: 'light' | 'dark' | 'auto';
  position?: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right' | 'center';
  size?: 'small' | 'medium' | 'large';
  customStyles?: Partial<CSSStyleDeclaration>;
}

// Events
export type TesseraEventType =
  | 'verification-started'
  | 'verification-completed'
  | 'verification-failed'
  | 'proof-generated'
  | 'cache-updated';

export interface TesseraEvent {
  type: TesseraEventType;
  data: any;
  timestamp: number;
}

// Tessera Web Client
export class TesseraClient {
  private static instance: TesseraClient | null = null;
  private config: Required<TesseraConfig>;
  private verificationCache: Map<string, VerificationResult> = new Map();
  private eventListeners: Map<TesseraEventType, Function[]> = new Map();

  private constructor(config: TesseraConfig) {
    this.config = {
      coreNodeUrl: 'https://core.tessera.network',
      orgNodeUrl: undefined,
      orgAuthToken: undefined,
      cacheTimeout: 5 * 60 * 1000, // 5 minutes
      enableLogging: false,
      maxRetries: 3,
      ...config,
    };

    // Initialize WebRTC detection
    this.setupWebRTCDetection();
  }

  // Prepare and broadcast an outbound verified call
  public async prepareVerifiedCall(
    destination: VerifiedCallDestination,
    metadata?: Record<string, any>
  ): Promise<OutboundCallResult> {
    try {
      const identity = await this.getOrCreateIdentity();

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

      const proof = await this.createProof(identity, callContext);

      // Broadcast to core network (no auth - public endpoint)
      const response = await this.fetchWithRetry(
        `${this.config.coreNodeUrl}/proofs/broadcast`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            proof: {
              ...proof,
              commitment_id: destination.commitment,
            },
            decoys: 3,
          }),
        }
      );

      const broadcastResult = await response.json();

      this.emit('proof-generated', proof);

      return {
        proofId: proof.proofId,
        broadcast: {
          status: broadcastResult.status || 'broadcast',
          notified: broadcastResult.notified || 0,
          timestamp: Date.now(),
        },
        dialIntent: `tel:${destination.phoneNumber}`,
        verificationWindow: 300,
      };

    } catch (error) {
      this.log('Error preparing verified call:', error);
      throw error;
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
        headers: {
          'Content-Type': 'application/json',
          ...(this.config.orgAuthToken && { Authorization: `Bearer ${this.config.orgAuthToken}` }),
        },
        body: JSON.stringify({
          customer_id: customerId,
          commitment,
          device_id: deviceId,
          metadata,
        }),
      }
    );

    return response.json();
  }

  public static initialize(config: TesseraConfig): TesseraClient {
    if (!TesseraClient.instance) {
      TesseraClient.instance = new TesseraClient(config);
    }
    return TesseraClient.instance;
  }

  public static getInstance(): TesseraClient {
    if (!TesseraClient.instance) {
      throw new Error('TesseraClient not initialized. Call TesseraClient.initialize() first.');
    }
    return TesseraClient.instance;
  }

  // Event handling
  public on(event: TesseraEventType, callback: (data: any) => void): void {
    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, []);
    }
    this.eventListeners.get(event)!.push(callback);
  }

  public off(event: TesseraEventType, callback: (data: any) => void): void {
    const listeners = this.eventListeners.get(event);
    if (listeners) {
      const index = listeners.indexOf(callback);
      if (index > -1) {
        listeners.splice(index, 1);
      }
    }
  }

  private emit(event: TesseraEventType, data: any): void {
    const listeners = this.eventListeners.get(event);
    if (listeners) {
      listeners.forEach(callback => callback(data));
    }
  }

  // Main verification method
  public async verifyIncomingCall(callContext: CallContext): Promise<VerificationResult> {
    this.emit('verification-started', callContext);

    try {
      const cacheKey = this.generateCacheKey(callContext);

      // Check cache first
      const cached = this.verificationCache.get(cacheKey);
      if (cached && Date.now() - cached.timestamp < this.config.cacheTimeout) {
        this.log('Using cached verification result');
        return cached;
      }

      // Enhance call context with browser info
      const enhancedContext = await this.enhanceCallContext(callContext);

      // Look up proof from network
      const response = await this.fetchWithRetry(
        `${this.config.baseUrl}/api/lookup-proof?` +
          new URLSearchParams({
            callerId: enhancedContext.callerId,
            callType: enhancedContext.callType,
            timestamp: (enhancedContext.timestamp || Date.now()).toString(),
          }),
        {
          headers: {
            'Content-Type': 'application/json',
            ...(this.config.apiKey && { Authorization: `Bearer ${this.config.apiKey}` }),
          },
        }
      );

      let result: VerificationResult;

      if (response.ok) {
        const proof = await response.json();
        const isValid = await this.verifyProof(proof, enhancedContext);

        result = {
          isVerified: isValid,
          callerInfo: isValid ? this.extractCallerInfo(proof) : undefined,
          confidence: isValid ? VerificationConfidence.HIGH : VerificationConfidence.NONE,
          callType: enhancedContext.callType,
          timestamp: Date.now(),
          metadata: proof.metadata,
        };
      } else {
        result = {
          isVerified: false,
          callerInfo: undefined,
          confidence: VerificationConfidence.NONE,
          callType: enhancedContext.callType,
          timestamp: Date.now(),
        };
      }

      // Cache result
      this.verificationCache.set(cacheKey, result);
      this.emit('cache-updated', this.verificationCache.size);
      this.emit('verification-completed', result);

      this.log('Verification complete:', result.isVerified);
      return result;

    } catch (error) {
      const errorResult: VerificationResult = {
        isVerified: false,
        callerInfo: undefined,
        confidence: VerificationConfidence.NONE,
        callType: callContext.callType,
        timestamp: Date.now(),
        error: error instanceof Error ? error.message : 'Unknown error',
      };

      this.emit('verification-failed', error);
      this.log('Error verifying call:', error);
      return errorResult;
    }
  }

  // Generate proof for outgoing calls
  public async generateCallProof(callContext: CallContext): Promise<any> {
    try {
      const identity = await this.getOrCreateIdentity();
      const enhancedContext = await this.enhanceCallContext(callContext);
      const proof = await this.createProof(identity, enhancedContext);

      // Register with network
      const response = await this.fetchWithRetry(`${this.config.baseUrl}/api/register-proof`, {
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

      this.emit('proof-generated', proof);
      this.log('Proof generated and registered');
      return proof;

    } catch (error) {
      this.log('Error generating proof:', error);
      throw error;
    }
  }

  // WebRTC integration
  private setupWebRTCDetection(): void {
    if (typeof window !== 'undefined' && window.RTCPeerConnection) {
      // Monitor WebRTC connections
      const originalSetLocalDescription = RTCPeerConnection.prototype.setLocalDescription;
      const originalSetRemoteDescription = RTCPeerConnection.prototype.setRemoteDescription;

      RTCPeerConnection.prototype.setLocalDescription = function(description) {
        TesseraClient.getInstance()?.handleWebRTCEvent('local-description', description);
        return originalSetLocalDescription.call(this, description);
      };

      RTCPeerConnection.prototype.setRemoteDescription = function(description) {
        TesseraClient.getInstance()?.handleWebRTCEvent('remote-description', description);
        return originalSetRemoteDescription.call(this, description);
      };
    }
  }

  private handleWebRTCEvent(type: string, description: RTCSessionDescriptionInit): void {
    this.log('WebRTC event:', type, description.type);
    // Could trigger automatic verification based on WebRTC events
  }

  // Helper methods
  private async enhanceCallContext(callContext: CallContext): Promise<CallContext> {
    const networkInfo: NetworkInfo = {
      platform: 'web',
      userAgent: navigator.userAgent,
      browser: this.detectBrowser(),
      browserVersion: this.detectBrowserVersion(),
    };

    return {
      ...callContext,
      networkInfo: { ...callContext.networkInfo, ...networkInfo },
      timestamp: callContext.timestamp || Date.now(),
      sessionId: callContext.sessionId || this.generateSessionId(),
    };
  }

  private detectBrowser(): string {
    const userAgent = navigator.userAgent;
    if (userAgent.includes('Chrome')) return 'Chrome';
    if (userAgent.includes('Firefox')) return 'Firefox';
    if (userAgent.includes('Safari')) return 'Safari';
    if (userAgent.includes('Edge')) return 'Edge';
    return 'Unknown';
  }

  private detectBrowserVersion(): string {
    const userAgent = navigator.userAgent;
    const match = userAgent.match(/(Chrome|Firefox|Safari|Edge)\/(\d+)/);
    return match ? match[2] : 'Unknown';
  }

  private generateSessionId(): string {
    return CryptoJS.lib.WordArray.random(16).toString();
  }

  private async getOrCreateIdentity(): Promise<any> {
    const storageKey = 'tessera_identity';

    try {
      const stored = localStorage.getItem(storageKey);
      if (stored) {
        return JSON.parse(stored);
      }

      // Generate new identity
      const identity = {
        privateKey: CryptoJS.lib.WordArray.random(32).toString(),
        publicKey: CryptoJS.lib.WordArray.random(64).toString(),
        created: Date.now(),
      };

      localStorage.setItem(storageKey, JSON.stringify(identity));
      return identity;
    } catch (error) {
      throw new Error('Failed to get or create identity');
    }
  }

  private async createProof(identity: any, callContext: CallContext): Promise<any> {
    const message = JSON.stringify({
      callerId: callContext.callerId,
      callType: callContext.callType,
      timestamp: callContext.timestamp,
      networkInfo: callContext.networkInfo,
    });

    const signature = CryptoJS.HmacSHA256(message, identity.privateKey).toString();

    return {
      proofId: CryptoJS.lib.WordArray.random(16).toString(),
      publicKey: identity.publicKey,
      signature,
      commitment: CryptoJS.SHA256(message).toString(),
      callContext,
      timestamp: Date.now(),
      metadata: callContext.metadata,
    };
  }

  private async verifyProof(proof: any, callContext: CallContext): Promise<boolean> {
    try {
      const message = JSON.stringify({
        callerId: callContext.callerId,
        callType: callContext.callType,
        timestamp: callContext.timestamp,
        networkInfo: callContext.networkInfo,
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
      domain: proof.metadata.domain,
      verified: true,
      trustScore: this.calculateTrustScore(proof),
      verificationLevel: this.determineVerificationLevel(proof),
      profileImage: proof.metadata.profileImage,
    };
  }

  private calculateTrustScore(proof: any): number {
    let score = 0.5;

    if (proof.metadata?.organization) score += 0.2;
    if (proof.metadata?.verified_domain) score += 0.2;
    if (proof.metadata?.ssl_certificate) score += 0.1;

    return Math.min(1.0, score);
  }

  private determineVerificationLevel(proof: any): VerificationLevel {
    if (proof.metadata?.ssl_certificate) return VerificationLevel.CERTIFICATE;
    if (proof.metadata?.verified_domain) return VerificationLevel.DOMAIN;
    if (proof.metadata?.organization) return VerificationLevel.ENTERPRISE;
    return VerificationLevel.BASIC;
  }

  private generateCacheKey(callContext: CallContext): string {
    return `${callContext.callerId}_${callContext.callType}_${callContext.sessionId || 'unknown'}`;
  }

  private async fetchWithRetry(url: string, options: RequestInit): Promise<Response> {
    let lastError: Error | null = null;

    for (let i = 0; i < this.config.maxRetries; i++) {
      try {
        const response = await fetch(url, options);
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

  private log(...args: any[]): void {
    if (this.config.enableLogging) {
      console.log('[Tessera]', ...args);
    }
  }

  // Utility methods
  public clearCache(): void {
    this.verificationCache.clear();
    this.emit('cache-updated', 0);
  }

  public getStats(): any {
    const totalVerifications = this.verificationCache.size;
    const successfulVerifications = Array.from(this.verificationCache.values())
      .filter(result => result.isVerified).length;

    return {
      totalVerifications,
      successfulVerifications,
      successRate: totalVerifications > 0 ? successfulVerifications / totalVerifications : 0,
      cacheSize: totalVerifications,
    };
  }
}

// Default export
export default TesseraClient;
import { useState, useEffect, useCallback } from 'react';
import { CallDNSClient, CallContext, VerificationResult, CallDNSWidgetConfig } from './index';

// React Hook for CallDNS verification
export function useCallDNSVerification(
  callContext: CallContext | null,
  config?: CallDNSWidgetConfig
) {
  const [verificationResult, setVerificationResult] = useState<VerificationResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const verifyCall = useCallback(async (context: CallContext) => {
    if (!context) return;

    setIsLoading(true);
    setError(null);

    try {
      const client = CallDNSClient.getInstance();
      const result = await client.verifyIncomingCall(context);
      setVerificationResult(result);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      setVerificationResult({
        isVerified: false,
        confidence: 'NONE' as any,
        callType: context.callType,
        timestamp: Date.now(),
        error: errorMessage
      });
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (callContext && config?.autoVerify !== false) {
      verifyCall(callContext);
    }
  }, [callContext, config?.autoVerify, verifyCall]);

  const retry = useCallback(() => {
    if (callContext) {
      verifyCall(callContext);
    }
  }, [callContext, verifyCall]);

  return {
    verificationResult,
    isLoading,
    error,
    retry,
    verifyCall
  };
}

// React Hook for CallDNS statistics
export function useCallDNSStats() {
  const [stats, setStats] = useState<any>(null);

  const refreshStats = useCallback(() => {
    try {
      const client = CallDNSClient.getInstance();
      const currentStats = client.getStats();
      setStats(currentStats);
    } catch (error) {
      console.warn('Failed to get CallDNS stats:', error);
    }
  }, []);

  useEffect(() => {
    refreshStats();

    try {
      const client = CallDNSClient.getInstance();

      const handleCacheUpdate = () => {
        refreshStats();
      };

      client.on('cache-updated', handleCacheUpdate);
      client.on('verification-completed', handleCacheUpdate);

      return () => {
        client.off('cache-updated', handleCacheUpdate);
        client.off('verification-completed', handleCacheUpdate);
      };
    } catch (error) {
      console.warn('Failed to set up CallDNS event listeners:', error);
    }
  }, [refreshStats]);

  return {
    stats,
    refresh: refreshStats
  };
}

// React Hook for proof generation
export function useCallDNSProofGeneration() {
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generateProof = useCallback(async (callContext: CallContext) => {
    setIsGenerating(true);
    setError(null);

    try {
      const client = CallDNSClient.getInstance();
      const proof = await client.generateCallProof(callContext);
      return proof;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      throw err;
    } finally {
      setIsGenerating(false);
    }
  }, []);

  return {
    generateProof,
    isGenerating,
    error
  };
}
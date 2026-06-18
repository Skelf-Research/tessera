import { useState, useEffect, useCallback } from 'react';
import { TesseraClient, CallContext, VerificationResult, TesseraWidgetConfig } from './index';

// React Hook for Tessera verification
export function useTesseraVerification(
  callContext: CallContext | null,
  config?: TesseraWidgetConfig
) {
  const [verificationResult, setVerificationResult] = useState<VerificationResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const verifyCall = useCallback(async (context: CallContext) => {
    if (!context) return;

    setIsLoading(true);
    setError(null);

    try {
      const client = TesseraClient.getInstance();
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

// React Hook for Tessera statistics
export function useTesseraStats() {
  const [stats, setStats] = useState<any>(null);

  const refreshStats = useCallback(() => {
    try {
      const client = TesseraClient.getInstance();
      const currentStats = client.getStats();
      setStats(currentStats);
    } catch (error) {
      console.warn('Failed to get Tessera stats:', error);
    }
  }, []);

  useEffect(() => {
    refreshStats();

    try {
      const client = TesseraClient.getInstance();

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
      console.warn('Failed to set up Tessera event listeners:', error);
    }
  }, [refreshStats]);

  return {
    stats,
    refresh: refreshStats
  };
}

// React Hook for proof generation
export function useTesseraProofGeneration() {
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generateProof = useCallback(async (callContext: CallContext) => {
    setIsGenerating(true);
    setError(null);

    try {
      const client = TesseraClient.getInstance();
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
package com.calldns.sdk

import android.content.Context
import android.util.Log
import kotlinx.coroutines.*
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.security.SecureRandom
import java.util.concurrent.ConcurrentHashMap

/**
 * CallDNS Android SDK
 *
 * Provides zero-knowledge proof verification for incoming calls of any type:
 * - Traditional phone calls
 * - VoIP calls (WhatsApp, Telegram, etc.)
 * - In-app calls
 * - Video calls
 * - Conference calls
 */
class CallDNSClient private constructor(
    private val context: Context,
    private val config: CallDNSConfig
) {
    companion object {
        private const val TAG = "CallDNSClient"
        private var instance: CallDNSClient? = null

        fun initialize(context: Context, config: CallDNSConfig): CallDNSClient {
            return instance ?: synchronized(this) {
                instance ?: CallDNSClient(context.applicationContext, config).also { instance = it }
            }
        }

        fun getInstance(): CallDNSClient {
            return instance ?: throw IllegalStateException("CallDNSClient not initialized")
        }
    }

    private val apiService: CallDNSApiService
    private val cryptoManager: CryptoManager
    private val keyManager: KeyManager
    private val verificationCache = ConcurrentHashMap<String, VerificationResult>()
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    init {
        // Initialize API service
        val retrofit = Retrofit.Builder()
            .baseUrl(config.baseUrl)
            .addConverterFactory(GsonConverterFactory.create())
            .build()

        apiService = retrofit.create(CallDNSApiService::class.java)
        cryptoManager = CryptoManager()
        keyManager = KeyManager(context)

        Log.d(TAG, "CallDNS SDK initialized")
    }

    /**
     * Generate a proof for an outgoing call
     */
    suspend fun generateCallProof(callContext: CallContext): Result<CallProof> {
        return withContext(Dispatchers.IO) {
            try {
                val identity = keyManager.getOrCreateIdentity()
                val proof = cryptoManager.generateProof(identity, callContext)

                // Register proof with network
                val response = apiService.registerProof(proof)
                if (response.isSuccessful) {
                    Log.d(TAG, "Proof generated and registered for ${callContext.callType}")
                    Result.success(proof)
                } else {
                    Result.failure(CallDNSException("Failed to register proof: ${response.code()}"))
                }
            } catch (e: Exception) {
                Log.e(TAG, "Error generating proof", e)
                Result.failure(e)
            }
        }
    }

    /**
     * Verify an incoming call
     */
    suspend fun verifyIncomingCall(
        callContext: CallContext,
        callback: ((VerificationResult) -> Unit)? = null
    ): VerificationResult {
        return withContext(Dispatchers.IO) {
            try {
                val cacheKey = generateCacheKey(callContext)

                // Check cache first
                verificationCache[cacheKey]?.let { cached ->
                    if (System.currentTimeMillis() - cached.timestamp < config.cacheTimeout) {
                        callback?.invoke(cached)
                        return@withContext cached
                    }
                }

                // Look up proof from network
                val response = apiService.lookupProof(
                    callerId = callContext.callerId,
                    callType = callContext.callType.name,
                    timestamp = System.currentTimeMillis()
                )

                val result = if (response.isSuccessful && response.body() != null) {
                    val proof = response.body()!!
                    val isValid = cryptoManager.verifyProof(proof, callContext)

                    VerificationResult(
                        isVerified = isValid,
                        callerInfo = if (isValid) extractCallerInfo(proof) else null,
                        confidence = if (isValid) VerificationConfidence.HIGH else VerificationConfidence.NONE,
                        callType = callContext.callType,
                        timestamp = System.currentTimeMillis(),
                        metadata = proof.metadata
                    )
                } else {
                    VerificationResult(
                        isVerified = false,
                        callerInfo = null,
                        confidence = VerificationConfidence.NONE,
                        callType = callContext.callType,
                        timestamp = System.currentTimeMillis()
                    )
                }

                // Cache result
                verificationCache[cacheKey] = result

                callback?.invoke(result)
                Log.d(TAG, "Verification complete: ${result.isVerified}")
                result

            } catch (e: Exception) {
                Log.e(TAG, "Error verifying call", e)
                val errorResult = VerificationResult(
                    isVerified = false,
                    callerInfo = null,
                    confidence = VerificationConfidence.NONE,
                    callType = callContext.callType,
                    timestamp = System.currentTimeMillis(),
                    error = e.message
                )
                callback?.invoke(errorResult)
                errorResult
            }
        }
    }

    /**
     * Register identity for verification
     */
    suspend fun registerIdentity(identityInfo: IdentityInfo): Result<Boolean> {
        return withContext(Dispatchers.IO) {
            try {
                val identity = keyManager.createIdentity(identityInfo)
                val response = apiService.registerIdentity(identity)

                if (response.isSuccessful) {
                    Log.d(TAG, "Identity registered successfully")
                    Result.success(true)
                } else {
                    Result.failure(CallDNSException("Failed to register identity: ${response.code()}"))
                }
            } catch (e: Exception) {
                Log.e(TAG, "Error registering identity", e)
                Result.failure(e)
            }
        }
    }

    /**
     * Get verification statistics
     */
    fun getVerificationStats(): VerificationStats {
        val totalVerifications = verificationCache.size
        val successfulVerifications = verificationCache.values.count { it.isVerified }

        return VerificationStats(
            totalVerifications = totalVerifications,
            successfulVerifications = successfulVerifications,
            successRate = if (totalVerifications > 0) {
                successfulVerifications.toFloat() / totalVerifications
            } else 0f,
            cacheSize = verificationCache.size
        )
    }

    /**
     * Clear verification cache
     */
    fun clearCache() {
        verificationCache.clear()
        Log.d(TAG, "Verification cache cleared")
    }

    private fun generateCacheKey(callContext: CallContext): String {
        return "${callContext.callerId}_${callContext.callType.name}_${callContext.sessionId}"
    }

    private fun extractCallerInfo(proof: CallProof): CallerInfo? {
        return proof.metadata?.let { metadata ->
            CallerInfo(
                displayName = metadata["displayName"] as? String,
                organization = metadata["organization"] as? String,
                verified = true,
                trustScore = calculateTrustScore(proof)
            )
        }
    }

    private fun calculateTrustScore(proof: CallProof): Float {
        // Calculate trust score based on proof strength, recency, etc.
        var score = 0.5f

        if (proof.metadata?.contains("organization") == true) score += 0.2f
        if (proof.metadata?.contains("verified_domain") == true) score += 0.3f

        return minOf(1.0f, score)
    }

    fun destroy() {
        scope.cancel()
        verificationCache.clear()
        instance = null
        Log.d(TAG, "CallDNS SDK destroyed")
    }
}
package com.calldns.sdk

import retrofit2.Response
import retrofit2.http.*

/**
 * Retrofit API service for CallDNS network communication
 */
interface CallDNSApiService {

    // Core node endpoints (proof routing)

    @POST("proofs/broadcast")
    suspend fun broadcastProof(
        @Body proof: ProofBroadcastRequest
    ): Response<ProofBroadcastResponse>

    @POST("subscriptions/{subscriberId}")
    suspend fun registerSubscription(
        @Path("subscriberId") subscriberId: String,
        @Body subscription: SubscriptionRequest
    ): Response<SubscriptionResponse>

    @GET("proofs/{subscriberId}")
    suspend fun getPendingProofs(
        @Path("subscriberId") subscriberId: String
    ): Response<PendingProofsResponse>

    @GET("health")
    suspend fun healthCheck(): Response<HealthResponse>

    // Org node endpoints (registration & verification)

    @POST("customers/register")
    suspend fun registerCommitment(
        @Body registration: CommitmentRegistration
    ): Response<CommitmentRegistrationResponse>

    @GET("customers/{customerId}/commitments")
    suspend fun getCustomerCommitments(
        @Path("customerId") customerId: String
    ): Response<CustomerCommitmentsResponse>

    @POST("customers/{customerId}/broadcast")
    suspend fun broadcastToCustomer(
        @Path("customerId") customerId: String,
        @Body proof: ProofBroadcastRequest
    ): Response<CustomerBroadcastResponse>

    // Legacy endpoints for backward compatibility

    @POST("api/register-proof")
    suspend fun registerProof(
        @Body proof: CallProof
    ): Response<Unit>

    @GET("api/lookup-proof")
    suspend fun lookupProof(
        @Query("callerId") callerId: String,
        @Query("callType") callType: String,
        @Query("timestamp") timestamp: Long
    ): Response<CallProof>

    @POST("api/register-identity")
    suspend fun registerIdentity(
        @Body identity: Any
    ): Response<Unit>
}

// Request/Response models

data class ProofBroadcastRequest(
    val proof: Map<String, Any>,
    val decoys: Int = 3
)

data class ProofBroadcastResponse(
    val status: String,
    val notified: Int,
    val push: Map<String, Any>? = null,
    val timestamp: Long
)

data class SubscriptionRequest(
    val bucket: Int,
    val bloomFilter: String,
    val orgHints: List<String>? = null,
    val timeWindow: Int = 600
)

data class SubscriptionResponse(
    val status: String,
    val subscriberId: String,
    val bucket: Int
)

data class PendingProofsResponse(
    val subscriberId: String,
    val proofs: List<Map<String, Any>>,
    val count: Int
)

data class HealthResponse(
    val status: String,
    val nodeId: String,
    val nodeType: String,
    val timestamp: Long,
    val stats: Map<String, Any>
)

data class CommitmentRegistration(
    val customerId: String,
    val commitment: String,
    val deviceId: String? = null,
    val metadata: Map<String, Any>? = null
)

data class CommitmentRegistrationResponse(
    val status: String,
    val customerId: String,
    val commitment: String,
    val deviceId: String?,
    val registeredAt: Long,
    val totalDevices: Int
)

data class CustomerCommitmentsResponse(
    val customerId: String,
    val commitments: List<String>,
    val devices: List<DeviceCommitment>
)

data class DeviceCommitment(
    val commitment: String,
    val deviceId: String?,
    val registeredAt: Long,
    val metadata: Map<String, Any>?
)

data class CustomerBroadcastResponse(
    val status: String,
    val customerId: String,
    val devices: Int,
    val results: List<DeviceBroadcastResult>
)

data class DeviceBroadcastResult(
    val deviceId: String?,
    val commitment: String,
    val notified: Int,
    val push: Map<String, Any>?
)

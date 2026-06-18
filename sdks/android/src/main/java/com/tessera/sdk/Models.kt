package com.calldns.sdk

import java.util.*

/**
 * Configuration for CallDNS SDK
 *
 * Authentication model:
 * - Core nodes: Public, no auth (anonymous for privacy)
 * - Org nodes: Bank-issued JWT tokens
 */
data class CallDNSConfig(
    val coreNodeUrl: String = "https://core.calldns.network",
    val orgNodeUrl: String? = null, // Bank's org node for registration
    val orgAuthToken: String? = null, // JWT token for org node authentication
    val cacheTimeout: Long = 5 * 60 * 1000, // 5 minutes
    val enableLogging: Boolean = false,
    val maxRetries: Int = 3
)

/**
 * Result of broadcasting an outbound call proof
 */
data class OutboundCallResult(
    val proofId: String,
    val broadcast: BroadcastStatus,
    val dialIntent: String,
    val verificationWindow: Int = 300 // 5 minutes
)

/**
 * Status of proof broadcast
 */
data class BroadcastStatus(
    val status: String,
    val notified: Int,
    val timestamp: Long
)

/**
 * Destination info for outbound verified calls
 */
data class VerifiedCallDestination(
    val destinationId: String,
    val destinationName: String,
    val phoneNumber: String,
    val commitment: String? = null
)

/**
 * Represents different types of calls that can be verified
 */
enum class CallType {
    VOICE_CALL,      // Traditional phone call
    VIDEO_CALL,      // Video call
    VOIP_CALL,       // VoIP call (WhatsApp, Telegram, etc.)
    IN_APP_CALL,     // In-app communication
    CONFERENCE_CALL, // Conference/group call
    EMERGENCY_CALL,  // Emergency services
    UNKNOWN
}

/**
 * Context information about a call
 */
data class CallContext(
    val callerId: String,
    val calleeId: String? = null,
    val callType: CallType,
    val sessionId: String = UUID.randomUUID().toString(),
    val timestamp: Long = System.currentTimeMillis(),
    val metadata: Map<String, Any> = emptyMap(),
    val appContext: String? = null, // App identifier for in-app calls
    val networkInfo: NetworkInfo? = null
)

/**
 * Network information for the call
 */
data class NetworkInfo(
    val ipAddress: String? = null,
    val userAgent: String? = null,
    val platform: String = "android"
)

/**
 * Zero-knowledge proof for call verification
 */
data class CallProof(
    val proofId: String,
    val publicKey: String,
    val signature: String,
    val commitment: String,
    val callContext: CallContext,
    val timestamp: Long,
    val metadata: Map<String, Any>? = null
)

/**
 * Identity information for registration
 */
data class IdentityInfo(
    val userId: String,
    val displayName: String? = null,
    val phoneNumber: String? = null,
    val email: String? = null,
    val organization: String? = null,
    val verificationLevel: VerificationLevel = VerificationLevel.BASIC
)

/**
 * Verification levels for identity
 */
enum class VerificationLevel {
    BASIC,      // Basic verification
    PHONE,      // Phone number verified
    EMAIL,      // Email verified
    DOCUMENT,   // Document verified
    ENTERPRISE  // Enterprise/organization verified
}

/**
 * Result of call verification
 */
data class VerificationResult(
    val isVerified: Boolean,
    val callerInfo: CallerInfo?,
    val confidence: VerificationConfidence,
    val callType: CallType,
    val timestamp: Long,
    val metadata: Map<String, Any>? = null,
    val error: String? = null
)

/**
 * Information about the caller
 */
data class CallerInfo(
    val displayName: String?,
    val organization: String?,
    val verified: Boolean,
    val trustScore: Float, // 0.0 to 1.0
    val verificationLevel: VerificationLevel? = null,
    val profileImage: String? = null
)

/**
 * Confidence level of verification
 */
enum class VerificationConfidence {
    NONE,      // No verification
    LOW,       // Some indicators present
    MEDIUM,    // Good verification
    HIGH,      // Strong verification
    ABSOLUTE   // Cryptographically verified
}

/**
 * Statistics about verifications
 */
data class VerificationStats(
    val totalVerifications: Int,
    val successfulVerifications: Int,
    val successRate: Float,
    val cacheSize: Int
)

/**
 * CallDNS specific exceptions
 */
class CallDNSException(message: String, cause: Throwable? = null) : Exception(message, cause)

/**
 * Widget configuration for UI components
 */
data class CallDNSWidgetConfig(
    val showTrustScore: Boolean = true,
    val showOrganization: Boolean = true,
    val showVerificationBadge: Boolean = true,
    val autoVerify: Boolean = true,
    val theme: CallDNSTheme = CallDNSTheme.AUTO,
    val position: WidgetPosition = WidgetPosition.TOP_RIGHT,
    val size: WidgetSize = WidgetSize.MEDIUM
)

/**
 * UI theme options
 */
enum class CallDNSTheme {
    LIGHT,
    DARK,
    AUTO
}

/**
 * Widget positioning
 */
enum class WidgetPosition {
    TOP_LEFT,
    TOP_RIGHT,
    BOTTOM_LEFT,
    BOTTOM_RIGHT,
    CENTER,
    FLOATING
}

/**
 * Widget size options
 */
enum class WidgetSize {
    SMALL,
    MEDIUM,
    LARGE,
    FULL_WIDTH
}

/**
 * Events that can be emitted by the SDK
 */
sealed class CallDNSEvent {
    data class VerificationStarted(val callContext: CallContext) : CallDNSEvent()
    data class VerificationCompleted(val result: VerificationResult) : CallDNSEvent()
    data class VerificationFailed(val error: String) : CallDNSEvent()
    data class ProofGenerated(val proof: CallProof) : CallDNSEvent()
    data class CacheUpdated(val cacheSize: Int) : CallDNSEvent()
}
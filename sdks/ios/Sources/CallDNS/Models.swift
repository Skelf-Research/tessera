import Foundation

// MARK: - Call Types
@objc public enum CallType: Int, CaseIterable {
    case voiceCall = 0
    case videoCall = 1
    case voipCall = 2
    case webrtcCall = 3
    case inAppCall = 4
    case conferenceCall = 5
    case emergencyCall = 6
    case screenShare = 7
    case unknown = 99

    public var displayName: String {
        switch self {
        case .voiceCall: return "Voice Call"
        case .videoCall: return "Video Call"
        case .voipCall: return "VoIP Call"
        case .webrtcCall: return "WebRTC Call"
        case .inAppCall: return "In-App Call"
        case .conferenceCall: return "Conference Call"
        case .emergencyCall: return "Emergency Call"
        case .screenShare: return "Screen Share"
        case .unknown: return "Unknown"
        }
    }
}

// MARK: - Call Context
@objc public class CallContext: NSObject {
    @objc public let callerId: String
    @objc public let calleeId: String?
    @objc public let callType: CallType
    @objc public let sessionId: String?
    @objc public let timestamp: Date
    @objc public let metadata: [String: Any]?
    @objc public let appContext: String?

    @objc public init(
        callerId: String,
        calleeId: String? = nil,
        callType: CallType,
        sessionId: String? = nil,
        timestamp: Date = Date(),
        metadata: [String: Any]? = nil,
        appContext: String? = nil
    ) {
        self.callerId = callerId
        self.calleeId = calleeId
        self.callType = callType
        self.sessionId = sessionId ?? UUID().uuidString
        self.timestamp = timestamp
        self.metadata = metadata
        self.appContext = appContext
    }
}

// MARK: - Verification Confidence
@objc public enum VerificationConfidence: Int {
    case none = 0
    case low = 1
    case medium = 2
    case high = 3
    case absolute = 4

    public var displayName: String {
        switch self {
        case .none: return "None"
        case .low: return "Low"
        case .medium: return "Medium"
        case .high: return "High"
        case .absolute: return "Absolute"
        }
    }
}

// MARK: - Verification Level
@objc public enum VerificationLevel: Int {
    case basic = 0
    case email = 1
    case domain = 2
    case enterprise = 3
    case certificate = 4

    public var displayName: String {
        switch self {
        case .basic: return "Basic"
        case .email: return "Email"
        case .domain: return "Domain"
        case .enterprise: return "Enterprise"
        case .certificate: return "Certificate"
        }
    }
}

// MARK: - Caller Info
@objc public class CallerInfo: NSObject {
    @objc public let displayName: String?
    @objc public let organization: String?
    @objc public let isVerified: Bool
    @objc public let trustScore: Double
    @objc public let verificationLevel: VerificationLevel
    @objc public let profileImageUrl: String?
    @objc public let domain: String?

    @objc public init(
        displayName: String? = nil,
        organization: String? = nil,
        isVerified: Bool,
        trustScore: Double,
        verificationLevel: VerificationLevel = .basic,
        profileImageUrl: String? = nil,
        domain: String? = nil
    ) {
        self.displayName = displayName
        self.organization = organization
        self.isVerified = isVerified
        self.trustScore = trustScore
        self.verificationLevel = verificationLevel
        self.profileImageUrl = profileImageUrl
        self.domain = domain
    }
}

// MARK: - Verification Result
@objc public class VerificationResult: NSObject {
    @objc public let isVerified: Bool
    @objc public let callerInfo: CallerInfo?
    @objc public let confidence: VerificationConfidence
    @objc public let callType: CallType
    @objc public let timestamp: Date
    @objc public let metadata: [String: Any]?
    @objc public let error: String?

    @objc public init(
        isVerified: Bool,
        callerInfo: CallerInfo? = nil,
        confidence: VerificationConfidence,
        callType: CallType,
        timestamp: Date = Date(),
        metadata: [String: Any]? = nil,
        error: String? = nil
    ) {
        self.isVerified = isVerified
        self.callerInfo = callerInfo
        self.confidence = confidence
        self.callType = callType
        self.timestamp = timestamp
        self.metadata = metadata
        self.error = error
    }
}

// MARK: - Widget Configuration
@objc public class CallDNSWidgetConfig: NSObject {
    @objc public let showTrustScore: Bool
    @objc public let showOrganization: Bool
    @objc public let showVerificationBadge: Bool
    @objc public let autoVerify: Bool
    @objc public let theme: String
    @objc public let size: String

    @objc public init(
        showTrustScore: Bool = true,
        showOrganization: Bool = true,
        showVerificationBadge: Bool = true,
        autoVerify: Bool = true,
        theme: String = "auto",
        size: String = "medium"
    ) {
        self.showTrustScore = showTrustScore
        self.showOrganization = showOrganization
        self.showVerificationBadge = showVerificationBadge
        self.autoVerify = autoVerify
        self.theme = theme
        self.size = size
    }
}

// MARK: - CallDNS Configuration
/**
 * CallDNS SDK Configuration
 *
 * Authentication model:
 * - Core nodes: Public, no auth required (anonymous for privacy)
 * - Org nodes: Bank-issued JWT tokens
 */
@objc public class CallDNSConfig: NSObject {
    @objc public let coreNodeUrl: String
    @objc public let orgNodeUrl: String?
    @objc public let orgAuthToken: String? // JWT token for org node authentication
    @objc public let enableLogging: Bool
    @objc public let cacheTimeout: TimeInterval
    @objc public let maxRetries: Int

    @objc public init(
        coreNodeUrl: String = "https://core.calldns.network",
        orgNodeUrl: String? = nil,
        orgAuthToken: String? = nil,
        enableLogging: Bool = false,
        cacheTimeout: TimeInterval = 300, // 5 minutes
        maxRetries: Int = 3
    ) {
        self.coreNodeUrl = coreNodeUrl
        self.orgNodeUrl = orgNodeUrl
        self.orgAuthToken = orgAuthToken
        self.enableLogging = enableLogging
        self.cacheTimeout = cacheTimeout
        self.maxRetries = maxRetries
    }
}

// MARK: - Outbound Call Result
@objc public class OutboundCallResult: NSObject {
    @objc public let proofId: String
    @objc public let broadcastStatus: String
    @objc public let notified: Int
    @objc public let dialIntent: String
    @objc public let verificationWindow: Int
    @objc public let timestamp: Date

    @objc public init(
        proofId: String,
        broadcastStatus: String,
        notified: Int,
        dialIntent: String,
        verificationWindow: Int = 300,
        timestamp: Date = Date()
    ) {
        self.proofId = proofId
        self.broadcastStatus = broadcastStatus
        self.notified = notified
        self.dialIntent = dialIntent
        self.verificationWindow = verificationWindow
        self.timestamp = timestamp
    }
}

// MARK: - Verified Call Destination
@objc public class VerifiedCallDestination: NSObject {
    @objc public let destinationId: String
    @objc public let destinationName: String
    @objc public let phoneNumber: String
    @objc public let commitment: String?

    @objc public init(
        destinationId: String,
        destinationName: String,
        phoneNumber: String,
        commitment: String? = nil
    ) {
        self.destinationId = destinationId
        self.destinationName = destinationName
        self.phoneNumber = phoneNumber
        self.commitment = commitment
    }
}

// MARK: - CallDNS Errors
public enum CallDNSError: Error {
    case notInitialized
    case networkError(String)
    case verificationFailed(String)
    case orgNodeNotConfigured
    case invalidResponse
}
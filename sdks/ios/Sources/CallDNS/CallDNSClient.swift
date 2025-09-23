import Foundation
import UIKit
import CallKit
import Contacts
import CryptoSwift
import Alamofire

/**
 * CallDNS iOS SDK
 *
 * Provides zero-knowledge proof verification for incoming calls of any type:
 * - Traditional phone calls (via CallKit integration)
 * - VoIP calls (FaceTime, WhatsApp, etc.)
 * - In-app calls
 * - Video calls
 * - Conference calls
 */
@objc public class CallDNSClient: NSObject {

    // MARK: - Singleton
    @objc public static let shared = CallDNSClient()

    // MARK: - Properties
    private var config: CallDNSConfig?
    private var apiService: CallDNSAPIService?
    private var cryptoManager: CryptoManager?
    private var keyManager: KeyManager?
    private var verificationCache: [String: VerificationResult] = [:]
    private let cacheQueue = DispatchQueue(label: "com.calldns.cache", attributes: .concurrent)

    // MARK: - Initialization
    private override init() {
        super.init()
    }

    /**
     * Initialize the CallDNS SDK
     */
    @objc public func initialize(config: CallDNSConfig) {
        self.config = config
        self.apiService = CallDNSAPIService(config: config)
        self.cryptoManager = CryptoManager()
        self.keyManager = KeyManager()

        setupCallKitIntegration()

        print("CallDNS iOS SDK initialized")
    }

    // MARK: - Public Methods

    /**
     * Generate a proof for an outgoing call
     */
    @objc public func generateCallProof(
        callContext: CallContext,
        completion: @escaping (Result<CallProof, Error>) -> Void
    ) {
        guard let apiService = apiService,
              let cryptoManager = cryptoManager,
              let keyManager = keyManager else {
            completion(.failure(CallDNSError.notInitialized))
            return
        }

        DispatchQueue.global(qos: .userInitiated).async {
            do {
                let identity = try keyManager.getOrCreateIdentity()
                let proof = try cryptoManager.generateProof(identity: identity, callContext: callContext)

                apiService.registerProof(proof: proof) { result in
                    switch result {
                    case .success:
                        DispatchQueue.main.async {
                            completion(.success(proof))
                        }
                    case .failure(let error):
                        DispatchQueue.main.async {
                            completion(.failure(error))
                        }
                    }
                }
            } catch {
                DispatchQueue.main.async {
                    completion(.failure(error))
                }
            }
        }
    }

    /**
     * Verify an incoming call
     */
    @objc public func verifyIncomingCall(
        callContext: CallContext,
        completion: @escaping (VerificationResult) -> Void
    ) {
        guard let apiService = apiService,
              let cryptoManager = cryptoManager else {
            let errorResult = VerificationResult(
                isVerified: false,
                callerInfo: nil,
                confidence: .none,
                callType: callContext.callType,
                timestamp: Date(),
                error: "SDK not initialized"
            )
            completion(errorResult)
            return
        }

        let cacheKey = generateCacheKey(callContext: callContext)

        // Check cache first
        cacheQueue.sync {
            if let cached = verificationCache[cacheKey],
               Date().timeIntervalSince(cached.timestamp) < (config?.cacheTimeout ?? 300) {
                DispatchQueue.main.async {
                    completion(cached)
                }
                return
            }
        }

        // Look up proof from network
        apiService.lookupProof(
            callerId: callContext.callerId,
            callType: callContext.callType,
            timestamp: Date()
        ) { [weak self] result in
            guard let self = self else { return }

            let verificationResult: VerificationResult

            switch result {
            case .success(let proof):
                do {
                    let isValid = try cryptoManager.verifyProof(proof: proof, callContext: callContext)
                    verificationResult = VerificationResult(
                        isVerified: isValid,
                        callerInfo: isValid ? self.extractCallerInfo(from: proof) : nil,
                        confidence: isValid ? .high : .none,
                        callType: callContext.callType,
                        timestamp: Date(),
                        metadata: proof.metadata
                    )
                } catch {
                    verificationResult = VerificationResult(
                        isVerified: false,
                        callerInfo: nil,
                        confidence: .none,
                        callType: callContext.callType,
                        timestamp: Date(),
                        error: error.localizedDescription
                    )
                }

            case .failure(let error):
                verificationResult = VerificationResult(
                    isVerified: false,
                    callerInfo: nil,
                    confidence: .none,
                    callType: callContext.callType,
                    timestamp: Date(),
                    error: error.localizedDescription
                )
            }

            // Cache result
            self.cacheQueue.async(flags: .barrier) {
                self.verificationCache[cacheKey] = verificationResult
            }

            DispatchQueue.main.async {
                completion(verificationResult)
            }
        }
    }

    /**
     * Register identity for verification
     */
    @objc public func registerIdentity(
        identityInfo: IdentityInfo,
        completion: @escaping (Result<Bool, Error>) -> Void
    ) {
        guard let apiService = apiService,
              let keyManager = keyManager else {
            completion(.failure(CallDNSError.notInitialized))
            return
        }

        DispatchQueue.global(qos: .userInitiated).async {
            do {
                let identity = try keyManager.createIdentity(identityInfo: identityInfo)

                apiService.registerIdentity(identity: identity) { result in
                    DispatchQueue.main.async {
                        completion(result)
                    }
                }
            } catch {
                DispatchQueue.main.async {
                    completion(.failure(error))
                }
            }
        }
    }

    /**
     * Get verification statistics
     */
    @objc public func getVerificationStats() -> VerificationStats {
        var totalVerifications = 0
        var successfulVerifications = 0

        cacheQueue.sync {
            totalVerifications = verificationCache.count
            successfulVerifications = verificationCache.values.filter { $0.isVerified }.count
        }

        let successRate = totalVerifications > 0 ? Float(successfulVerifications) / Float(totalVerifications) : 0.0

        return VerificationStats(
            totalVerifications: totalVerifications,
            successfulVerifications: successfulVerifications,
            successRate: successRate,
            cacheSize: totalVerifications
        )
    }

    /**
     * Clear verification cache
     */
    @objc public func clearCache() {
        cacheQueue.async(flags: .barrier) {
            self.verificationCache.removeAll()
        }
    }

    // MARK: - Private Methods

    private func setupCallKitIntegration() {
        // Setup CallKit provider for handling calls
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(handleIncomingCall),
            name: .CXCallObserverCallChanged,
            object: nil
        )
    }

    @objc private func handleIncomingCall(_ notification: Notification) {
        // Handle incoming call detection via CallKit
        // This would integrate with the phone app to automatically verify calls
    }

    private func generateCacheKey(callContext: CallContext) -> String {
        return "\(callContext.callerId)_\(callContext.callType.rawValue)_\(callContext.sessionId)"
    }

    private func extractCallerInfo(from proof: CallProof) -> CallerInfo? {
        guard let metadata = proof.metadata else { return nil }

        return CallerInfo(
            displayName: metadata["displayName"] as? String,
            organization: metadata["organization"] as? String,
            verified: true,
            trustScore: calculateTrustScore(proof: proof),
            verificationLevel: .basic,
            profileImage: metadata["profileImage"] as? String
        )
    }

    private func calculateTrustScore(proof: CallProof) -> Float {
        var score: Float = 0.5

        if proof.metadata?["organization"] != nil {
            score += 0.2
        }

        if proof.metadata?["verified_domain"] != nil {
            score += 0.3
        }

        return min(1.0, score)
    }
}

// MARK: - CallKit Integration Extension
extension CallDNSClient: CXCallObserverDelegate {
    public func callObserver(_ callObserver: CXCallObserver, callChanged call: CXCall) {
        if call.hasEnded || call.hasConnected {
            // Handle call state changes
            let callContext = CallContext(
                callerId: call.remoteHandle?.value ?? "unknown",
                calleeId: nil,
                callType: .voiceCall,
                sessionId: call.uuid.uuidString,
                timestamp: Date(),
                metadata: [:],
                appContext: "phone",
                networkInfo: nil
            )

            if !call.hasEnded {
                verifyIncomingCall(callContext: callContext) { result in
                    // Handle verification result
                    NotificationCenter.default.post(
                        name: .callDNSVerificationCompleted,
                        object: result
                    )
                }
            }
        }
    }
}

// MARK: - Notification Names
extension Notification.Name {
    static let callDNSVerificationCompleted = Notification.Name("CallDNSVerificationCompleted")
    static let callDNSProofGenerated = Notification.Name("CallDNSProofGenerated")
}
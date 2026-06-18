import SwiftUI

/**
 * SwiftUI View for call verification widget
 */
public struct SenderVerificationView: View {
    let callContext: CallContext
    let config: TesseraWidgetConfig
    let onVerificationComplete: ((VerificationResult) -> Void)?

    @State private var verificationState: VerificationState = .loading
    @State private var isVisible: Bool = true

    public init(
        callContext: CallContext,
        config: TesseraWidgetConfig = TesseraWidgetConfig(),
        onVerificationComplete: ((VerificationResult) -> Void)? = nil
    ) {
        self.callContext = callContext
        self.config = config
        self.onVerificationComplete = onVerificationComplete
    }

    public var body: some View {
        Group {
            if isVisible {
                VStack {
                    switch verificationState {
                    case .loading:
                        LoadingView(callContext: callContext, config: config)
                    case .verified(let result):
                        VerifiedView(result: result, config: config)
                    case .unverified(let result):
                        UnverifiedView(result: result, config: config)
                    case .error(let message):
                        ErrorView(message: message, config: config)
                    }
                }
                .background(backgroundCard)
                .transition(.asymmetric(
                    insertion: .move(edge: .top).combined(with: .opacity),
                    removal: .move(edge: .top).combined(with: .opacity)
                ))
            }
        }
        .onAppear {
            startVerification()
        }
    }

    private var backgroundCard: some View {
        RoundedRectangle(cornerRadius: 12)
            .fill(cardBackground)
            .shadow(color: .black.opacity(0.1), radius: 4, x: 0, y: 2)
    }

    private var cardBackground: Color {
        switch config.theme {
        case .light:
            return .white
        case .dark:
            return Color(.systemGray6)
        case .auto:
            return Color(.systemBackground)
        }
    }

    private func startVerification() {
        TesseraClient.shared.verifyIncomingCall(callContext: callContext) { result in
            withAnimation(.easeInOut(duration: 0.3)) {
                verificationState = result.isVerified
                    ? .verified(result)
                    : (result.error != nil ? .error(result.error!) : .unverified(result))
            }
            onVerificationComplete?(result)
        }
    }
}

// MARK: - Subviews

private struct LoadingView: View {
    let callContext: CallContext
    let config: TesseraWidgetConfig

    var body: some View {
        HStack(spacing: 12) {
            ProgressView()
                .scaleEffect(0.8)

            VStack(alignment: .leading, spacing: 2) {
                Text("Verifying \(callContext.callType.displayName)...")
                    .font(.system(size: 14, weight: .medium))
                    .foregroundColor(.primary)

                Text("Tessera Security Check")
                    .font(.system(size: 12))
                    .foregroundColor(.secondary)
            }

            Spacer()
        }
        .padding(16)
    }
}

private struct VerifiedView: View {
    let result: VerificationResult
    let config: TesseraWidgetConfig

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Image(systemName: "checkmark.circle.fill")
                    .foregroundColor(.green)
                    .font(.system(size: 24))

                Text("✓ Verified Call")
                    .font(.system(size: 16, weight: .bold))
                    .foregroundColor(.green)

                if config.showVerificationBadge {
                    Spacer()
                    confidenceBadge
                }
            }

            if let callerInfo = result.callerInfo {
                VStack(alignment: .leading, spacing: 4) {
                    if config.showOrganization, let organization = callerInfo.organization {
                        Text(organization)
                            .font(.system(size: 14, weight: .medium))
                            .foregroundColor(.primary)
                    }

                    if let displayName = callerInfo.displayName {
                        Text(displayName)
                            .font(.system(size: 12))
                            .foregroundColor(.secondary)
                    }

                    if config.showTrustScore {
                        TrustScoreView(trustScore: callerInfo.trustScore)
                    }
                }
            }

            Text("Tessera Protected")
                .font(.system(size: 10))
                .foregroundColor(.secondary)
        }
        .padding(16)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color.green.opacity(0.1))
        )
    }

    private var confidenceBadge: some View {
        Text(result.confidence.rawValue.uppercased())
            .font(.system(size: 10, weight: .bold))
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(Color.green.opacity(0.2))
            .foregroundColor(.green)
            .clipShape(Capsule())
    }
}

private struct UnverifiedView: View {
    let result: VerificationResult
    let config: TesseraWidgetConfig

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Image(systemName: "exclamationmark.triangle.fill")
                    .foregroundColor(.orange)
                    .font(.system(size: 24))

                Text("Unverified Call")
                    .font(.system(size: 14, weight: .medium))
                    .foregroundColor(.primary)
            }

            Text("This \(result.callType.displayName) could not be verified")
                .font(.system(size: 12))
                .foregroundColor(.secondary)
        }
        .padding(16)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color.orange.opacity(0.1))
        )
    }
}

private struct ErrorView: View {
    let message: String
    let config: TesseraWidgetConfig

    var body: some View {
        HStack {
            Image(systemName: "xmark.circle.fill")
                .foregroundColor(.red)
                .font(.system(size: 24))

            VStack(alignment: .leading, spacing: 2) {
                Text("Verification Error")
                    .font(.system(size: 14, weight: .medium))
                    .foregroundColor(.red)

                Text(message)
                    .font(.system(size: 12))
                    .foregroundColor(.secondary)
            }

            Spacer()
        }
        .padding(16)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color.red.opacity(0.1))
        )
    }
}

private struct TrustScoreView: View {
    let trustScore: Float

    var body: some View {
        HStack(spacing: 4) {
            Text("Trust Score:")
                .font(.system(size: 10))
                .foregroundColor(.secondary)

            ProgressView(value: Double(trustScore))
                .frame(width: 60, height: 4)
                .tint(trustScoreColor)

            Text("\(Int(trustScore * 100))%")
                .font(.system(size: 10))
                .foregroundColor(.secondary)
        }
    }

    private var trustScoreColor: Color {
        switch trustScore {
        case 0.8...1.0:
            return .green
        case 0.6..<0.8:
            return .orange
        default:
            return .red
        }
    }
}

// MARK: - Supporting Types

private enum VerificationState {
    case loading
    case verified(VerificationResult)
    case unverified(VerificationResult)
    case error(String)
}

// MARK: - CallType Extension

extension CallType {
    var displayName: String {
        switch self {
        case .voiceCall:
            return "voice call"
        case .videoCall:
            return "video call"
        case .voipCall:
            return "VoIP call"
        case .inAppCall:
            return "app call"
        case .conferenceCall:
            return "conference call"
        case .emergencyCall:
            return "emergency call"
        case .unknown:
            return "call"
        }
    }
}

// MARK: - Preview

struct CallVerificationView_Previews: PreviewProvider {
    static var previews: some View {
        VStack(spacing: 20) {
            SenderVerificationView(
                callContext: CallContext(
                    callerId: "+1234567890",
                    calleeId: nil,
                    callType: .voiceCall,
                    sessionId: "preview",
                    timestamp: Date(),
                    metadata: [:],
                    appContext: "preview",
                    networkInfo: nil
                )
            )

            SenderVerificationView(
                callContext: CallContext(
                    callerId: "+1234567890",
                    calleeId: nil,
                    callType: .voipCall,
                    sessionId: "preview2",
                    timestamp: Date(),
                    metadata: [:],
                    appContext: "WhatsApp",
                    networkInfo: nil
                ),
                config: TesseraWidgetConfig(theme: .dark)
            )
        }
        .padding()
        .previewLayout(.sizeThatFits)
    }
}
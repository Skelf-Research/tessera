import SwiftUI
import UIKit

/**
 * Verified Call Button
 *
 * A SwiftUI view that generates a proof, broadcasts it to the network,
 * and then initiates a phone call. This enables customer-to-bank verification.
 *
 * UX Flow:
 * 1. User taps "Call with Verification"
 * 2. SDK generates proof and broadcasts to network
 * 3. Phone app opens with destination number
 * 4. Bank's contact center verifies the proof
 */
public struct VerifiedCallButton: View {
    let phoneNumber: String
    let destinationId: String
    let destinationName: String
    let config: VerifiedCallButtonConfig
    let onCallInitiated: ((CallProof) -> Void)?
    let onError: ((String) -> Void)?

    @State private var buttonState: ButtonState = .ready

    public init(
        phoneNumber: String,
        destinationId: String,
        destinationName: String = "Organization",
        config: VerifiedCallButtonConfig = VerifiedCallButtonConfig(),
        onCallInitiated: ((CallProof) -> Void)? = nil,
        onError: ((String) -> Void)? = nil
    ) {
        self.phoneNumber = phoneNumber
        self.destinationId = destinationId
        self.destinationName = destinationName
        self.config = config
        self.onCallInitiated = onCallInitiated
        self.onError = onError
    }

    public var body: some View {
        VStack(spacing: 8) {
            Button(action: initiateVerifiedCall) {
                HStack(spacing: 8) {
                    buttonContent
                }
                .frame(maxWidth: .infinity)
                .frame(height: CGFloat(config.buttonHeight))
            }
            .buttonStyle(VerifiedCallButtonStyle(
                state: buttonState,
                config: config
            ))
            .disabled(buttonState != .ready)

            if config.showInfoText {
                Text("Your identity will be cryptographically verified")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

            if config.showDestination {
                HStack(spacing: 4) {
                    Image(systemName: "phone.fill")
                        .font(.caption2)
                    Text("\(destinationName): \(phoneNumber)")
                        .font(.caption2)
                }
                .foregroundColor(.secondary.opacity(0.7))
            }
        }
    }

    @ViewBuilder
    private var buttonContent: some View {
        switch buttonState {
        case .ready:
            Image(systemName: "shield.checkmark.fill")
                .font(.body)
            Text(config.buttonText)
                .fontWeight(.medium)

        case .generating:
            ProgressView()
                .progressViewStyle(CircularProgressViewStyle(tint: .white))
                .scaleEffect(0.8)
            Text("Generating proof...")

        case .broadcasting:
            ProgressView()
                .progressViewStyle(CircularProgressViewStyle(tint: .white))
                .scaleEffect(0.8)
            Text("Broadcasting...")

        case .readyToDial:
            Image(systemName: "checkmark.circle.fill")
                .font(.body)
            Text("Opening phone...")

        case .error(let message):
            Image(systemName: "exclamationmark.triangle.fill")
                .font(.body)
            Text(String(message.prefix(30)))
                .font(.subheadline)
        }
    }

    private func initiateVerifiedCall() {
        guard buttonState == .ready else { return }

        buttonState = .generating

        let callContext = CallContext(
            callerId: "customer",
            calleeId: destinationId,
            callType: .voiceCall,
            sessionId: UUID().uuidString,
            timestamp: Date(),
            metadata: [
                "direction": "outbound",
                "destination": destinationId,
                "destination_name": destinationName
            ],
            appContext: nil,
            networkInfo: nil
        )

        CallDNSClient.shared.generateCallProof(callContext: callContext) { result in
            DispatchQueue.main.async {
                switch result {
                case .success(let proof):
                    self.buttonState = .broadcasting

                    // Simulate broadcast delay
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) {
                        self.buttonState = .readyToDial

                        // Open phone dialer
                        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                            self.openPhoneDialer()
                            self.onCallInitiated?(proof)

                            // Reset button
                            DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
                                self.buttonState = .ready
                            }
                        }
                    }

                case .failure(let error):
                    self.buttonState = .error(error.localizedDescription)
                    self.onError?(error.localizedDescription)

                    // Reset after error display
                    DispatchQueue.main.asyncAfter(deadline: .now() + 3.0) {
                        self.buttonState = .ready
                    }
                }
            }
        }
    }

    private func openPhoneDialer() {
        let cleanedNumber = phoneNumber.replacingOccurrences(of: " ", with: "")
        guard let url = URL(string: "tel://\(cleanedNumber)") else { return }

        if UIApplication.shared.canOpenURL(url) {
            UIApplication.shared.open(url)
        }
    }
}

// MARK: - Configuration

public struct VerifiedCallButtonConfig {
    public let buttonText: String
    public let buttonColor: Color
    public let buttonHeight: Int
    public let cornerRadius: CGFloat
    public let showInfoText: Bool
    public let showDestination: Bool

    public init(
        buttonText: String = "Call with Verification",
        buttonColor: Color = Color.blue,
        buttonHeight: Int = 56,
        cornerRadius: CGFloat = 12,
        showInfoText: Bool = true,
        showDestination: Bool = true
    ) {
        self.buttonText = buttonText
        self.buttonColor = buttonColor
        self.buttonHeight = buttonHeight
        self.cornerRadius = cornerRadius
        self.showInfoText = showInfoText
        self.showDestination = showDestination
    }
}

// MARK: - Button State

private enum ButtonState: Equatable {
    case ready
    case generating
    case broadcasting
    case readyToDial
    case error(String)
}

// MARK: - Button Style

private struct VerifiedCallButtonStyle: ButtonStyle {
    let state: ButtonState
    let config: VerifiedCallButtonConfig

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .foregroundColor(.white)
            .background(backgroundColor)
            .cornerRadius(config.cornerRadius)
            .scaleEffect(configuration.isPressed ? 0.98 : 1.0)
            .animation(.easeInOut(duration: 0.1), value: configuration.isPressed)
    }

    private var backgroundColor: Color {
        switch state {
        case .readyToDial:
            return Color.green
        case .error:
            return Color.red
        default:
            return config.buttonColor
        }
    }
}

// MARK: - Preview

struct VerifiedCallButton_Previews: PreviewProvider {
    static var previews: some View {
        VStack(spacing: 20) {
            VerifiedCallButton(
                phoneNumber: "+44 800 123 4567",
                destinationId: "natwest-uk",
                destinationName: "NatWest Bank"
            )
        }
        .padding()
    }
}

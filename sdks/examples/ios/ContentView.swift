import SwiftUI
import CallDNS

struct ContentView: View {
    @StateObject private var viewModel = CallDNSDemoViewModel()

    var body: some View {
        NavigationView {
            ScrollView {
                VStack(spacing: 20) {
                    headerSection
                    callTypeSimulator
                    if viewModel.showWidget {
                        verificationResultCard
                    }
                    integrationExamples
                }
                .padding()
            }
            .navigationTitle("CallDNS Demo")
            .navigationBarTitleDisplayMode(.large)
        }
        .onAppear {
            viewModel.initializeCallDNS()
        }
    }

    private var headerSection: some View {
        VStack(spacing: 12) {
            Text("🛡️ CallDNS iOS Demo")
                .font(.title.bold())
                .foregroundColor(.primary)

            Text("Experience zero-knowledge caller verification on iOS")
                .font(.body)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
        }
    }

    private var callTypeSimulator: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("📞 Call Type Simulator")
                .font(.title2.weight(.semibold))

            Text("Select a call type to simulate verification:")
                .font(.body)
                .foregroundColor(.secondary)

            LazyVGrid(columns: [
                GridItem(.flexible()),
                GridItem(.flexible())
            ], spacing: 12) {
                ForEach(CallType.allCases, id: \.self) { callType in
                    CallTypeCard(
                        callType: callType,
                        isSelected: viewModel.selectedCallType == callType
                    ) {
                        viewModel.selectedCallType = callType
                    }
                }
            }

            VStack(spacing: 12) {
                TextField("Caller ID", text: $viewModel.callerId)
                    .textFieldStyle(.roundedBorder)

                Button("Verify Incoming Call") {
                    viewModel.verifyCall()
                }
                .buttonStyle(.borderedProminent)
                .disabled(viewModel.selectedCallType == nil)
                .frame(maxWidth: .infinity)
            }
        }
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color(.systemBackground))
                .shadow(color: .black.opacity(0.1), radius: 8, x: 0, y: 2)
        )
    }

    @ViewBuilder
    private var verificationResultCard: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                Text("Verification Result")
                    .font(.title2.weight(.semibold))

                Spacer()

                Button("Close") {
                    viewModel.showWidget = false
                }
                .buttonStyle(.bordered)
            }

            if let callContext = viewModel.callContext {
                CallVerificationView(
                    callContext: callContext,
                    config: CallDNSWidgetConfig(
                        showTrustScore: true,
                        showOrganization: true,
                        showVerificationBadge: true,
                        autoVerify: true
                    )
                )
            }
        }
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color(.systemBackground))
                .shadow(color: .black.opacity(0.1), radius: 8, x: 0, y: 2)
        )
    }

    private var integrationExamples: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("📊 Integration Examples")
                .font(.title2.weight(.semibold))

            VStack(alignment: .leading, spacing: 12) {
                ExampleRow(
                    title: "Voice Call Verification",
                    description: "Verify traditional phone calls in real-time"
                )

                ExampleRow(
                    title: "FaceTime Integration",
                    description: "Verify iOS native video calls automatically"
                )

                ExampleRow(
                    title: "CallKit Integration",
                    description: "Seamless integration with iOS call interface"
                )

                ExampleRow(
                    title: "WhatsApp Call Security",
                    description: "Protect VoIP calls from messaging apps"
                )
            }
        }
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color(.systemBackground))
                .shadow(color: .black.opacity(0.1), radius: 8, x: 0, y: 2)
        )
    }
}

struct CallTypeCard: View {
    let callType: CallType
    let isSelected: Bool
    let onSelect: () -> Void

    var body: some View {
        Button(action: onSelect) {
            VStack(spacing: 8) {
                Text(callType.icon)
                    .font(.title)

                Text(callType.displayName)
                    .font(.caption.weight(.medium))
                    .multilineTextAlignment(.center)

                Text(callType.description)
                    .font(.caption2)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
            }
            .frame(maxWidth: .infinity)
            .padding(12)
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .fill(isSelected ? Color.accentColor.opacity(0.2) : Color(.systemGray6))
                    .overlay(
                        RoundedRectangle(cornerRadius: 8)
                            .stroke(isSelected ? Color.accentColor : Color.clear, lineWidth: 2)
                    )
            )
            .foregroundColor(isSelected ? .accentColor : .primary)
        }
        .buttonStyle(.plain)
    }
}

struct ExampleRow: View {
    let title: String
    let description: String

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            Circle()
                .fill(Color.accentColor)
                .frame(width: 6, height: 6)
                .padding(.top, 6)

            VStack(alignment: .leading, spacing: 4) {
                Text(title)
                    .font(.body.weight(.medium))

                Text(description)
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

            Spacer()
        }
    }
}

@MainActor
class CallDNSDemoViewModel: ObservableObject {
    @Published var selectedCallType: CallType?
    @Published var callerId = "+1 (555) 123-4567"
    @Published var showWidget = false
    @Published var callContext: CallContext?

    func initializeCallDNS() {
        let config = CallDNSConfig(
            apiKey: "demo-api-key",
            baseUrl: "https://demo.calldns.com",
            enableLogging: true
        )

        CallDNSClient.shared.initialize(config: config)
    }

    func verifyCall() {
        guard let callType = selectedCallType else { return }

        callContext = CallContext(
            callerId: callerId,
            callType: callType,
            metadata: [
                "displayName": "John Smith",
                "organization": "Acme Corporation"
            ]
        )

        showWidget = true
    }
}

extension CallType {
    var icon: String {
        switch self {
        case .voiceCall: return "📞"
        case .videoCall: return "📹"
        case .voipCall: return "🌐"
        case .webrtcCall: return "🖥️"
        case .inAppCall: return "📱"
        case .conferenceCall: return "👥"
        case .emergencyCall: return "🚨"
        case .screenShare: return "📺"
        case .unknown: return "❓"
        }
    }

    var description: String {
        switch self {
        case .voiceCall: return "Traditional call"
        case .videoCall: return "FaceTime, Meet"
        case .voipCall: return "WhatsApp, Signal"
        case .webrtcCall: return "Browser call"
        case .inAppCall: return "App-to-app"
        case .conferenceCall: return "Multi-party"
        case .emergencyCall: return "Emergency"
        case .screenShare: return "Screen sharing"
        case .unknown: return "Unknown type"
        }
    }
}

struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        ContentView()
    }
}
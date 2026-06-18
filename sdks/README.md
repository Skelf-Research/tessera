# Tessera Mobile & Web SDKs

This directory contains platform-specific SDKs for integrating Tessera zero-knowledge caller verification into mobile and web applications.

## 📱 **Available SDKs**

### Android SDK
**Location:** `android/`
**Language:** Kotlin
**UI Framework:** Jetpack Compose
**Integration:** Easy embed widget for any Android app

```kotlin
// Initialize
TesseraClient.initialize(this, TesseraConfig(apiKey = "your-api-key"))

// Use in Compose
CallVerificationWidget(
    callContext = CallContext(
        callerId = "+1234567890",
        callType = CallType.VOICE_CALL
    )
)
```

### iOS SDK
**Location:** `ios/`
**Language:** Swift
**UI Framework:** SwiftUI + UIKit
**Integration:** Native iOS widget with CallKit integration

```swift
// Initialize
TesseraClient.shared.initialize(config: TesseraConfig(apiKey: "your-api-key"))

// Use in SwiftUI
CallVerificationView(
    callContext: CallContext(
        callerId: "+1234567890",
        callType: .voiceCall
    )
)
```

### React Native SDK
**Location:** `react-native/`
**Language:** TypeScript
**UI Framework:** React Native
**Integration:** Cross-platform mobile widget

```tsx
// Initialize
TesseraClient.initialize({ apiKey: 'your-api-key' });

// Use in React Native
<CallVerificationWidget
  callContext={{
    callerId: '+1234567890',
    callType: CallType.VOICE_CALL
  }}
/>
```

### Web SDK
**Location:** `web/`
**Language:** TypeScript
**UI Framework:** Vanilla JS + React support
**Integration:** WebRTC integration, embeddable widget

```javascript
// Initialize
TesseraClient.initialize({ apiKey: 'your-api-key' });

// Create widget
const widget = new TesseraWidget('#widget-container');
widget.show({
  callerId: '+1234567890',
  callType: 'WEBRTC_CALL'
});
```

### Flutter SDK (Coming Soon)
**Location:** `flutter/`
**Language:** Dart
**UI Framework:** Flutter
**Integration:** Cross-platform widget

## 🎯 **Call Types Supported**

All SDKs support verification for various call types:

- **📞 Voice Calls** - Traditional phone calls
- **📹 Video Calls** - FaceTime, Google Meet, etc.
- **🌐 VoIP Calls** - WhatsApp, Telegram, Signal, etc.
- **📱 In-App Calls** - App-to-app communication
- **👥 Conference Calls** - Multi-party calls
- **🚨 Emergency Calls** - Emergency services
- **🖥️ WebRTC Calls** - Browser-based calls
- **📺 Screen Share** - Screen sharing sessions

## 🚀 **Quick Start Guide**

### 1. Choose Your Platform
Select the appropriate SDK for your platform and follow the platform-specific setup.

### 2. Initialize SDK
```javascript
// Common initialization pattern across all platforms
TesseraClient.initialize({
  apiKey: 'your-api-key',
  baseUrl: 'https://api.tessera.com', // Optional
  enableLogging: true, // Optional
  cacheTimeout: 300000 // 5 minutes
});
```

### 3. Integrate Widget
Embed the verification widget in your call interface:

```javascript
// When receiving a call
const result = await TesseraClient.getInstance().verifyIncomingCall({
  callerId: incomingCallerId,
  callType: 'VOICE_CALL',
  sessionId: callSessionId
});

if (result.isVerified) {
  showVerifiedCallInterface(result.callerInfo);
} else {
  showUnverifiedCallWarning();
}
```

### 4. Handle Results
Process verification results to enhance user experience:

```javascript
function handleVerificationResult(result) {
  if (result.isVerified) {
    console.log('✅ Verified caller:', result.callerInfo.displayName);
    console.log('🏢 Organization:', result.callerInfo.organization);
    console.log('🎯 Trust Score:', result.callerInfo.trustScore);
  } else {
    console.log('⚠️ Unverified call');
    // Show warning to user
  }
}
```

## 🎨 **Widget Customization**

All SDKs support extensive widget customization:

```javascript
const widgetConfig = {
  theme: 'auto', // 'light', 'dark', 'auto'
  size: 'medium', // 'small', 'medium', 'large'
  position: 'top-right', // Various positions
  showTrustScore: true,
  showOrganization: true,
  showVerificationBadge: true,
  autoVerify: true
};
```

## 🔧 **Advanced Features**

### Real-time Verification
```javascript
// Subscribe to verification events
client.on('verification-completed', (result) => {
  updateUI(result);
});

client.on('verification-failed', (error) => {
  showError(error);
});
```

### Proof Generation
```javascript
// Generate proof for outgoing calls
const proof = await client.generateCallProof({
  callerId: myUserId,
  calleeId: recipientId,
  callType: 'VIDEO_CALL',
  metadata: {
    displayName: 'John Doe',
    organization: 'Acme Corp'
  }
});
```

### WebRTC Integration (Web SDK)
```javascript
// Automatic WebRTC call detection
client.on('webrtc-call-detected', (callInfo) => {
  // Automatically verify WebRTC calls
  client.verifyIncomingCall(callInfo);
});
```

## 📊 **Analytics & Monitoring**

Track verification statistics:

```javascript
const stats = client.getStats();
console.log('Verification Success Rate:', stats.successRate);
console.log('Total Verifications:', stats.totalVerifications);
```

## 🔒 **Security & Privacy**

- **Zero-Knowledge Proofs** - No sensitive data exposed
- **Local Key Storage** - Keys stored securely on device
- **End-to-End Encryption** - All communications encrypted
- **No Call Content** - Only verification metadata processed
- **Privacy-First** - No tracking or profiling

## 🌐 **Browser Support (Web SDK)**

- ✅ Chrome 80+
- ✅ Firefox 75+
- ✅ Safari 13+
- ✅ Edge 80+
- ✅ Mobile browsers

## 📱 **Platform Requirements**

### Android
- Minimum SDK: 21 (Android 5.0)
- Target SDK: 34 (Android 14)
- Kotlin 1.8+

### iOS
- Minimum iOS: 13.0
- Swift 5.0+
- Xcode 14+

### React Native
- React Native 0.60+
- React 16.8+

### Web
- ES2018+ support
- WebRTC support (for call detection)

## 🚀 **Getting Started**

1. **Choose your platform** from the directories above
2. **Follow the platform-specific README** in each SDK directory
3. **Run the example apps** to see integration in action
4. **Customize the widget** to match your app's design
5. **Deploy and start protecting** your users from call spoofing

## 📚 **Examples**

Each SDK directory contains complete example applications demonstrating:

- Basic integration
- Advanced customization
- Real-time verification
- Error handling
- Best practices

## 🆘 **Support**

- 📖 [Documentation](../docs/)
- 💬 [GitHub Discussions](https://github.com/dipankar/tessera/discussions)
- 🐛 [Issue Tracker](https://github.com/dipankar/tessera/issues)
- 📧 [Email Support](mailto:support@tessera.com)

## 📄 **License**

All SDKs are released under the MIT License. See [LICENSE](../LICENSE) for details.
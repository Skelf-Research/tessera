import React, { useState, useEffect } from 'react';
import {
  StyleSheet,
  Text,
  View,
  ScrollView,
  TouchableOpacity,
  TextInput,
  SafeAreaView,
  StatusBar,
  Alert,
} from 'react-native';

import {
  CallDNSClient,
  CallVerificationWidget,
  useCallDNSVerification,
  useCallDNSStats,
  CallType,
  CallContext,
  CallDNSWidgetConfig,
} from '@calldns/react-native';

const CALL_TYPES = [
  { type: CallType.VOICE_CALL, icon: '📞', name: 'Voice Call', desc: 'Traditional phone call' },
  { type: CallType.VIDEO_CALL, icon: '📹', name: 'Video Call', desc: 'FaceTime, Google Meet' },
  { type: CallType.VOIP_CALL, icon: '🌐', name: 'VoIP Call', desc: 'WhatsApp, Signal' },
  { type: CallType.WEBRTC_CALL, icon: '🖥️', name: 'WebRTC Call', desc: 'Browser-based call' },
  { type: CallType.IN_APP_CALL, icon: '📱', name: 'In-App Call', desc: 'App-to-app communication' },
  { type: CallType.CONFERENCE_CALL, icon: '👥', name: 'Conference Call', desc: 'Multi-party calls' },
];

const INTEGRATION_EXAMPLES = [
  {
    title: 'Voice Call Verification',
    description: 'Verify traditional phone calls in real-time',
  },
  {
    title: 'WhatsApp Call Integration',
    description: 'Verify VoIP calls from messaging apps',
  },
  {
    title: 'Video Conference Security',
    description: 'Protect Zoom, Teams, and Meet calls',
  },
  {
    title: 'Cross-Platform Support',
    description: 'Works on both iOS and Android seamlessly',
  },
];

export default function App() {
  const [selectedCallType, setSelectedCallType] = useState<CallType | null>(null);
  const [callerId, setCallerId] = useState('+1 (555) 123-4567');
  const [showWidget, setShowWidget] = useState(false);
  const [callContext, setCallContext] = useState<CallContext | null>(null);

  const { stats } = useCallDNSStats();

  useEffect(() => {
    // Initialize CallDNS
    CallDNSClient.initialize({
      apiKey: 'demo-api-key',
      baseUrl: 'https://demo.calldns.com',
      enableLogging: true,
    }).catch((error) => {
      Alert.alert('Initialization Error', error.message);
    });
  }, []);

  const handleVerifyCall = () => {
    if (!selectedCallType) return;

    const context: CallContext = {
      callerId,
      callType: selectedCallType,
      sessionId: `demo-${Date.now()}`,
      timestamp: Date.now(),
      metadata: {
        displayName: 'John Smith',
        organization: 'Acme Corporation',
      },
    };

    setCallContext(context);
    setShowWidget(true);
  };

  const handleCallTypeSelect = (callType: CallType) => {
    setSelectedCallType(callType);
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor="#f8f9fa" />
      <ScrollView style={styles.scrollView} showsVerticalScrollIndicator={false}>
        <View style={styles.content}>
          {/* Header */}
          <View style={styles.header}>
            <Text style={styles.title}>🛡️ CallDNS React Native Demo</Text>
            <Text style={styles.subtitle}>
              Experience zero-knowledge caller verification in React Native
            </Text>
          </View>

          {/* Call Type Simulator */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>📞 Call Type Simulator</Text>
            <Text style={styles.sectionSubtitle}>
              Select a call type to simulate verification:
            </Text>

            <View style={styles.callTypeGrid}>
              {CALL_TYPES.map((item) => (
                <CallTypeCard
                  key={item.type}
                  callType={item}
                  isSelected={selectedCallType === item.type}
                  onSelect={() => handleCallTypeSelect(item.type)}
                />
              ))}
            </View>

            <View style={styles.inputContainer}>
              <Text style={styles.inputLabel}>Caller ID:</Text>
              <TextInput
                style={styles.textInput}
                value={callerId}
                onChangeText={setCallerId}
                placeholder="Enter caller ID"
                placeholderTextColor="#999"
              />
            </View>

            <TouchableOpacity
              style={[
                styles.verifyButton,
                { opacity: selectedCallType ? 1 : 0.5 },
              ]}
              onPress={handleVerifyCall}
              disabled={!selectedCallType}
            >
              <Text style={styles.verifyButtonText}>Verify Incoming Call</Text>
            </TouchableOpacity>
          </View>

          {/* Verification Widget */}
          {showWidget && callContext && (
            <VerificationSection
              callContext={callContext}
              onClose={() => setShowWidget(false)}
            />
          )}

          {/* Statistics */}
          {stats && (
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>📊 Verification Statistics</Text>
              <View style={styles.statsGrid}>
                <StatCard
                  title="Total Verifications"
                  value={stats.totalVerifications.toString()}
                />
                <StatCard
                  title="Successful"
                  value={stats.successfulVerifications.toString()}
                />
                <StatCard
                  title="Success Rate"
                  value={`${Math.round(stats.successRate * 100)}%`}
                />
                <StatCard title="Cache Size" value={stats.cacheSize.toString()} />
              </View>
            </View>
          )}

          {/* Integration Examples */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>💻 Integration Examples</Text>
            {INTEGRATION_EXAMPLES.map((example, index) => (
              <ExampleItem key={index} title={example.title} description={example.description} />
            ))}
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

function CallTypeCard({
  callType,
  isSelected,
  onSelect,
}: {
  callType: typeof CALL_TYPES[0];
  isSelected: boolean;
  onSelect: () => void;
}) {
  return (
    <TouchableOpacity
      style={[styles.callTypeCard, isSelected && styles.callTypeCardSelected]}
      onPress={onSelect}
    >
      <Text style={styles.callTypeIcon}>{callType.icon}</Text>
      <Text style={[styles.callTypeName, isSelected && styles.callTypeNameSelected]}>
        {callType.name}
      </Text>
      <Text style={styles.callTypeDesc}>{callType.desc}</Text>
    </TouchableOpacity>
  );
}

function VerificationSection({
  callContext,
  onClose,
}: {
  callContext: CallContext;
  onClose: () => void;
}) {
  const config: CallDNSWidgetConfig = {
    showTrustScore: true,
    showOrganization: true,
    showVerificationBadge: true,
    autoVerify: true,
  };

  return (
    <View style={styles.section}>
      <View style={styles.sectionHeader}>
        <Text style={styles.sectionTitle}>Verification Result</Text>
        <TouchableOpacity onPress={onClose} style={styles.closeButton}>
          <Text style={styles.closeButtonText}>Close</Text>
        </TouchableOpacity>
      </View>

      <CallVerificationWidget callContext={callContext} config={config} />
    </View>
  );
}

function StatCard({ title, value }: { title: string; value: string }) {
  return (
    <View style={styles.statCard}>
      <Text style={styles.statValue}>{value}</Text>
      <Text style={styles.statTitle}>{title}</Text>
    </View>
  );
}

function ExampleItem({ title, description }: { title: string; description: string }) {
  return (
    <View style={styles.exampleItem}>
      <View style={styles.exampleBullet} />
      <View style={styles.exampleContent}>
        <Text style={styles.exampleTitle}>{title}</Text>
        <Text style={styles.exampleDescription}>{description}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8f9fa',
  },
  scrollView: {
    flex: 1,
  },
  content: {
    padding: 16,
  },
  header: {
    alignItems: 'center',
    marginBottom: 24,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#2c3e50',
    textAlign: 'center',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: '#7f8c8d',
    textAlign: 'center',
    lineHeight: 22,
  },
  section: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 3,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: '600',
    color: '#2c3e50',
    marginBottom: 8,
  },
  sectionSubtitle: {
    fontSize: 16,
    color: '#7f8c8d',
    marginBottom: 16,
  },
  callTypeGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    marginBottom: 20,
  },
  callTypeCard: {
    width: '48%',
    backgroundColor: '#f8f9fa',
    borderRadius: 8,
    padding: 12,
    marginBottom: 12,
    alignItems: 'center',
    borderWidth: 2,
    borderColor: 'transparent',
  },
  callTypeCardSelected: {
    borderColor: '#3498db',
    backgroundColor: '#e3f2fd',
  },
  callTypeIcon: {
    fontSize: 24,
    marginBottom: 8,
  },
  callTypeName: {
    fontSize: 14,
    fontWeight: '600',
    color: '#2c3e50',
    textAlign: 'center',
    marginBottom: 4,
  },
  callTypeNameSelected: {
    color: '#3498db',
  },
  callTypeDesc: {
    fontSize: 12,
    color: '#7f8c8d',
    textAlign: 'center',
    lineHeight: 16,
  },
  inputContainer: {
    marginBottom: 16,
  },
  inputLabel: {
    fontSize: 16,
    fontWeight: '500',
    color: '#2c3e50',
    marginBottom: 8,
  },
  textInput: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
    backgroundColor: 'white',
  },
  verifyButton: {
    backgroundColor: '#3498db',
    borderRadius: 8,
    padding: 16,
    alignItems: 'center',
  },
  verifyButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
  closeButton: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    backgroundColor: '#ecf0f1',
    borderRadius: 6,
  },
  closeButtonText: {
    color: '#2c3e50',
    fontWeight: '500',
  },
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  statCard: {
    width: '48%',
    backgroundColor: '#f8f9fa',
    borderRadius: 8,
    padding: 16,
    marginBottom: 12,
    alignItems: 'center',
  },
  statValue: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#3498db',
    marginBottom: 4,
  },
  statTitle: {
    fontSize: 12,
    color: '#7f8c8d',
    textAlign: 'center',
    textTransform: 'uppercase',
  },
  exampleItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  exampleBullet: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: '#3498db',
    marginTop: 8,
    marginRight: 12,
  },
  exampleContent: {
    flex: 1,
  },
  exampleTitle: {
    fontSize: 16,
    fontWeight: '500',
    color: '#2c3e50',
    marginBottom: 4,
  },
  exampleDescription: {
    fontSize: 14,
    color: '#7f8c8d',
    lineHeight: 20,
  },
});
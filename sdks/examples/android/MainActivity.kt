package com.tessera.example

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.lifecycleScope
import com.tessera.sdk.TesseraClient
import com.tessera.sdk.TesseraConfig
import com.tessera.sdk.CallContext
import com.tessera.sdk.CallType
import com.tessera.sdk.ui.SenderVerificationWidget
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Initialize Tessera
        val config = TesseraConfig(
            apiKey = "demo-api-key",
            baseUrl = "https://demo.tessera.com",
            enableLogging = true
        )

        lifecycleScope.launch {
            TesseraClient.initialize(this@MainActivity, config)
        }

        setContent {
            TesseraExampleTheme {
                TesseraDemo()
            }
        }
    }
}

@Composable
fun TesseraDemo() {
    var selectedCallType by remember { mutableStateOf<CallType?>(null) }
    var callerId by remember { mutableStateOf("+1 (555) 123-4567") }
    var showWidget by remember { mutableStateOf(false) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Text(
            text = "🛡️ Tessera Android Demo",
            style = MaterialTheme.typography.headlineMedium,
            fontWeight = FontWeight.Bold
        )

        Text(
            text = "Experience zero-knowledge caller verification on Android",
            style = MaterialTheme.typography.bodyLarge,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        Card {
            Column(
                modifier = Modifier.padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Text(
                    text = "📞 Call Type Simulator",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold
                )

                LazyColumn(
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    items(CallType.values()) { callType ->
                        CallTypeCard(
                            callType = callType,
                            isSelected = selectedCallType == callType,
                            onSelect = { selectedCallType = callType }
                        )
                    }
                }

                OutlinedTextField(
                    value = callerId,
                    onValueChange = { callerId = it },
                    label = { Text("Caller ID") },
                    modifier = Modifier.fillMaxWidth()
                )

                Button(
                    onClick = { showWidget = true },
                    enabled = selectedCallType != null,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Verify Incoming Call")
                }
            }
        }

        if (showWidget && selectedCallType != null) {
            Card {
                Column(
                    modifier = Modifier.padding(16.dp)
                ) {
                    Text(
                        text = "Verification Result",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.SemiBold
                    )

                    Spacer(modifier = Modifier.height(12.dp))

                    SenderVerificationWidget(
                        callContext = CallContext(
                            callerId = callerId,
                            callType = selectedCallType!!,
                            metadata = mapOf(
                                "displayName" to "John Smith",
                                "organization" to "Acme Corporation"
                            )
                        ),
                        onVerificationComplete = {
                            // Handle verification complete
                        },
                        onError = { error ->
                            // Handle error
                        }
                    )

                    Spacer(modifier = Modifier.height(12.dp))

                    TextButton(
                        onClick = { showWidget = false },
                        modifier = Modifier.align(Alignment.End)
                    ) {
                        Text("Close")
                    }
                }
            }
        }

        Card {
            Column(
                modifier = Modifier.padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Text(
                    text = "📊 Integration Examples",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold
                )

                ExampleItem(
                    title = "Voice Call Verification",
                    description = "Verify traditional phone calls in real-time"
                )

                ExampleItem(
                    title = "WhatsApp Call Integration",
                    description = "Verify VoIP calls from messaging apps"
                )

                ExampleItem(
                    title = "Video Conference Security",
                    description = "Protect Zoom, Teams, and Meet calls"
                )
            }
        }
    }
}

@Composable
fun CallTypeCard(
    callType: CallType,
    isSelected: Boolean,
    onSelect: () -> Unit
) {
    Card(
        onClick = onSelect,
        colors = CardDefaults.cardColors(
            containerColor = if (isSelected) {
                MaterialTheme.colorScheme.primaryContainer
            } else {
                MaterialTheme.colorScheme.surface
            }
        ),
        border = if (isSelected) {
            CardDefaults.outlinedCardBorder().copy(
                brush = null,
                width = 2.dp
            )
        } else null
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = getCallTypeIcon(callType),
                style = MaterialTheme.typography.headlineSmall
            )

            Spacer(modifier = Modifier.width(12.dp))

            Column {
                Text(
                    text = getCallTypeDisplayName(callType),
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Medium
                )
                Text(
                    text = getCallTypeDescription(callType),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}

@Composable
fun ExampleItem(
    title: String,
    description: String
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.Top
    ) {
        Text(
            text = "•",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.primary
        )

        Spacer(modifier = Modifier.width(8.dp))

        Column {
            Text(
                text = title,
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.Medium
            )
            Text(
                text = description,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

fun getCallTypeIcon(callType: CallType): String {
    return when (callType) {
        CallType.VOICE_CALL -> "📞"
        CallType.VIDEO_CALL -> "📹"
        CallType.VOIP_CALL -> "🌐"
        CallType.WEBRTC_CALL -> "🖥️"
        CallType.IN_APP_CALL -> "📱"
        CallType.CONFERENCE_CALL -> "👥"
        CallType.EMERGENCY_CALL -> "🚨"
        CallType.SCREEN_SHARE -> "📺"
        else -> "❓"
    }
}

fun getCallTypeDisplayName(callType: CallType): String {
    return when (callType) {
        CallType.VOICE_CALL -> "Voice Call"
        CallType.VIDEO_CALL -> "Video Call"
        CallType.VOIP_CALL -> "VoIP Call"
        CallType.WEBRTC_CALL -> "WebRTC Call"
        CallType.IN_APP_CALL -> "In-App Call"
        CallType.CONFERENCE_CALL -> "Conference Call"
        CallType.EMERGENCY_CALL -> "Emergency Call"
        CallType.SCREEN_SHARE -> "Screen Share"
        else -> "Unknown"
    }
}

fun getCallTypeDescription(callType: CallType): String {
    return when (callType) {
        CallType.VOICE_CALL -> "Traditional phone call"
        CallType.VIDEO_CALL -> "FaceTime, Google Meet"
        CallType.VOIP_CALL -> "WhatsApp, Signal"
        CallType.WEBRTC_CALL -> "Browser-based call"
        CallType.IN_APP_CALL -> "App-to-app communication"
        CallType.CONFERENCE_CALL -> "Multi-party calls"
        CallType.EMERGENCY_CALL -> "Emergency services"
        CallType.SCREEN_SHARE -> "Screen sharing session"
        else -> "Unknown call type"
    }
}

@Composable
fun TesseraExampleTheme(content: @Composable () -> Unit) {
    MaterialTheme(content = content)
}
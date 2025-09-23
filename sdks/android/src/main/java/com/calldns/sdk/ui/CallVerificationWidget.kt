package com.calldns.sdk.ui

import androidx.compose.animation.*
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.calldns.sdk.*
import kotlinx.coroutines.delay

/**
 * CallDNS Verification Widget
 *
 * A composable widget that can be embedded in any Android app to show
 * call verification status. Supports various call types and themes.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CallVerificationWidget(
    callContext: CallContext,
    config: CallDNSWidgetConfig = CallDNSWidgetConfig(),
    onVerificationComplete: ((VerificationResult) -> Unit)? = null,
    modifier: Modifier = Modifier
) {
    var verificationState by remember { mutableStateOf<VerificationState>(VerificationState.Loading) }
    var isVisible by remember { mutableStateOf(true) }

    LaunchedEffect(callContext) {
        try {
            val client = CallDNSClient.getInstance()
            val result = client.verifyIncomingCall(callContext) { result ->
                verificationState = when {
                    result.isVerified -> VerificationState.Verified(result)
                    result.error != null -> VerificationState.Error(result.error!!)
                    else -> VerificationState.Unverified(result)
                }
                onVerificationComplete?.invoke(result)
            }
        } catch (e: Exception) {
            verificationState = VerificationState.Error(e.message ?: "Unknown error")
        }
    }

    AnimatedVisibility(
        visible = isVisible,
        enter = slideInVertically() + fadeIn(),
        exit = slideOutVertically() + fadeOut(),
        modifier = modifier
    ) {
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .padding(8.dp),
            shape = RoundedCornerShape(12.dp),
            elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
        ) {
            when (verificationState) {
                is VerificationState.Loading -> LoadingContent(callContext, config)
                is VerificationState.Verified -> VerifiedContent(verificationState.result, config)
                is VerificationState.Unverified -> UnverifiedContent(verificationState.result, config)
                is VerificationState.Error -> ErrorContent(verificationState.message, config)
            }
        }
    }
}

@Composable
private fun LoadingContent(
    callContext: CallContext,
    config: CallDNSWidgetConfig
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(16.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        CircularProgressIndicator(
            modifier = Modifier.size(24.dp),
            strokeWidth = 2.dp
        )

        Spacer(modifier = Modifier.width(12.dp))

        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = "Verifying ${callContext.callType.displayName()}...",
                fontSize = 14.sp,
                fontWeight = FontWeight.Medium
            )
            Text(
                text = "CallDNS Security Check",
                fontSize = 12.sp,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
            )
        }
    }
}

@Composable
private fun VerifiedContent(
    result: VerificationResult,
    config: CallDNSWidgetConfig
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(
                Color(0xFF4CAF50).copy(alpha = 0.1f),
                RoundedCornerShape(12.dp)
            )
            .padding(16.dp)
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier.fillMaxWidth()
        ) {
            Icon(
                Icons.Default.Check,
                contentDescription = "Verified",
                tint = Color(0xFF4CAF50),
                modifier = Modifier.size(24.dp)
            )

            Spacer(modifier = Modifier.width(8.dp))

            Text(
                text = "✓ Verified Call",
                fontSize = 16.sp,
                fontWeight = FontWeight.Bold,
                color = Color(0xFF4CAF50)
            )

            if (config.showVerificationBadge) {
                Spacer(modifier = Modifier.width(8.dp))
                Badge {
                    Text(
                        text = result.confidence.name,
                        fontSize = 10.sp
                    )
                }
            }
        }

        result.callerInfo?.let { callerInfo ->
            Spacer(modifier = Modifier.height(8.dp))

            if (config.showOrganization && callerInfo.organization != null) {
                Text(
                    text = callerInfo.organization!!,
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Medium,
                    color = MaterialTheme.colorScheme.onSurface
                )
            }

            callerInfo.displayName?.let { name ->
                Text(
                    text = name,
                    fontSize = 12.sp,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.8f)
                )
            }

            if (config.showTrustScore) {
                Spacer(modifier = Modifier.height(4.dp))
                TrustScoreIndicator(callerInfo.trustScore)
            }
        }

        Text(
            text = "CallDNS Protected",
            fontSize = 10.sp,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
            modifier = Modifier.padding(top = 4.dp)
        )
    }
}

@Composable
private fun UnverifiedContent(
    result: VerificationResult,
    config: CallDNSWidgetConfig
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(
                MaterialTheme.colorScheme.surfaceVariant,
                RoundedCornerShape(12.dp)
            )
            .padding(16.dp)
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier.fillMaxWidth()
        ) {
            Icon(
                Icons.Default.Warning,
                contentDescription = "Unverified",
                tint = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
                modifier = Modifier.size(24.dp)
            )

            Spacer(modifier = Modifier.width(8.dp))

            Text(
                text = "Unverified Call",
                fontSize = 14.sp,
                fontWeight = FontWeight.Medium,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.8f)
            )
        }

        Text(
            text = "This ${result.callType.displayName()} could not be verified",
            fontSize = 12.sp,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
            modifier = Modifier.padding(top = 4.dp)
        )
    }
}

@Composable
private fun ErrorContent(
    message: String,
    config: CallDNSWidgetConfig
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(
                MaterialTheme.colorScheme.errorContainer.copy(alpha = 0.3f),
                RoundedCornerShape(12.dp)
            )
            .padding(16.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(
            Icons.Default.Close,
            contentDescription = "Error",
            tint = MaterialTheme.colorScheme.error,
            modifier = Modifier.size(24.dp)
        )

        Spacer(modifier = Modifier.width(8.dp))

        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = "Verification Error",
                fontSize = 14.sp,
                fontWeight = FontWeight.Medium,
                color = MaterialTheme.colorScheme.error
            )
            Text(
                text = message,
                fontSize = 12.sp,
                color = MaterialTheme.colorScheme.onErrorContainer
            )
        }
    }
}

@Composable
private fun TrustScoreIndicator(trustScore: Float) {
    Row(
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            text = "Trust Score: ",
            fontSize = 10.sp,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
        )

        LinearProgressIndicator(
            progress = trustScore,
            modifier = Modifier
                .width(60.dp)
                .height(4.dp)
                .clip(RoundedCornerShape(2.dp)),
            color = when {
                trustScore >= 0.8f -> Color(0xFF4CAF50)
                trustScore >= 0.6f -> Color(0xFFFF9800)
                else -> Color(0xFFF44336)
            }
        )

        Text(
            text = "${(trustScore * 100).toInt()}%",
            fontSize = 10.sp,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
            modifier = Modifier.padding(start = 4.dp)
        )
    }
}

private sealed class VerificationState {
    object Loading : VerificationState()
    data class Verified(val result: VerificationResult) : VerificationState()
    data class Unverified(val result: VerificationResult) : VerificationState()
    data class Error(val message: String) : VerificationState()
}

private fun CallType.displayName(): String = when (this) {
    CallType.VOICE_CALL -> "voice call"
    CallType.VIDEO_CALL -> "video call"
    CallType.VOIP_CALL -> "VoIP call"
    CallType.IN_APP_CALL -> "app call"
    CallType.CONFERENCE_CALL -> "conference call"
    CallType.EMERGENCY_CALL -> "emergency call"
    CallType.UNKNOWN -> "call"
}

@Preview
@Composable
private fun CallVerificationWidgetPreview() {
    MaterialTheme {
        CallVerificationWidget(
            callContext = CallContext(
                callerId = "+1234567890",
                callType = CallType.VOICE_CALL
            )
        )
    }
}
package com.tessera.sdk.ui

import android.content.Intent
import android.net.Uri
import androidx.compose.animation.*
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Call
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Security
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.tessera.sdk.*
import kotlinx.coroutines.launch

/**
 * Verified Call Button
 *
 * A composable button that generates a proof, broadcasts it to the network,
 * and then initiates a phone call. This enables customer-to-bank verification.
 *
 * UX Flow:
 * 1. User taps "Call with Verification"
 * 2. SDK generates proof and broadcasts to network
 * 3. Phone dialer opens with destination number
 * 4. Bank's contact center verifies the proof
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun VerifiedSenderButton(
    phoneNumber: String,
    destinationId: String,
    destinationName: String = "Organization",
    config: VerifiedCallButtonConfig = VerifiedCallButtonConfig(),
    onCallInitiated: ((CallProof) -> Unit)? = null,
    onError: ((String) -> Unit)? = null,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var buttonState by remember { mutableStateOf<ButtonState>(ButtonState.Ready) }

    Column(
        modifier = modifier,
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Button(
            onClick = {
                if (buttonState == ButtonState.Ready) {
                    buttonState = ButtonState.Generating

                    scope.launch {
                        try {
                            val client = TesseraClient.getInstance()

                            // Generate proof for outbound call
                            val callContext = CallContext(
                                callerId = "customer", // Will be filled by SDK
                                calleeId = destinationId,
                                callType = CallType.VOICE_CALL,
                                metadata = mapOf(
                                    "direction" to "outbound",
                                    "destination" to destinationId,
                                    "destination_name" to destinationName
                                )
                            )

                            val result = client.generateCallProof(callContext)

                            result.fold(
                                onSuccess = { proof ->
                                    buttonState = ButtonState.Broadcasting

                                    // Proof is registered with network by generateCallProof
                                    buttonState = ButtonState.Ready_To_Dial

                                    // Short delay to show success state
                                    kotlinx.coroutines.delay(500)

                                    // Open phone dialer
                                    val intent = Intent(Intent.ACTION_DIAL).apply {
                                        data = Uri.parse("tel:$phoneNumber")
                                    }
                                    context.startActivity(intent)

                                    onCallInitiated?.invoke(proof)

                                    // Reset after dial
                                    kotlinx.coroutines.delay(1000)
                                    buttonState = ButtonState.Ready
                                },
                                onFailure = { error ->
                                    buttonState = ButtonState.Error(error.message ?: "Failed to generate proof")
                                    onError?.invoke(error.message ?: "Unknown error")

                                    // Reset after error display
                                    kotlinx.coroutines.delay(3000)
                                    buttonState = ButtonState.Ready
                                }
                            )
                        } catch (e: Exception) {
                            buttonState = ButtonState.Error(e.message ?: "Unknown error")
                            onError?.invoke(e.message ?: "Unknown error")

                            kotlinx.coroutines.delay(3000)
                            buttonState = ButtonState.Ready
                        }
                    }
                }
            },
            enabled = buttonState == ButtonState.Ready,
            colors = ButtonDefaults.buttonColors(
                containerColor = when (buttonState) {
                    is ButtonState.Ready_To_Dial -> Color(0xFF4CAF50)
                    is ButtonState.Error -> MaterialTheme.colorScheme.error
                    else -> config.buttonColor
                }
            ),
            shape = RoundedCornerShape(config.cornerRadius),
            modifier = Modifier
                .fillMaxWidth()
                .height(config.buttonHeight)
        ) {
            AnimatedContent(
                targetState = buttonState,
                transitionSpec = {
                    fadeIn() togetherWith fadeOut()
                }
            ) { state ->
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.Center
                ) {
                    when (state) {
                        is ButtonState.Ready -> {
                            Icon(
                                Icons.Default.Security,
                                contentDescription = null,
                                modifier = Modifier.size(20.dp)
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = config.buttonText,
                                fontSize = 16.sp,
                                fontWeight = FontWeight.Medium
                            )
                        }
                        is ButtonState.Generating -> {
                            CircularProgressIndicator(
                                modifier = Modifier.size(20.dp),
                                strokeWidth = 2.dp,
                                color = MaterialTheme.colorScheme.onPrimary
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = "Generating proof...",
                                fontSize = 16.sp
                            )
                        }
                        is ButtonState.Broadcasting -> {
                            CircularProgressIndicator(
                                modifier = Modifier.size(20.dp),
                                strokeWidth = 2.dp,
                                color = MaterialTheme.colorScheme.onPrimary
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = "Broadcasting...",
                                fontSize = 16.sp
                            )
                        }
                        is ButtonState.Ready_To_Dial -> {
                            Icon(
                                Icons.Default.Check,
                                contentDescription = null,
                                modifier = Modifier.size(20.dp)
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = "Opening dialer...",
                                fontSize = 16.sp
                            )
                        }
                        is ButtonState.Error -> {
                            Icon(
                                Icons.Default.Call,
                                contentDescription = null,
                                modifier = Modifier.size(20.dp)
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = state.message.take(30),
                                fontSize = 14.sp
                            )
                        }
                    }
                }
            }
        }

        // Info text below button
        if (config.showInfoText) {
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = "Your identity will be cryptographically verified",
                fontSize = 12.sp,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
            )
        }

        // Destination info
        if (config.showDestination) {
            Spacer(modifier = Modifier.height(4.dp))
            Row(
                verticalAlignment = Alignment.CenterVertically
            ) {
                Icon(
                    Icons.Default.Call,
                    contentDescription = null,
                    modifier = Modifier.size(12.dp),
                    tint = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f)
                )
                Spacer(modifier = Modifier.width(4.dp))
                Text(
                    text = "$destinationName: $phoneNumber",
                    fontSize = 11.sp,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f)
                )
            }
        }
    }
}

/**
 * Configuration for VerifiedSenderButton
 */
data class VerifiedCallButtonConfig(
    val buttonText: String = "Call with Verification",
    val buttonColor: Color = Color(0xFF1976D2),
    val buttonHeight: Int = 56,
    val cornerRadius: Int = 12,
    val showInfoText: Boolean = true,
    val showDestination: Boolean = true
)

private sealed class ButtonState {
    object Ready : ButtonState()
    object Generating : ButtonState()
    object Broadcasting : ButtonState()
    object Ready_To_Dial : ButtonState()
    data class Error(val message: String) : ButtonState()
}

@Preview
@Composable
private fun VerifiedCallButtonPreview() {
    MaterialTheme {
        Surface(
            modifier = Modifier.padding(16.dp)
        ) {
            VerifiedSenderButton(
                phoneNumber = "+44 800 123 4567",
                destinationId = "natwest-uk",
                destinationName = "NatWest Bank"
            )
        }
    }
}

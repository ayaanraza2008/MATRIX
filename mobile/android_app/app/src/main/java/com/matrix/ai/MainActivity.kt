package com.matrix.ai

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.animation.core.*
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.matrix.ai.network.ConnectionState
import com.matrix.ai.network.MatrixApiClient
import com.matrix.ai.network.SystemStatus
import com.matrix.ai.ui.theme.*
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

data class ChatMessage(
    val role: String,
    val text: String,
    val audioUrl: String? = null,
    val latencyMs: Float = 0f
)

class MainActivity : ComponentActivity() {
    private lateinit var apiClient: MatrixApiClient

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        apiClient = MatrixApiClient(applicationContext)

        setContent {
            MatrixTheme {
                MatrixMobileApp(apiClient)
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        apiClient.disconnect()
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MatrixMobileApp(apiClient: MatrixApiClient) {
    val connectionState by apiClient.connectionState.collectAsState()
    val systemStatus by apiClient.systemStatus.collectAsState()

    var inputText by remember { mutableStateOf("") }
    val messages = remember { mutableStateListOf<ChatMessage>() }
    val coroutineScope = rememberCoroutineScope()
    var isVoiceReplyEnabled by remember { mutableStateOf(false) }
    var showPairDialog by remember { mutableStateOf(false) }

    var pairHostInput by remember { mutableStateOf(apiClient.serverHost) }
    var pairTokenInput by remember { mutableStateOf("") }
    var pairErrorMsg by remember { mutableStateOf<String?>(null) }
    var isPairingLoading by remember { mutableStateOf(false) }

    // Periodic telemetry fetch when connected
    LaunchedEffect(connectionState) {
        if (connectionState == ConnectionState.CONNECTED) {
            messages.add(ChatMessage("assistant", "MATRIX Link established. Remote companion online."))
            while (connectionState == ConnectionState.CONNECTED) {
                apiClient.fetchStatus()
                delay(4000)
            }
        } else if (connectionState == ConnectionState.REVOKED) {
            messages.add(ChatMessage("assistant", "SECURITY ALERT: Device authorization was revoked by host."))
        }
    }

    // Holographic core animation
    val infiniteTransition = rememberInfiniteTransition(label = "rotation")
    val rotation by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 360f,
        animationSpec = infiniteRepeatable(
            animation = tween(10000, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "coreRotation"
    )

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween,
                        modifier = Modifier.fillMaxWidth().padding(end = 8.dp)
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text(
                                "MATRIX MOBILE",
                                fontFamily = FontFamily.Monospace,
                                fontWeight = FontWeight.Bold,
                                fontSize = 15.sp,
                                color = MatrixCyan
                            )
                            Spacer(modifier = Modifier.width(8.dp))

                            // Connection State Pill
                            val (badgeColor, stateLabel) = when (connectionState) {
                                ConnectionState.CONNECTED -> Pair(MatrixGreen, "CONNECTED")
                                ConnectionState.RECONNECTING -> Pair(Color(0xFFFFB300), "RECONNECTING")
                                ConnectionState.DISCONNECTED -> Pair(MatrixRed, "OFFLINE")
                                ConnectionState.REVOKED -> Pair(Color(0xFF888888), "REVOKED")
                            }

                            Surface(
                                shape = RoundedCornerShape(12.dp),
                                color = badgeColor.copy(alpha = 0.2f),
                                border = BorderStroke(1.dp, badgeColor)
                            ) {
                                Text(
                                    text = stateLabel,
                                    fontSize = 9.sp,
                                    fontFamily = FontFamily.Monospace,
                                    color = badgeColor,
                                    modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                                )
                            }
                        }

                        // Top Action Icons: Pair / Settings & Revoke
                        Row {
                            IconButton(onClick = { showPairDialog = true }) {
                                Icon(
                                    imageVector = Icons.Default.QrCodeScanner,
                                    contentDescription = "Pair Device",
                                    tint = MatrixCyan
                                )
                            }
                            if (connectionState == ConnectionState.CONNECTED) {
                                IconButton(onClick = {
                                    coroutineScope.launch {
                                        apiClient.revokeDevice()
                                    }
                                }) {
                                    Icon(
                                        imageVector = Icons.Default.LinkOff,
                                        contentDescription = "Revoke Connection",
                                        tint = MatrixRed
                                    )
                                }
                            }
                        }
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = Color(0xFF070B16)
                )
            )
        },
        bottomBar = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(Color(0xFF070B16))
                    .padding(8.dp)
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    // Voice Reply Toggle
                    IconButton(
                        onClick = { isVoiceReplyEnabled = !isVoiceReplyEnabled },
                        modifier = Modifier
                            .size(42.dp)
                            .background(if (isVoiceReplyEnabled) MatrixGreen else MatrixCard, CircleShape)
                    ) {
                        Icon(
                            imageVector = Icons.Default.Mic,
                            contentDescription = "Voice Mode",
                            tint = if (isVoiceReplyEnabled) Color.Black else MatrixCyan
                        )
                    }

                    Spacer(modifier = Modifier.width(8.dp))

                    TextField(
                        value = inputText,
                        onValueChange = { inputText = it },
                        placeholder = { Text("Directive for MATRIX...", fontSize = 12.sp, color = MatrixTextMuted) },
                        modifier = Modifier.weight(1f),
                        colors = TextFieldDefaults.colors(
                            focusedContainerColor = MatrixCard,
                            unfocusedContainerColor = MatrixCard,
                            focusedTextColor = Color.White,
                            unfocusedTextColor = Color.White
                        ),
                        shape = RoundedCornerShape(8.dp)
                    )

                    Spacer(modifier = Modifier.width(8.dp))

                    IconButton(
                        onClick = {
                            val text = inputText.trim()
                            if (text.isNotEmpty()) {
                                messages.add(ChatMessage("user", text))
                                inputText = ""
                                coroutineScope.launch {
                                    val res = apiClient.sendCommand(text, synthesizeVoice = isVoiceReplyEnabled)
                                    messages.add(
                                        ChatMessage(
                                            role = "assistant",
                                            text = res.reply,
                                            audioUrl = res.audioUrl,
                                            latencyMs = res.latencyMs
                                        )
                                    )
                                }
                            }
                        },
                        enabled = connectionState == ConnectionState.CONNECTED,
                        modifier = Modifier
                            .size(42.dp)
                            .background(if (connectionState == ConnectionState.CONNECTED) MatrixCyan else Color.DarkGray, CircleShape)
                    ) {
                        Icon(imageVector = Icons.Default.Send, contentDescription = "Send", tint = Color.Black)
                    }
                }
            }
        }
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .background(MatrixBackground)
                .padding(innerPadding)
                .padding(12.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            // Live Hardware Telemetry Strip
            Surface(
                modifier = Modifier.fillMaxWidth().padding(bottom = 12.dp),
                color = MatrixCard,
                shape = RoundedCornerShape(10.dp),
                border = BorderStroke(1.dp, MatrixBlue.copy(alpha = 0.5f))
            ) {
                Column(modifier = Modifier.padding(10.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "HOST TELEMETRY (${systemStatus.lanIp})",
                            fontFamily = FontFamily.Monospace,
                            fontSize = 10.sp,
                            color = MatrixCyan
                        )
                        Text(
                            text = systemStatus.systemStatus,
                            fontFamily = FontFamily.Monospace,
                            fontSize = 10.sp,
                            fontWeight = FontWeight.Bold,
                            color = if (systemStatus.systemStatus == "NOMINAL") MatrixGreen else MatrixRed
                        )
                    }

                    Spacer(modifier = Modifier.height(6.dp))

                    // CPU and RAM Progress Indicators
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text("CPU: ${systemStatus.cpuPercent.toInt()}%", fontSize = 10.sp, color = Color.White, fontFamily = FontFamily.Monospace)
                            LinearProgressIndicator(
                                progress = { (systemStatus.cpuPercent / 100f).coerceIn(0f, 1f) },
                                modifier = Modifier.fillMaxWidth().height(4.dp).clip(RoundedCornerShape(2.dp)),
                                color = MatrixCyan,
                                trackColor = Color(0xFF131D33)
                            )
                        }
                        Column(modifier = Modifier.weight(1f)) {
                            Text("RAM: ${systemStatus.ramUsedPercent.toInt()}%", fontSize = 10.sp, color = Color.White, fontFamily = FontFamily.Monospace)
                            LinearProgressIndicator(
                                progress = { (systemStatus.ramUsedPercent / 100f).coerceIn(0f, 1f) },
                                modifier = Modifier.fillMaxWidth().height(4.dp).clip(RoundedCornerShape(2.dp)),
                                color = MatrixBlue,
                                trackColor = Color(0xFF131D33)
                            )
                        }
                    }
                }
            }

            // Central Hologram Ring
            Box(
                modifier = Modifier
                    .size(90.dp)
                    .rotate(rotation)
                    .border(2.dp, MatrixCyan.copy(alpha = 0.6f), CircleShape)
                    .padding(6.dp)
                    .border(1.dp, MatrixBlue.copy(alpha = 0.8f), CircleShape),
                contentAlignment = Alignment.Center
            ) {
                Box(
                    modifier = Modifier
                        .size(14.dp)
                        .background(if (connectionState == ConnectionState.CONNECTED) MatrixCyan else MatrixRed, CircleShape)
                )
            }

            Spacer(modifier = Modifier.height(8.dp))

            // Conversation Stream
            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                items(messages) { msg ->
                    val isUser = msg.role == "user"
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = if (isUser) Arrangement.End else Arrangement.Start
                    ) {
                        Surface(
                            shape = RoundedCornerShape(12.dp),
                            color = if (isUser) Color(0xFF0F1A30) else MatrixCard,
                            border = BorderStroke(
                                1.dp,
                                if (isUser) MatrixBlue else MatrixCyan.copy(alpha = 0.3f)
                            ),
                            modifier = Modifier.widthIn(max = 300.dp)
                        ) {
                            Column(modifier = Modifier.padding(10.dp)) {
                                Text(
                                    text = msg.text,
                                    fontSize = 12.sp,
                                    fontFamily = FontFamily.Monospace,
                                    color = Color.White
                                )
                                if (msg.latencyMs > 0) {
                                    Spacer(modifier = Modifier.height(4.dp))
                                    Text(
                                        text = "${msg.latencyMs.toInt()} ms",
                                        fontSize = 9.sp,
                                        fontFamily = FontFamily.Monospace,
                                        color = MatrixTextMuted
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // Pairing Modal Dialog
    if (showPairDialog) {
        AlertDialog(
            onDismissRequest = { showPairDialog = false },
            title = {
                Text(
                    "PAIR MATRIX COMPANION",
                    fontFamily = FontFamily.Monospace,
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Bold,
                    color = MatrixCyan
                )
            },
            text = {
                Column {
                    Text(
                        "Enter the Matrix Server address and pairing token generated by your Windows 11 PC.",
                        fontSize = 11.sp,
                        color = Color.LightGray
                    )
                    Spacer(modifier = Modifier.height(10.dp))

                    OutlinedTextField(
                        value = pairHostInput,
                        onValueChange = { pairHostInput = it },
                        label = { Text("Server Host (LAN or Tailscale IP:Port)", fontSize = 11.sp) },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth()
                    )

                    Spacer(modifier = Modifier.height(8.dp))

                    OutlinedTextField(
                        value = pairTokenInput,
                        onValueChange = { pairTokenInput = it },
                        label = { Text("Pairing Token (mtx_pair_...)", fontSize = 11.sp) },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth()
                    )

                    if (pairErrorMsg != null) {
                        Spacer(modifier = Modifier.height(6.dp))
                        Text(pairErrorMsg!!, color = MatrixRed, fontSize = 10.sp, fontFamily = FontFamily.Monospace)
                    }
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        isPairingLoading = true
                        pairErrorMsg = null
                        coroutineScope.launch {
                            val (success, msg) = apiClient.pairWithToken(pairTokenInput, pairHostInput)
                            isPairingLoading = false
                            if (success) {
                                showPairDialog = false
                                pairTokenInput = ""
                            } else {
                                pairErrorMsg = msg
                            }
                        }
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = MatrixCyan)
                ) {
                    Text(if (isPairingLoading) "Pairing..." else "Pair Now", color = Color.Black)
                }
            },
            dismissButton = {
                TextButton(onClick = { showPairDialog = false }) {
                    Text("Cancel", color = Color.Gray)
                }
            },
            containerColor = MatrixCard
        )
    }
}

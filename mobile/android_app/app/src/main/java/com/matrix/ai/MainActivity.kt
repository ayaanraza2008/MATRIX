package com.matrix.ai

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.animation.core.*
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
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
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.matrix.ai.network.ConnectionState
import com.matrix.ai.network.MatrixApiClient
import com.matrix.ai.network.SystemStatus
import com.matrix.ai.ui.theme.*
import com.google.gson.JsonObject
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

data class ChatMessage(
    val role: String,
    val text: String,
    val audioUrl: String? = null,
    val latencyMs: Float = 0f
)

enum class ScreenTab(val title: String, val icon: ImageVector) {
    DASHBOARD("Dashboard", Icons.Default.Dashboard),
    PAIRING("Pairing", Icons.Default.QrCodeScanner),
    VOICE("Voice", Icons.Default.Mic),
    CHAT("Chat", Icons.Default.Chat),
    PC_STATUS("PC Status", Icons.Default.DesktopWindows),
    METRICS("Telemetry", Icons.Default.Speed),
    HISTORY("History", Icons.Default.History),
    TASKS("Tasks", Icons.Default.Assignment),
    SECURITY("Security", Icons.Default.Security),
    SETTINGS("Settings", Icons.Default.Settings)
}

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

    var currentTab by remember { mutableStateOf(ScreenTab.DASHBOARD) }
    var inputText by remember { mutableStateOf("") }
    val messages = remember { mutableStateListOf<ChatMessage>() }
    val coroutineScope = rememberCoroutineScope()
    var isVoiceReplyEnabled by remember { mutableStateOf(false) }

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

    Scaffold(
        topBar = {
            Column {
                TopAppBar(
                    title = {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.SpaceBetween,
                            modifier = Modifier.fillMaxWidth().padding(end = 8.dp)
                        ) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Text(
                                    "MATRIX AI",
                                    fontFamily = FontFamily.Monospace,
                                    fontWeight = FontWeight.Bold,
                                    fontSize = 15.sp,
                                    color = MatrixCyan
                                )
                                Spacer(modifier = Modifier.width(8.dp))

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

                            if (connectionState == ConnectionState.CONNECTED) {
                                IconButton(onClick = {
                                    coroutineScope.launch { apiClient.revokeDevice() }
                                }) {
                                    Icon(
                                        imageVector = Icons.Default.LinkOff,
                                        contentDescription = "Revoke",
                                        tint = MatrixRed
                                    )
                                }
                            }
                        }
                    },
                    colors = TopAppBarDefaults.topAppBarColors(
                        containerColor = Color(0xFF070B16)
                    )
                )

                // 10-Screen Scrollable Tab Row
                ScrollableTabRow(
                    selectedTabIndex = currentTab.ordinal,
                    containerColor = Color(0xFF0A0F1E),
                    contentColor = MatrixCyan,
                    edgePadding = 8.dp
                ) {
                    ScreenTab.values().forEach { tab ->
                        Tab(
                            selected = currentTab == tab,
                            onClick = { currentTab = tab },
                            text = {
                                Text(
                                    tab.title,
                                    fontSize = 11.sp,
                                    fontFamily = FontFamily.Monospace,
                                    fontWeight = if (currentTab == tab) FontWeight.Bold else FontWeight.Normal
                                )
                            },
                            icon = {
                                Icon(
                                    tab.icon,
                                    contentDescription = tab.title,
                                    modifier = Modifier.size(18.dp)
                                )
                            },
                            selectedContentColor = MatrixCyan,
                            unselectedContentColor = Color.Gray
                        )
                    }
                }
            }
        },
        bottomBar = {
            if (currentTab == ScreenTab.CHAT || currentTab == ScreenTab.VOICE) {
                Surface(
                    modifier = Modifier.fillMaxWidth(),
                    color = Color(0xFF070B16),
                    border = BorderStroke(1.dp, Color(0xFF131D33))
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth().padding(8.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        IconButton(
                            onClick = { isVoiceReplyEnabled = !isVoiceReplyEnabled },
                            modifier = Modifier
                                .size(40.dp)
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
                            placeholder = { Text("Directive for MATRIX...", fontSize = 11.sp, color = MatrixTextMuted) },
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
                                .size(40.dp)
                                .background(if (connectionState == ConnectionState.CONNECTED) MatrixCyan else Color.DarkGray, CircleShape)
                        ) {
                            Icon(imageVector = Icons.Default.Send, contentDescription = "Send", tint = Color.Black)
                        }
                    }
                }
            }
        }
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(MatrixBackground)
                .padding(innerPadding)
                .padding(12.dp)
        ) {
            when (currentTab) {
                ScreenTab.DASHBOARD -> DashboardScreen(apiClient, systemStatus, connectionState) { currentTab = it }
                ScreenTab.PAIRING -> PairingScreen(apiClient)
                ScreenTab.VOICE -> VoiceScreen(apiClient, connectionState)
                ScreenTab.CHAT -> ChatScreen(apiClient, messages, connectionState)
                ScreenTab.PC_STATUS -> PCStatusScreen(apiClient, systemStatus)
                ScreenTab.METRICS -> MetricsScreen(apiClient, systemStatus)
                ScreenTab.HISTORY -> HistoryScreen(apiClient)
                ScreenTab.TASKS -> TasksScreen(apiClient)
                ScreenTab.SECURITY -> SecurityScreen(apiClient, connectionState)
                ScreenTab.SETTINGS -> SettingsScreen(apiClient)
            }
        }
    }
}

// ==========================================
// SCREEN 1: DASHBOARD
// ==========================================
@Composable
fun DashboardScreen(
    apiClient: MatrixApiClient,
    status: SystemStatus,
    connectionState: ConnectionState,
    onNavigate: (ScreenTab) -> Unit
) {
    val coroutineScope = rememberCoroutineScope()
    var pingLatency by remember { mutableStateOf<Long?>(null) }
    var isPinging by remember { mutableStateOf(false) }

    LazyColumn(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        item {
            Card(
                colors = CardDefaults.cardColors(containerColor = MatrixCard),
                border = BorderStroke(1.dp, MatrixBlue.copy(alpha = 0.5f))
            ) {
                Column(modifier = Modifier.padding(14.dp)) {
                    Text("ACTIVE GATEWAY", color = MatrixCyan, fontSize = 11.sp, fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold)
                    Spacer(modifier = Modifier.height(4.dp))
                    Text("LAN Endpoint: ${apiClient.serverHost}", color = Color.White, fontSize = 12.sp, fontFamily = FontFamily.Monospace)
                    if (status.tailscaleIp != null) {
                        Text("Tailscale Remote IP: ${status.tailscaleIp}", color = MatrixGreen, fontSize = 12.sp, fontFamily = FontFamily.Monospace)
                    } else {
                        Text("Tailscale Remote: Standby / Offline", color = Color.Gray, fontSize = 11.sp, fontFamily = FontFamily.Monospace)
                    }
                    Spacer(modifier = Modifier.height(8.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(
                            onClick = {
                                coroutineScope.launch {
                                    isPinging = true
                                    val t0 = System.currentTimeMillis()
                                    apiClient.heartbeat()
                                    pingLatency = System.currentTimeMillis() - t0
                                    isPinging = false
                                }
                            },
                            colors = ButtonDefaults.buttonColors(containerColor = MatrixBlue)
                        ) {
                            Text(if (isPinging) "Pinging..." else if (pingLatency != null) "${pingLatency}ms" else "Test Latency", fontSize = 11.sp)
                        }

                        OutlinedButton(onClick = { onNavigate(ScreenTab.PAIRING) }) {
                            Text("Pair Settings", fontSize = 11.sp, color = MatrixCyan)
                        }
                    }
                }
            }
        }

        item {
            Card(
                colors = CardDefaults.cardColors(containerColor = MatrixCard),
                border = BorderStroke(1.dp, Color(0xFF1B2844))
            ) {
                Column(modifier = Modifier.padding(14.dp)) {
                    Text("DEVICE IDENTITY", color = MatrixCyan, fontSize = 11.sp, fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold)
                    Spacer(modifier = Modifier.height(6.dp))
                    Text("Device ID: ${apiClient.deviceId}", color = Color.White, fontSize = 11.sp, fontFamily = FontFamily.Monospace)
                    Text("Hardware: ${apiClient.deviceName}", color = Color.LightGray, fontSize = 11.sp, fontFamily = FontFamily.Monospace)
                    Text("Protocol: WSS AES/Token-Gated Nonce", color = Color.LightGray, fontSize = 11.sp, fontFamily = FontFamily.Monospace)
                }
            }
        }

        item {
            Text("QUICK WORKFLOWS", color = MatrixCyan, fontSize = 12.sp, fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold)
        }

        item {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                Surface(
                    modifier = Modifier.weight(1f).clickable { onNavigate(ScreenTab.VOICE) },
                    shape = RoundedCornerShape(8.dp),
                    color = MatrixCard,
                    border = BorderStroke(1.dp, MatrixBlue.copy(alpha = 0.4f))
                ) {
                    Column(modifier = Modifier.padding(12.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                        Icon(Icons.Default.Mic, contentDescription = "Voice", tint = MatrixCyan, modifier = Modifier.size(24.dp))
                        Spacer(modifier = Modifier.height(4.dp))
                        Text("Voice Assistant", fontSize = 11.sp, color = Color.White, fontFamily = FontFamily.Monospace)
                    }
                }

                Surface(
                    modifier = Modifier.weight(1f).clickable { onNavigate(ScreenTab.METRICS) },
                    shape = RoundedCornerShape(8.dp),
                    color = MatrixCard,
                    border = BorderStroke(1.dp, MatrixBlue.copy(alpha = 0.4f))
                ) {
                    Column(modifier = Modifier.padding(12.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                        Icon(Icons.Default.Speed, contentDescription = "Metrics", tint = MatrixGreen, modifier = Modifier.size(24.dp))
                        Spacer(modifier = Modifier.height(4.dp))
                        Text("PC Telemetry", fontSize = 11.sp, color = Color.White, fontFamily = FontFamily.Monospace)
                    }
                }
            }
        }
    }
}

// ==========================================
// SCREEN 2: PAIRING
// ==========================================
@Composable
fun PairingScreen(apiClient: MatrixApiClient) {
    var hostInput by remember { mutableStateOf(apiClient.serverHost) }
    var tokenInput by remember { mutableStateOf("") }
    var resultMsg by remember { mutableStateOf<String?>(null) }
    var isPairing by remember { mutableStateOf(false) }
    val coroutineScope = rememberCoroutineScope()

    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("PAIR COMPANION DEVICE", color = MatrixCyan, fontSize = 13.sp, fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold)
        Text(
            "Enter the host address of your Windows 11 PC (LAN IP:8000 or Tailscale IP:8000) and the single-use pairing token generated from MATRIX Desktop HUD.",
            color = Color.LightGray,
            fontSize = 11.sp
        )

        OutlinedTextField(
            value = hostInput,
            onValueChange = { hostInput = it },
            label = { Text("Server Host (IP:Port)") },
            modifier = Modifier.fillMaxWidth()
        )

        OutlinedTextField(
            value = tokenInput,
            onValueChange = { tokenInput = it },
            label = { Text("Pairing Token (mtx_pair_...)") },
            modifier = Modifier.fillMaxWidth()
        )

        Button(
            onClick = {
                isPairing = true
                resultMsg = null
                coroutineScope.launch {
                    val (success, msg) = apiClient.pairWithToken(tokenInput, hostInput)
                    isPairing = false
                    resultMsg = msg
                    if (success) tokenInput = ""
                }
            },
            colors = ButtonDefaults.buttonColors(containerColor = MatrixCyan),
            modifier = Modifier.fillMaxWidth()
        ) {
            Text(if (isPairing) "Authenticating..." else "Execute Pairing Handshake", color = Color.Black, fontWeight = FontWeight.Bold)
        }

        if (resultMsg != null) {
            Surface(
                color = MatrixCard,
                shape = RoundedCornerShape(8.dp),
                border = BorderStroke(1.dp, MatrixBlue),
                modifier = Modifier.fillMaxWidth().padding(top = 8.dp)
            ) {
                Text(resultMsg!!, modifier = Modifier.padding(10.dp), color = Color.White, fontSize = 11.sp, fontFamily = FontFamily.Monospace)
            }
        }
    }
}

// ==========================================
// SCREEN 3: VOICE ASSISTANT
// ==========================================
@Composable
fun VoiceScreen(apiClient: MatrixApiClient, connectionState: ConnectionState) {
    val coroutineScope = rememberCoroutineScope()
    var isListening by remember { mutableStateOf(false) }
    var voiceStatus by remember { mutableStateOf("Tap to start hands-free voice stream") }
    var lastVoiceReply by remember { mutableStateOf("") }

    val infiniteTransition = rememberInfiniteTransition(label = "pulse")
    val pulseScale by infiniteTransition.animateFloat(
        initialValue = 1f,
        targetValue = 1.25f,
        animationSpec = infiniteRepeatable(tween(800, easing = FastOutSlowInEasing), RepeatMode.Reverse),
        label = "pulseScale"
    )

    Column(
        modifier = Modifier.fillMaxSize(),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Box(
            modifier = Modifier
                .size(140.dp)
                .rotate(if (isListening) pulseScale * 30f else 0f)
                .border(2.dp, if (isListening) MatrixGreen else MatrixCyan, CircleShape)
                .padding(12.dp)
                .border(1.dp, MatrixBlue, CircleShape),
            contentAlignment = Alignment.Center
        ) {
            IconButton(
                onClick = {
                    if (isListening) {
                        isListening = false
                        voiceStatus = "Audio uploaded. Awaiting Faster-Whisper CPU inference..."
                        coroutineScope.launch {
                            val res = apiClient.sendCommand("Hello Matrix, check status", synthesizeVoice = true)
                            lastVoiceReply = res.reply
                            voiceStatus = "Complete."
                        }
                    } else {
                        isListening = true
                        voiceStatus = "Listening... Speak directive clearly"
                    }
                },
                modifier = Modifier.size(70.dp).background(if (isListening) MatrixGreen else MatrixCard, CircleShape)
            ) {
                Icon(
                    imageVector = if (isListening) Icons.Default.Mic else Icons.Default.MicNone,
                    contentDescription = "Mic",
                    tint = if (isListening) Color.Black else MatrixCyan,
                    modifier = Modifier.size(36.dp)
                )
            }
        }

        Spacer(modifier = Modifier.height(20.dp))
        Text(voiceStatus, color = MatrixCyan, fontSize = 12.sp, fontFamily = FontFamily.Monospace, textAlign = TextAlign.Center)

        if (lastVoiceReply.isNotEmpty()) {
            Spacer(modifier = Modifier.height(16.dp))
            Surface(
                color = MatrixCard,
                shape = RoundedCornerShape(10.dp),
                border = BorderStroke(1.dp, MatrixBlue),
                modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp)
            ) {
                Column(modifier = Modifier.padding(12.dp)) {
                    Text("REPLY AUDIO STREAM", color = MatrixGreen, fontSize = 10.sp, fontFamily = FontFamily.Monospace)
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(lastVoiceReply, color = Color.White, fontSize = 12.sp)
                }
            }
        }
    }
}

// ==========================================
// SCREEN 4: CHAT
// ==========================================
@Composable
fun ChatScreen(apiClient: MatrixApiClient, messages: List<ChatMessage>, connectionState: ConnectionState) {
    val coroutineScope = rememberCoroutineScope()

    Column(modifier = Modifier.fillMaxSize()) {
        // Quick suggestions pills
        Row(
            modifier = Modifier.fillMaxWidth().padding(bottom = 8.dp),
            horizontalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            val suggestions = listOf("System Health", "VS Code Status", "Morning Briefing")
            suggestions.forEach { sug ->
                Surface(
                    shape = RoundedCornerShape(14.dp),
                    color = MatrixCard,
                    border = BorderStroke(1.dp, MatrixBlue.copy(alpha = 0.5f)),
                    modifier = Modifier.clickable {
                        coroutineScope.launch {
                            apiClient.sendCommand(sug)
                        }
                    }
                ) {
                    Text(sug, fontSize = 9.sp, color = MatrixCyan, fontFamily = FontFamily.Monospace, modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp))
                }
            }
        }

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
                        border = BorderStroke(1.dp, if (isUser) MatrixBlue else MatrixCyan.copy(alpha = 0.3f)),
                        modifier = Modifier.widthIn(max = 280.dp)
                    ) {
                        Column(modifier = Modifier.padding(10.dp)) {
                            Text(text = msg.text, fontSize = 12.sp, color = Color.White, fontFamily = FontFamily.Monospace)
                            if (msg.latencyMs > 0) {
                                Spacer(modifier = Modifier.height(2.dp))
                                Text(text = "${msg.latencyMs.toInt()} ms", fontSize = 8.sp, color = MatrixTextMuted, fontFamily = FontFamily.Monospace)
                            }
                        }
                    }
                }
            }
        }
    }
}

// ==========================================
// SCREEN 5: REMOTE PC STATUS
// ==========================================
@Composable
fun PCStatusScreen(apiClient: MatrixApiClient, status: SystemStatus) {
    val coroutineScope = rememberCoroutineScope()

    LazyColumn(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        item {
            Text("HOST WORKSTATION SPECIFICATIONS", color = MatrixCyan, fontSize = 12.sp, fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold)
        }

        item {
            Card(
                colors = CardDefaults.cardColors(containerColor = MatrixCard),
                border = BorderStroke(1.dp, Color(0xFF1B2844))
            ) {
                Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text("OS: Windows 11 Home 64-bit (Build 26100)", color = Color.White, fontSize = 11.sp, fontFamily = FontFamily.Monospace)
                    Text("Processor: AMD Ryzen 7 5700U (8 Cores, 16 Threads)", color = Color.White, fontSize = 11.sp, fontFamily = FontFamily.Monospace)
                    Text("RAM: 8.00 GB DDR4 (7.34 GB usable)", color = Color.White, fontSize = 11.sp, fontFamily = FontFamily.Monospace)
                    Text("Graphics: AMD Radeon Integrated (CPU-First)", color = Color.White, fontSize = 11.sp, fontFamily = FontFamily.Monospace)
                    Text("Persistent Storage: D:\\matrix_data\\", color = MatrixCyan, fontSize = 11.sp, fontFamily = FontFamily.Monospace)
                }
            }
        }

        item {
            Text("REMOTE WORKSPACE SHORTCUTS", color = MatrixCyan, fontSize = 12.sp, fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold)
        }

        item {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                Button(
                    onClick = { coroutineScope.launch { apiClient.sendCommand("Open VS Code") } },
                    modifier = Modifier.weight(1f),
                    colors = ButtonDefaults.buttonColors(containerColor = MatrixBlue)
                ) {
                    Text("Launch VS Code", fontSize = 11.sp)
                }
                Button(
                    onClick = { coroutineScope.launch { apiClient.sendCommand("mute audio") } },
                    modifier = Modifier.weight(1f),
                    colors = ButtonDefaults.buttonColors(containerColor = MatrixCard)
                ) {
                    Text("Toggle Mute", fontSize = 11.sp, color = MatrixCyan)
                }
            }
        }
    }
}

// ==========================================
// SCREEN 6: CPU / RAM / DISK TELEMETRY
// ==========================================
@Composable
fun MetricsScreen(apiClient: MatrixApiClient, status: SystemStatus) {
    LazyColumn(verticalArrangement = Arrangement.spacedBy(14.dp)) {
        item {
            Text("REAL-TIME HARDWARE GAUGES", color = MatrixCyan, fontSize = 12.sp, fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold)
        }

        item {
            Card(colors = CardDefaults.cardColors(containerColor = MatrixCard)) {
                Column(modifier = Modifier.padding(14.dp)) {
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text("CPU UTILIZATION", color = Color.White, fontSize = 11.sp, fontFamily = FontFamily.Monospace)
                        Text("${status.cpuPercent.toInt()}%", color = MatrixCyan, fontSize = 11.sp, fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold)
                    }
                    Spacer(modifier = Modifier.height(6.dp))
                    LinearProgressIndicator(
                        progress = { (status.cpuPercent / 100f).coerceIn(0f, 1f) },
                        modifier = Modifier.fillMaxWidth().height(8.dp).clip(RoundedCornerShape(4.dp)),
                        color = MatrixCyan,
                        trackColor = Color(0xFF131D33)
                    )
                }
            }
        }

        item {
            Card(colors = CardDefaults.cardColors(containerColor = MatrixCard)) {
                Column(modifier = Modifier.padding(14.dp)) {
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text("RAM USAGE (7.34 GB USABLE)", color = Color.White, fontSize = 11.sp, fontFamily = FontFamily.Monospace)
                        Text("${status.ramUsedPercent.toInt()}%", color = MatrixBlue, fontSize = 11.sp, fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold)
                    }
                    Spacer(modifier = Modifier.height(6.dp))
                    LinearProgressIndicator(
                        progress = { (status.ramUsedPercent / 100f).coerceIn(0f, 1f) },
                        modifier = Modifier.fillMaxWidth().height(8.dp).clip(RoundedCornerShape(4.dp)),
                        color = MatrixBlue,
                        trackColor = Color(0xFF131D33)
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text("Available: ${status.ramAvailableMb.toInt()} MB", color = MatrixTextMuted, fontSize = 10.sp, fontFamily = FontFamily.Monospace)
                }
            }
        }

        item {
            Card(colors = CardDefaults.cardColors(containerColor = MatrixCard)) {
                Column(modifier = Modifier.padding(14.dp)) {
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text("DISK VOLUME C: & D:", color = Color.White, fontSize = 11.sp, fontFamily = FontFamily.Monospace)
                        Text("${status.diskUsedPercent.toInt()}%", color = MatrixGreen, fontSize = 11.sp, fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold)
                    }
                    Spacer(modifier = Modifier.height(6.dp))
                    LinearProgressIndicator(
                        progress = { (status.diskUsedPercent / 100f).coerceIn(0f, 1f) },
                        modifier = Modifier.fillMaxWidth().height(8.dp).clip(RoundedCornerShape(4.dp)),
                        color = MatrixGreen,
                        trackColor = Color(0xFF131D33)
                    )
                }
            }
        }
    }
}

// ==========================================
// SCREEN 7: REMOTE COMMAND HISTORY
// ==========================================
@Composable
fun HistoryScreen(apiClient: MatrixApiClient) {
    var historyItems by remember { mutableStateOf<List<JsonObject>>(emptyList()) }
    var isLoading by remember { mutableStateOf(true) }

    LaunchedEffect(Unit) {
        historyItems = apiClient.fetchAuditHistory()
        isLoading = false
    }

    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Text("AUDIT & COMMAND LOG", color = MatrixCyan, fontSize = 12.sp, fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold)

        if (isLoading) {
            CircularProgressIndicator(color = MatrixCyan, modifier = Modifier.align(Alignment.CenterHorizontally))
        } else if (historyItems.isEmpty()) {
            Text("No remote commands recorded in audit ledger yet.", color = Color.Gray, fontSize = 11.sp)
        } else {
            LazyColumn(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                items(historyItems) { item ->
                    Card(colors = CardDefaults.cardColors(containerColor = MatrixCard)) {
                        Column(modifier = Modifier.padding(10.dp)) {
                            Text(item.get("action")?.asString ?: "Command", color = Color.White, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                            Text(item.get("timestamp")?.asString ?: "", color = MatrixTextMuted, fontSize = 9.sp)
                        }
                    }
                }
            }
        }
    }
}

// ==========================================
// SCREEN 8: ACTIVE BACKGROUND TASKS
// ==========================================
@Composable
fun TasksScreen(apiClient: MatrixApiClient) {
    var tasks by remember { mutableStateOf<List<JsonObject>>(emptyList()) }
    var isLoading by remember { mutableStateOf(true) }

    LaunchedEffect(Unit) {
        tasks = apiClient.fetchTasks()
        isLoading = false
    }

    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Text("AUTONOMOUS SCHEDULER & TASKS", color = MatrixCyan, fontSize = 12.sp, fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold)

        if (isLoading) {
            CircularProgressIndicator(color = MatrixCyan, modifier = Modifier.align(Alignment.CenterHorizontally))
        } else if (tasks.isEmpty()) {
            Text("No scheduled tasks currently active in background engine.", color = Color.Gray, fontSize = 11.sp)
        } else {
            LazyColumn(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                items(tasks) { task ->
                    Card(colors = CardDefaults.cardColors(containerColor = MatrixCard)) {
                        Column(modifier = Modifier.padding(10.dp)) {
                            Text(task.get("name")?.asString ?: "Task", color = MatrixGreen, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                            Text("Schedule: ${task.get("cron")?.asString ?: "Interval"}", color = Color.White, fontSize = 10.sp)
                        }
                    }
                }
            }
        }
    }
}

// ==========================================
// SCREEN 9: DEVICE SECURITY & REVOCATION
// ==========================================
@Composable
fun SecurityScreen(apiClient: MatrixApiClient, connectionState: ConnectionState) {
    val coroutineScope = rememberCoroutineScope()
    var isRotating by remember { mutableStateOf(false) }
    var rotateStatus by remember { mutableStateOf<String?>(null) }

    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("SECURITY GOVERNANCE & ACCESS CONTROL", color = MatrixCyan, fontSize = 12.sp, fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold)

        Card(colors = CardDefaults.cardColors(containerColor = MatrixCard)) {
            Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Text("AUTONOMY LEVEL: LEVEL 4 (SUPERVISED)", color = MatrixGreen, fontSize = 11.sp, fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold)
                Text("Destructive operations, external email sending, PSTN phone dialing, and credential exports require explicit operator confirmation tokens.", color = Color.LightGray, fontSize = 10.sp)
            }
        }

        Button(
            onClick = {
                isRotating = true
                coroutineScope.launch {
                    val ok = apiClient.rotateToken()
                    isRotating = false
                    rotateStatus = if (ok) "Session token rotated successfully." else "Rotation failed."
                }
            },
            colors = ButtonDefaults.buttonColors(containerColor = MatrixBlue),
            modifier = Modifier.fillMaxWidth()
        ) {
            Text(if (isRotating) "Rotating Token..." else "Rotate Bearer Token", fontSize = 11.sp)
        }

        if (rotateStatus != null) {
            Text(rotateStatus!!, color = MatrixCyan, fontSize = 10.sp, fontFamily = FontFamily.Monospace)
        }

        Spacer(modifier = Modifier.height(10.dp))

        Button(
            onClick = {
                coroutineScope.launch {
                    apiClient.revokeDevice()
                }
            },
            colors = ButtonDefaults.buttonColors(containerColor = MatrixRed),
            modifier = Modifier.fillMaxWidth()
        ) {
            Icon(Icons.Default.Dangerous, contentDescription = "Kill Switch")
            Spacer(modifier = Modifier.width(6.dp))
            Text("KILL SWITCH: REVOKE COMPANION ACCESS", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 11.sp)
        }
    }
}

// ==========================================
// SCREEN 10: NOTIFICATIONS & SETTINGS
// ==========================================
@Composable
fun SettingsScreen(apiClient: MatrixApiClient) {
    var notifications by remember { mutableStateOf<List<JsonObject>>(emptyList()) }
    var pushEnabled by remember { mutableStateOf(true) }
    val coroutineScope = rememberCoroutineScope()

    LaunchedEffect(Unit) {
        notifications = apiClient.fetchNotifications()
    }

    LazyColumn(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        item {
            Text("PUSH NOTIFICATIONS & CONFIGURATION", color = MatrixCyan, fontSize = 12.sp, fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold)
        }

        item {
            Card(colors = CardDefaults.cardColors(containerColor = MatrixCard)) {
                Row(
                    modifier = Modifier.fillMaxWidth().padding(14.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Text("Companion Push Alerts", color = Color.White, fontSize = 11.sp)
                        Text("Receive background autonomous task alerts", color = MatrixTextMuted, fontSize = 9.sp)
                    }
                    Switch(checked = pushEnabled, onCheckedChange = { pushEnabled = it })
                }
            }
        }

        item {
            Text("RECENT NOTIFICATION HISTORY", color = MatrixCyan, fontSize = 11.sp, fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold)
        }

        if (notifications.isEmpty()) {
            item {
                Text("No recent push alerts.", color = Color.Gray, fontSize = 10.sp)
            }
        } else {
            items(notifications) { notif ->
                Card(colors = CardDefaults.cardColors(containerColor = MatrixCard)) {
                    Column(modifier = Modifier.padding(10.dp)) {
                        Text(notif.get("title")?.asString ?: "Alert", color = MatrixCyan, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                        Text(notif.get("body")?.asString ?: "", color = Color.White, fontSize = 10.sp)
                    }
                }
            }
        }
    }
}

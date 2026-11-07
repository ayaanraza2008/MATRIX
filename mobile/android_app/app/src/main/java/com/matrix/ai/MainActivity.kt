package com.matrix.ai

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.Send
import androidx.compose.material.icons.filled.Wifi
import androidx.compose.material.icons.filled.WifiOff
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.matrix.ai.network.MatrixApiClient
import com.matrix.ai.ui.theme.*
import kotlinx.coroutines.launch

data class ChatMessage(val role: String, val text: String)

class MainActivity : ComponentActivity() {
    private val apiClient = MatrixApiClient("10.0.2.2:8000")

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
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
    var isConnected by remember { mutableStateOf(false) }
    var inputText by remember { mutableStateOf("") }
    val messages = remember { mutableStateListOf<ChatMessage>() }
    val coroutineScope = rememberCoroutineScope()
    var isListening by remember { mutableStateOf(false) }

    // Check PC health on startup
    LaunchedEffect(Unit) {
        isConnected = apiClient.checkHealth()
        if (isConnected) {
            messages.add(ChatMessage("assistant", "MATRIX Core Connected. Mobile Bridge Online."))
        } else {
            messages.add(ChatMessage("assistant", "PC Offline. Awaiting connection to MATRIX server."))
        }
    }

    // Hologram rotation animation
    val infiniteTransition = rememberInfiniteTransition(label = "rotation")
    val rotation by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 360f,
        animationSpec = infiniteRepeatable(
            animation = tween(12000, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "coreRotation"
    )

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(
                            "MATRIX MOBILE",
                            fontFamily = FontFamily.Monospace,
                            fontSize = 16.sp,
                            color = MatrixCyan
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Icon(
                            imageVector = if (isConnected) Icons.Default.Wifi else Icons.Default.WifiOff,
                            contentDescription = "Status",
                            tint = if (isConnected) MatrixGreen else MatrixRed,
                            modifier = Modifier.size(16.dp)
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = Color(0xFF070B16)
                )
            )
        },
        bottomBar = {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(Color(0xFF070B16))
                    .padding(8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                IconButton(
                    onClick = { isListening = !isListening },
                    modifier = Modifier
                        .size(44.dp)
                        .background(if (isListening) MatrixGreen else MatrixCard, CircleShape)
                ) {
                    Icon(
                        imageVector = Icons.Default.Mic,
                        contentDescription = "Mic",
                        tint = if (isListening) Color.Black else MatrixCyan
                    )
                }

                Spacer(modifier = Modifier.width(8.dp))

                TextField(
                    value = inputText,
                    onValueChange = { inputText = it },
                    placeholder = { Text("Command MATRIX...", fontSize = 13.sp, color = MatrixTextMuted) },
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
                                val reply = apiClient.sendCommand("sess_mobile_sync", text)
                                messages.add(ChatMessage("assistant", reply))
                            }
                        }
                    },
                    modifier = Modifier
                        .size(44.dp)
                        .background(MatrixCyan, CircleShape)
                ) {
                    Icon(imageVector = Icons.Default.Send, contentDescription = "Send", tint = Color.Black)
                }
            }
        }
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .background(MatrixBackground)
                .padding(innerPadding)
                .padding(16.dp),
            horizontalAlignment = Alignment.CenterVertically
        ) {
            // Central Holographic Ring
            Box(
                modifier = Modifier
                    .size(120.dp)
                    .rotate(rotation)
                    .border(2.dp, MatrixCyan.copy(alpha = 0.5f), CircleShape)
                    .padding(8.dp)
                    .border(1.dp, MatrixBlue.copy(alpha = 0.8f), CircleShape),
                contentAlignment = Alignment.Center
            ) {
                Box(
                    modifier = Modifier
                        .size(16.dp)
                        .background(MatrixCyan, CircleShape)
                )
            }

            Text(
                text = if (isConnected) "CORE LINK: NOMINAL" else "DISCONNECTED",
                fontFamily = FontFamily.Monospace,
                fontSize = 11.sp,
                color = if (isConnected) MatrixGreen else MatrixRed,
                modifier = Modifier.padding(top = 8.dp, bottom = 16.dp)
            )

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
                            border = ButtonDefaults.outlinedButtonBorder.copy(
                                brush = androidx.compose.ui.graphics.SolidColor(
                                    if (isUser) MatrixBlue else MatrixCyan.copy(alpha = 0.3f)
                                )
                            ),
                            modifier = Modifier.widthIn(max = 280.dp)
                        ) {
                            Text(
                                text = msg.text,
                                modifier = Modifier.padding(12.dp),
                                fontSize = 12.sp,
                                fontFamily = FontFamily.Monospace,
                                color = Color.White
                            )
                        }
                    }
                }
            }
        }
    }
}

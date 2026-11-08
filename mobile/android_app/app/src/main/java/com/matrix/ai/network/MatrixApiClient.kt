package com.matrix.ai.network

import android.content.Context
import android.content.SharedPreferences
import android.os.Build
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import com.google.gson.Gson
import com.google.gson.JsonObject
import java.io.File
import java.io.IOException
import java.util.UUID
import java.util.concurrent.TimeUnit

enum class ConnectionState {
    CONNECTED,
    DISCONNECTED,
    RECONNECTING,
    REVOKED
}

data class SystemStatus(
    val cpuPercent: Float = 0f,
    val ramUsedPercent: Float = 0f,
    val ramAvailableMb: Float = 0f,
    val ramTotalMb: Float = 0f,
    val diskUsedPercent: Float = 0f,
    val systemStatus: String = "NOMINAL",
    val lanIp: String = "",
    val tailscaleIp: String? = null
)

data class CommandResult(
    val success: Boolean,
    val reply: String,
    val audioUrl: String? = null,
    val planStatus: String? = null,
    val latencyMs: Float = 0f,
    val error: String? = null
)

class MatrixApiClient(context: Context? = null) {
    private val prefs: SharedPreferences? = context?.getSharedPreferences("matrix_prefs", Context.MODE_PRIVATE)
    private val gson = Gson()
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    private val client = OkHttpClient.Builder()
        .connectTimeout(8, TimeUnit.SECONDS)
        .readTimeout(20, TimeUnit.SECONDS)
        .writeTimeout(20, TimeUnit.SECONDS)
        .build()

    var serverHost: String = prefs?.getString("server_host", "192.168.31.194:8000") ?: "192.168.31.194:8000"
        private set

    var authToken: String? = prefs?.getString("auth_token", null)
        private set

    val deviceId: String = prefs?.getString("device_id", null) ?: run {
        val newId = "android_" + UUID.randomUUID().toString().replace("-", "").take(12)
        prefs?.edit()?.putString("device_id", newId)?.apply()
        newId
    }

    val deviceName: String = "${Build.MANUFACTURER} ${Build.MODEL}".trim()

    private val _connectionState = MutableStateFlow(ConnectionState.DISCONNECTED)
    val connectionState: StateFlow<ConnectionState> = _connectionState.asStateFlow()

    private val _systemStatus = MutableStateFlow(SystemStatus())
    val systemStatus: StateFlow<SystemStatus> = _systemStatus.asStateFlow()

    private var webSocket: WebSocket? = null
    private var isManualDisconnect = false
    private var reconnectJob: Job? = null

    init {
        if (!authToken.isNullOrEmpty()) {
            scope.launch {
                checkHealthAndConnect()
            }
        }
    }

    fun updateServerConfig(host: String, token: String? = null) {
        serverHost = host.trim().removePrefix("http://").removePrefix("https://").removeSuffix("/")
        prefs?.edit()?.putString("server_host", serverHost)?.apply()
        if (token != null) {
            authToken = token.trim()
            prefs?.edit()?.putString("auth_token", authToken)?.apply()
        }
    }

    fun clearAuthentication() {
        authToken = null
        prefs?.edit()?.remove("auth_token")?.apply()
        _connectionState.value = ConnectionState.REVOKED
        webSocket?.close(1000, "Device unauthenticated")
        webSocket = null
    }

    suspend fun pairWithToken(pairingToken: String, host: String): Pair<Boolean, String> = withContext(Dispatchers.IO) {
        updateServerConfig(host)
        val payload = JsonObject().apply {
            addProperty("device_id", deviceId)
            addProperty("name", deviceName)
            addProperty("platform", "android")
            addProperty("pairing_token", pairingToken.trim())
        }

        val body = payload.toString().toRequestBody("application/json".toMediaType())
        val request = Request.Builder()
            .url("http://$serverHost/api/v1/devices/pair")
            .post(body)
            .build()

        try {
            client.newCall(request).execute().use { response ->
                val respBody = response.body?.string() ?: ""
                if (response.isSuccessful) {
                    val json = gson.fromJson(respBody, JsonObject::class.java)
                    val token = json.get("auth_token")?.asString
                    if (!token.isNullOrEmpty()) {
                        authToken = token
                        prefs?.edit()?.putString("auth_token", token)?.apply()
                        _connectionState.value = ConnectionState.CONNECTED
                        connectWebSocket()
                        Pair(true, "Paired successfully. Matrix Link Active.")
                    } else {
                        Pair(false, "Server did not return authentication token.")
                    }
                } else {
                    Pair(false, "Pairing rejected (HTTP ${response.code}): $respBody")
                }
            }
        } catch (e: Exception) {
            Pair(false, "Pairing connection failed: ${e.message}")
        }
    }

    suspend fun checkHealthAndConnect(): ConnectionState = withContext(Dispatchers.IO) {
        if (_connectionState.value == ConnectionState.REVOKED) return@withContext ConnectionState.REVOKED

        val request = Request.Builder()
            .url("http://$serverHost/api/v1/health")
            .build()

        try {
            client.newCall(request).execute().use { resp ->
                if (resp.isSuccessful) {
                    if (!authToken.isNullOrEmpty()) {
                        val authOk = heartbeat()
                        if (authOk) {
                            _connectionState.value = ConnectionState.CONNECTED
                            connectWebSocket()
                        } else {
                            _connectionState.value = ConnectionState.REVOKED
                        }
                    } else {
                        _connectionState.value = ConnectionState.DISCONNECTED
                    }
                } else {
                    _connectionState.value = ConnectionState.DISCONNECTED
                }
            }
        } catch (e: Exception) {
            _connectionState.value = ConnectionState.DISCONNECTED
        }

        _connectionState.value
    }

    suspend fun heartbeat(): Boolean = withContext(Dispatchers.IO) {
        val token = authToken ?: return@withContext false
        val request = Request.Builder()
            .url("http://$serverHost/api/v1/devices/heartbeat")
            .addHeader("Authorization", "Bearer $token")
            .post(ByteArray(0).toRequestBody(null))
            .build()

        try {
            client.newCall(request).execute().use { resp ->
                if (resp.code == 401) {
                    clearAuthentication()
                    return@withContext false
                }
                resp.isSuccessful
            }
        } catch (e: Exception) {
            false
        }
    }

    suspend fun fetchStatus(): Boolean = withContext(Dispatchers.IO) {
        val token = authToken ?: return@withContext false
        val request = Request.Builder()
            .url("http://$serverHost/api/v1/devices/status")
            .addHeader("Authorization", "Bearer $token")
            .get()
            .build()

        try {
            client.newCall(request).execute().use { resp ->
                if (resp.code == 401) {
                    clearAuthentication()
                    return@withContext false
                }
                if (resp.isSuccessful) {
                    val json = gson.fromJson(resp.body?.string(), JsonObject::class.java)
                    _systemStatus.value = SystemStatus(
                        cpuPercent = json.get("cpu_percent")?.asFloat ?: 0f,
                        ramUsedPercent = json.get("ram_used_percent")?.asFloat ?: 0f,
                        ramAvailableMb = json.get("ram_available_mb")?.asFloat ?: 0f,
                        ramTotalMb = json.get("ram_total_mb")?.asFloat ?: 0f,
                        diskUsedPercent = json.get("disk_used_percent")?.asFloat ?: 0f,
                        systemStatus = json.get("system_status")?.asString ?: "NOMINAL",
                        lanIp = json.get("lan_ip")?.asString ?: "",
                        tailscaleIp = if (json.has("tailscale_ip") && !json.get("tailscale_ip").isJsonNull) json.get("tailscale_ip").asString else null
                    )
                    true
                } else {
                    false
                }
            }
        } catch (e: Exception) {
            false
        }
    }

    suspend fun sendCommand(command: String, synthesizeVoice: Boolean = false): CommandResult = withContext(Dispatchers.IO) {
        val token = authToken
        if (token.isNullOrEmpty()) {
            return@withContext CommandResult(false, "Device not paired. Please pair first.", error = "NOT_PAIRED")
        }

        val payload = JsonObject().apply {
            addProperty("command", command)
            addProperty("session_id", "sess_companion_$deviceId")
            addProperty("synthesize_voice", synthesizeVoice)
        }

        val body = payload.toString().toRequestBody("application/json".toMediaType())
        val request = Request.Builder()
            .url("http://$serverHost/api/v1/devices/command")
            .addHeader("Authorization", "Bearer $token")
            .post(body)
            .build()

        try {
            client.newCall(request).execute().use { resp ->
                val respStr = resp.body?.string() ?: ""
                if (resp.code == 401) {
                    clearAuthentication()
                    return@withContext CommandResult(false, "Authorization revoked by host.", error = "REVOKED")
                }
                if (resp.isSuccessful) {
                    val json = gson.fromJson(respStr, JsonObject::class.java)
                    CommandResult(
                        success = true,
                        reply = json.get("reply")?.asString ?: "Command executed.",
                        audioUrl = if (json.has("audio_url") && !json.get("audio_url").isJsonNull) json.get("audio_url").asString else null,
                        planStatus = json.get("plan_status")?.asString,
                        latencyMs = json.get("latency_ms")?.asFloat ?: 0f
                    )
                } else {
                    CommandResult(false, "Error: HTTP ${resp.code}", error = respStr)
                }
            }
        } catch (e: Exception) {
            CommandResult(false, "Connection failed: ${e.message}", error = e.message)
        }
    }

    suspend fun sendVoiceAudio(audioFile: File): CommandResult = withContext(Dispatchers.IO) {
        val token = authToken
        if (token.isNullOrEmpty()) {
            return@withContext CommandResult(false, "Device not paired. Please pair first.", error = "NOT_PAIRED")
        }

        val fileBody = audioFile.asRequestBody("audio/wav".toMediaType())
        val multiBody = MultipartBody.Builder()
            .setType(MultipartBody.FORM)
            .addFormDataPart("file", audioFile.name, fileBody)
            .addFormDataPart("session_id", "sess_companion_voice_$deviceId")
            .build()

        val request = Request.Builder()
            .url("http://$serverHost/api/v1/devices/voice")
            .addHeader("Authorization", "Bearer $token")
            .post(multiBody)
            .build()

        try {
            client.newCall(request).execute().use { resp ->
                val respStr = resp.body?.string() ?: ""
                if (resp.code == 401) {
                    clearAuthentication()
                    return@withContext CommandResult(false, "Authorization revoked by host.", error = "REVOKED")
                }
                if (resp.isSuccessful) {
                    val json = gson.fromJson(respStr, JsonObject::class.java)
                    CommandResult(
                        success = true,
                        reply = json.get("reply_text")?.asString ?: "Audio processed.",
                        audioUrl = if (json.has("audio_url") && !json.get("audio_url").isJsonNull) json.get("audio_url").asString else null,
                        latencyMs = json.get("latency_ms")?.asFloat ?: 0f
                    )
                } else {
                    CommandResult(false, "Voice error: HTTP ${resp.code}", error = respStr)
                }
            }
        } catch (e: Exception) {
            CommandResult(false, "Voice upload failed: ${e.message}", error = e.message)
        }
    }

    suspend fun rotateToken(): Boolean = withContext(Dispatchers.IO) {
        val token = authToken ?: return@withContext false
        val request = Request.Builder()
            .url("http://$serverHost/api/v1/devices/rotate-token")
            .addHeader("Authorization", "Bearer $token")
            .post(ByteArray(0).toRequestBody(null))
            .build()

        try {
            client.newCall(request).execute().use { resp ->
                if (resp.isSuccessful) {
                    val json = gson.fromJson(resp.body?.string(), JsonObject::class.java)
                    val newToken = json.get("auth_token")?.asString
                    if (!newToken.isNullOrEmpty()) {
                        authToken = newToken
                        prefs?.edit()?.putString("auth_token", newToken)?.apply()
                        return@withContext true
                    }
                }
            }
        } catch (e: Exception) {
            // Rotation error
        }
        false
    }

    suspend fun revokeDevice(): Boolean = withContext(Dispatchers.IO) {
        val token = authToken ?: return@withContext false
        val request = Request.Builder()
            .url("http://$serverHost/api/v1/devices/$deviceId/revoke")
            .addHeader("Authorization", "Bearer $token")
            .post(ByteArray(0).toRequestBody(null))
            .build()

        try {
            client.newCall(request).execute().use { resp ->
                clearAuthentication()
                resp.isSuccessful
            }
        } catch (e: Exception) {
            clearAuthentication()
            false
        }
    }

    fun connectWebSocket(onMessage: ((String) -> Unit)? = null) {
        if (_connectionState.value == ConnectionState.REVOKED) return
        val token = authToken ?: return
        isManualDisconnect = false

        val wsUrl = "ws://$serverHost/ws/events?token=$token"
        val request = Request.Builder().url(wsUrl).build()

        webSocket?.close(1000, "Reconnecting")
        webSocket = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                _connectionState.value = ConnectionState.CONNECTED
                reconnectJob?.cancel()
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                onMessage?.invoke(text)
                try {
                    val json = gson.fromJson(text, JsonObject::class.java)
                    val type = json.get("type")?.asString
                    if (type == "device_revoked" || type == "all_devices_revoked") {
                        clearAuthentication()
                    } else if (type == "telemetry_update") {
                        val payload = json.getAsJsonObject("payload")
                        if (payload != null) {
                            _systemStatus.value = _systemStatus.value.copy(
                                cpuPercent = payload.get("cpu_percent")?.asFloat ?: 0f,
                                ramUsedPercent = payload.get("ram_percent")?.asFloat ?: 0f,
                                ramAvailableMb = payload.get("ram_available_mb")?.asFloat ?: 0f
                            )
                        }
                    }
                } catch (e: Exception) {
                    // Ignore malformed JSON
                }
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                if (response?.code == 4001 || response?.code == 401) {
                    clearAuthentication()
                } else if (!isManualDisconnect && _connectionState.value != ConnectionState.REVOKED) {
                    scheduleReconnect()
                }
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                if (code == 4001) {
                    clearAuthentication()
                } else if (!isManualDisconnect && _connectionState.value != ConnectionState.REVOKED) {
                    scheduleReconnect()
                }
            }
        })
    }

    private fun scheduleReconnect() {
        if (_connectionState.value == ConnectionState.REVOKED || isManualDisconnect) return
        _connectionState.value = ConnectionState.RECONNECTING

        reconnectJob?.cancel()
        reconnectJob = scope.launch {
            var delaySec = 2L
            while (_connectionState.value == ConnectionState.RECONNECTING) {
                delay(delaySec * 1000)
                val ok = heartbeat()
                if (ok) {
                    _connectionState.value = ConnectionState.CONNECTED
                    connectWebSocket()
                    break
                }
                delaySec = (delaySec * 2).coerceAtMost(16L)
            }
        }
    }

    fun disconnect() {
        isManualDisconnect = true
        reconnectJob?.cancel()
        webSocket?.close(1000, "Client disconnected")
        webSocket = null
        if (_connectionState.value != ConnectionState.REVOKED) {
            _connectionState.value = ConnectionState.DISCONNECTED
        }
    }
}

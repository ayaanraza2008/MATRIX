package com.matrix.ai.network

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import com.google.gson.Gson
import com.google.gson.JsonObject
import java.io.IOException

data class SystemHealth(
    val status: String,
    val app_name: String,
    val version: String
)

class MatrixApiClient(private val serverHost: String = "10.0.2.2:8000") {
    private val client = OkHttpClient()
    private val gson = Gson()
    private var webSocket: WebSocket? = null

    suspend fun checkHealth(): Boolean = withContext(Dispatchers.IO) {
        val request = Request.Builder()
            .url("http://$serverHost/api/v1/health")
            .build()

        try {
            client.newCall(request).execute().use { response ->
                response.isSuccessful
            }
        } catch (e: Exception) {
            false
        }
    }

    suspend fun sendCommand(sessionId: String, command: String): String = withContext(Dispatchers.IO) {
        val jsonPayload = JsonObject().apply {
            addProperty("role", "user")
            addProperty("content", command)
            addProperty("agent_name", "android")
        }

        val body = jsonPayload.toString().toRequestBody("application/json".toMediaType())
        val request = Request.Builder()
            .url("http://$serverHost/api/v1/sessions/$sessionId/interact")
            .post(body)
            .build()

        try {
            client.newCall(request).execute().use { response ->
                if (response.isSuccessful) {
                    val respJson = gson.fromJson(response.body?.string(), JsonObject::class.java)
                    respJson.get("reply")?.asString ?: "Command executed."
                } else {
                    "Error: HTTP ${response.code}"
                }
            }
        } catch (e: Exception) {
            "Connection failed: ${e.message}"
        }
    }

    fun connectWebSocket(onMessage: (String) -> Unit) {
        val request = Request.Builder()
            .url("ws://$serverHost/ws/events")
            .build()

        webSocket = client.newWebSocket(request, object : WebSocketListener() {
            override fun onMessage(webSocket: WebSocket, text: String) {
                onMessage(text)
            }
            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                // Reconnect loop handled by client
            }
        })
    }

    fun disconnect() {
        webSocket?.close(1000, "Normal closure")
    }
}

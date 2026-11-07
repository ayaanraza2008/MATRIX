package com.matrix.ai.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

val MatrixBackground = Color(0xFF05070E)
val MatrixCard = Color(0xFF0A0F1D)
val MatrixCyan = Color(0xFF00F0FF)
val MatrixBlue = Color(0xFF0066FF)
val MatrixGreen = Color(0xFF00FF9D)
val MatrixRed = Color(0xFFFF3366)
val MatrixTextMuted = Color(0xFF6B7A99)

private val DarkColorScheme = darkColorScheme(
    primary = MatrixCyan,
    secondary = MatrixBlue,
    background = MatrixBackground,
    surface = MatrixCard,
    onPrimary = Color.Black,
    onSecondary = Color.White,
    onBackground = Color(0xFFE2E8F0),
    onSurface = Color(0xFFE2E8F0)
)

@Composable
fun MatrixTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = DarkColorScheme,
        content = content
    )
}

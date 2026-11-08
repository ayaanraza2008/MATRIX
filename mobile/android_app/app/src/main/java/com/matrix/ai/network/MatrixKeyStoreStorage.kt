package com.matrix.ai.network

import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/**
 * Hardware-backed Android Keystore AES-256-GCM encryption provider.
 * Protects Matrix Bearer auth tokens and pairing secrets from plaintext extraction.
 */
object MatrixKeyStoreStorage {
    private const val ANDROID_KEYSTORE = "AndroidKeyStore"
    private const val KEY_ALIAS = "MatrixKeyStore_AuthTokenKey_v1"
    private const val CIPHER_TRANSFORMATION = "AES/GCM/NoPadding"
    private const val GCM_IV_LENGTH = 12
    private const val GCM_TAG_LENGTH = 128

    private fun getOrCreateSecretKey(): SecretKey? {
        return try {
            val keyStore = KeyStore.getInstance(ANDROID_KEYSTORE).apply { load(null) }
            if (keyStore.containsAlias(KEY_ALIAS)) {
                val entry = keyStore.getEntry(KEY_ALIAS, null) as? KeyStore.SecretKeyEntry
                entry?.secretKey
            } else {
                val keyGenerator = KeyGenerator.getInstance(
                    KeyProperties.KEY_ALGORITHM_AES,
                    ANDROID_KEYSTORE
                )
                val keyGenParameterSpec = KeyGenParameterSpec.Builder(
                    KEY_ALIAS,
                    KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT
                )
                    .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                    .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                    .setKeySize(256)
                    .build()
                keyGenerator.init(keyGenParameterSpec)
                keyGenerator.generateKey()
            }
        } catch (e: Throwable) {
            null
        }
    }

    fun encrypt(plainText: String?): String? {
        if (plainText.isNullOrEmpty()) return null
        return try {
            val key = getOrCreateSecretKey() ?: return plainText
            val cipher = Cipher.getInstance(CIPHER_TRANSFORMATION)
            cipher.init(Cipher.ENCRYPT_MODE, key)
            val iv = cipher.iv
            val encryptedBytes = cipher.doFinal(plainText.toByteArray(Charsets.UTF_8))
            val combined = ByteArray(iv.size + encryptedBytes.size)
            System.arraycopy(iv, 0, combined, 0, iv.size)
            System.arraycopy(encryptedBytes, 0, combined, iv.size, encryptedBytes.size)
            "KS_ENC:" + Base64.encodeToString(combined, Base64.NO_WRAP)
        } catch (e: Throwable) {
            plainText
        }
    }

    fun decrypt(cipherText: String?): String? {
        if (cipherText.isNullOrEmpty()) return null
        if (!cipherText.startsWith("KS_ENC:")) return cipherText
        return try {
            val rawBase64 = cipherText.removePrefix("KS_ENC:")
            val combined = Base64.decode(rawBase64, Base64.NO_WRAP)
            if (combined.size < GCM_IV_LENGTH) return cipherText
            val iv = ByteArray(GCM_IV_LENGTH)
            val encryptedBytes = ByteArray(combined.size - GCM_IV_LENGTH)
            System.arraycopy(combined, 0, iv, 0, GCM_IV_LENGTH)
            System.arraycopy(combined, GCM_IV_LENGTH, encryptedBytes, 0, encryptedBytes.size)

            val key = getOrCreateSecretKey() ?: return cipherText
            val cipher = Cipher.getInstance(CIPHER_TRANSFORMATION)
            val spec = GCMParameterSpec(GCM_TAG_LENGTH, iv)
            cipher.init(Cipher.DECRYPT_MODE, key, spec)
            val decryptedBytes = cipher.doFinal(encryptedBytes)
            String(decryptedBytes, Charsets.UTF_8)
        } catch (e: Throwable) {
            cipherText
        }
    }
}

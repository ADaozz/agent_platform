package org.example.backend.common.utils;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

class PasswordUtilsTest {

    @Test
    void acceptsMixedRegisterPassword() {
        assertTrue(PasswordUtils.isValidRegisterPassword("Ab1@xy"));
        assertTrue(PasswordUtils.isValidRegisterPassword("Aa1!234567"));
        assertNull(PasswordUtils.validateRegisterPassword("Z9#aBc"));
    }

    @Test
    void rejectsWeakRegisterPassword() {
        assertFalse(PasswordUtils.isValidRegisterPassword("abc"));          // too short
        assertFalse(PasswordUtils.isValidRegisterPassword("Abcdef"));       // no digit/symbol
        assertFalse(PasswordUtils.isValidRegisterPassword("abcdef1"));      // no upper/symbol
        assertFalse(PasswordUtils.isValidRegisterPassword("ABCDEF1!"));     // no lower
        assertFalse(PasswordUtils.isValidRegisterPassword("Abcdef!"));      // no digit
        assertFalse(PasswordUtils.isValidRegisterPassword("Abcdef1"));      // no symbol
        assertFalse(PasswordUtils.isValidRegisterPassword("Aa1!234567890")); // too long
        assertNotNull(PasswordUtils.validateRegisterPassword("plain"));
    }
}

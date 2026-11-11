package org.example.backend.common.utils;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.example.backend.common.result.AjaxResult;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.Collections;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

class LogDesensitizeUtilsTest {

    private ObjectMapper objectMapper;

    @BeforeEach
    void setUp() {
        objectMapper = new ObjectMapper();
    }

    @Test
    void nullValue_returnsNull() {
        assertNull(LogDesensitizeUtils.toDesensitizedJson(
                objectMapper, null, Collections.<String>emptySet(), Collections.<String>emptySet()));
    }

    @Test
    void fullMask_passwordCaseInsensitive() throws Exception {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("passWord", "Secret123");
        body.put("PASSWORD", "Another");
        String json = LogDesensitizeUtils.toDesensitizedJson(
                objectMapper, body, Collections.<String>emptySet(), Collections.<String>emptySet());
        assertTrue(json.contains("\"passWord\":\"******\""));
        assertTrue(json.contains("\"PASSWORD\":\"******\""));
        assertFalse(json.contains("Secret123"));
    }

    @Test
    void fullMask_secretKeyAndP12Password() throws Exception {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("secretKey", "sk-live-abc");
        body.put("p12Password", "cert-pass");
        String json = LogDesensitizeUtils.toDesensitizedJson(
                objectMapper, body, Collections.<String>emptySet(), Collections.<String>emptySet());
        assertTrue(json.contains("\"secretKey\":\"******\""));
        assertTrue(json.contains("\"p12Password\":\"******\""));
    }

    @Test
    void partialMask_longToken() {
        String masked = LogDesensitizeUtils.partialMask("eyJhbGciOiJIUzI1NiJ9.payload.signature");
        assertEquals("eyJh****ture", masked);
    }

    @Test
    void partialMask_shortToken() {
        assertEquals("******", LogDesensitizeUtils.partialMask("short"));
        assertEquals("******", LogDesensitizeUtils.partialMask("12345678"));
    }

    @Test
    void partialMask_sessionIdInResponse() throws Exception {
        Map<String, Object> loginVo = new LinkedHashMap<>();
        loginVo.put("token", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.abc.def");
        loginVo.put("sessionId", "a1b2c3d4e5f67890abcdef1234567890");
        String json = LogDesensitizeUtils.toDesensitizedJson(
                objectMapper, loginVo, Collections.<String>emptySet(), Collections.<String>emptySet());
        assertTrue(json.contains("\"token\":\"eyJh****"));
        assertTrue(json.contains("\"sessionId\":\"a1b2****7890\""));
        assertFalse(json.contains("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"));
    }

    @Test
    void excludeKeys_removeFieldEntirely() throws Exception {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("passWord", "Secret123");
        body.put("userName", "admin");
        String json = LogDesensitizeUtils.toDesensitizedJson(
                objectMapper, body, Collections.singleton("passWord"), Collections.<String>emptySet());
        assertFalse(json.contains("passWord"));
        assertFalse(json.contains("Secret123"));
        assertTrue(json.contains("\"userName\":\"admin\""));
    }

    @Test
    void excludeTakesPrecedenceOverMask() throws Exception {
        Map<String, Object> body = Collections.singletonMap("token", "eyJhbGciOiJIUzI1NiJ9.abc.def");
        String json = LogDesensitizeUtils.toDesensitizedJson(
                objectMapper, body, Collections.singleton("token"), Collections.<String>emptySet());
        assertFalse(json.contains("token"));
        assertFalse(json.contains("eyJh"));
    }

    @Test
    void nestedObjectAndArray() throws Exception {
        Map<String, Object> user = Collections.singletonMap("passWord", "pwd");
        Map<String, Object> item = Collections.singletonMap("secretKey", "sk-1");
        Map<String, Object> nested = new LinkedHashMap<>();
        nested.put("user", user);
        nested.put("items", Collections.singletonList(item));
        String json = LogDesensitizeUtils.toDesensitizedJson(
                objectMapper, nested, Collections.<String>emptySet(), Collections.<String>emptySet());
        assertTrue(json.contains("\"passWord\":\"******\""));
        assertTrue(json.contains("\"secretKey\":\"******\""));
    }

    @Test
    void ajaxResultDataStructure() throws Exception {
        Map<String, Object> user = Collections.singletonMap("userId", 1);
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("token", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.sign.here");
        data.put("user", user);
        AjaxResult result = AjaxResult.success("登录成功", data);
        String json = LogDesensitizeUtils.toDesensitizedJson(
                objectMapper, result, Collections.<String>emptySet(), Collections.<String>emptySet());
        assertTrue(json.contains("\"token\":\"eyJh****"));
        assertTrue(json.contains("\"userId\":1"));
    }

    @Test
    void extraSensitiveParamNames_mergedWithGlobal() throws Exception {
        Map<String, Object> body = Collections.singletonMap("customSecret", "value-123");
        Set<String> extra = new HashSet<>(Collections.singletonList("customSecret"));
        String json = LogDesensitizeUtils.toDesensitizedJson(
                objectMapper, body, Collections.<String>emptySet(), extra);
        assertTrue(json.contains("\"customSecret\":\"******\""));
    }
}

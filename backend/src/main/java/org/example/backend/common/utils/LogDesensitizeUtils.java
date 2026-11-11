package org.example.backend.common.utils;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.fasterxml.jackson.databind.node.TextNode;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

/**
 * 操作日志 JSON 脱敏：递归处理嵌套对象/数组，供 LogAspect 控制台与 sys_oper_log 共用。
 */
public final class LogDesensitizeUtils {

    private static final String FULL_MASK = "******";

    private static final Set<String> FULL_MASK_KEYS = Collections.unmodifiableSet(new HashSet<>(Arrays.asList(
            "password", "passwd", "pwd", "oldpassword", "newpassword", "confirmpassword",
            "p12password", "secretkey", "secret", "privatekey", "credential"
    )));

    private static final Set<String> PARTIAL_MASK_KEYS = Collections.unmodifiableSet(new HashSet<>(Arrays.asList(
            "token", "accesstoken", "refreshtoken", "authorization", "sessionid"
    )));

    private LogDesensitizeUtils() {
    }

    public static String toDesensitizedJson(ObjectMapper mapper, Object value,
                                            Set<String> excludeKeys,
                                            Set<String> extraFullMaskKeys) {
        if (value == null) {
            return null;
        }
        Set<String> excludes = normalizeKeys(excludeKeys);
        Set<String> fullMaskKeys = mergeFullMaskKeys(extraFullMaskKeys);
        try {
            JsonNode root = mapper.valueToTree(value);
            desensitizeNode(root, excludes, fullMaskKeys);
            return mapper.writeValueAsString(root);
        } catch (JsonProcessingException e) {
            return String.valueOf(value);
        }
    }

    private static Set<String> mergeFullMaskKeys(Set<String> extraFullMaskKeys) {
        if (extraFullMaskKeys == null || extraFullMaskKeys.isEmpty()) {
            return FULL_MASK_KEYS;
        }
        Set<String> merged = new HashSet<>(FULL_MASK_KEYS);
        merged.addAll(normalizeKeys(extraFullMaskKeys));
        return Collections.unmodifiableSet(merged);
    }

    private static Set<String> normalizeKeys(Set<String> keys) {
        if (keys == null || keys.isEmpty()) {
            return Collections.emptySet();
        }
        Set<String> normalized = new HashSet<>();
        for (String key : keys) {
            if (key != null && !key.trim().isEmpty()) {
                normalized.add(key.toLowerCase(Locale.ROOT));
            }
        }
        return normalized;
    }

    private static void desensitizeNode(JsonNode node, Set<String> excludeKeys, Set<String> fullMaskKeys) {
        if (node == null) {
            return;
        }
        if (node.isObject()) {
            desensitizeObject((ObjectNode) node, excludeKeys, fullMaskKeys);
        } else if (node.isArray()) {
            desensitizeArray((ArrayNode) node, excludeKeys, fullMaskKeys);
        }
    }

    private static void desensitizeObject(ObjectNode object, Set<String> excludeKeys, Set<String> fullMaskKeys) {
        List<String> toRemove = new ArrayList<>();
        Iterator<Map.Entry<String, JsonNode>> fields = object.fields();
        while (fields.hasNext()) {
            Map.Entry<String, JsonNode> entry = fields.next();
            String fieldName = entry.getKey();
            String normalized = fieldName.toLowerCase(Locale.ROOT);
            if (excludeKeys.contains(normalized)) {
                toRemove.add(fieldName);
                continue;
            }
            JsonNode child = entry.getValue();
            if (child == null || child.isNull()) {
                continue;
            }
            if (child.isValueNode()) {
                applyMask(object, fieldName, normalized, child.asText(), fullMaskKeys);
            } else {
                desensitizeNode(child, excludeKeys, fullMaskKeys);
            }
        }
        for (String fieldName : toRemove) {
            object.remove(fieldName);
        }
    }

    private static void desensitizeArray(ArrayNode array, Set<String> excludeKeys, Set<String> fullMaskKeys) {
        for (int i = 0; i < array.size(); i++) {
            JsonNode element = array.get(i);
            if (element != null && !element.isValueNode()) {
                desensitizeNode(element, excludeKeys, fullMaskKeys);
            }
        }
    }

    private static void applyMask(ObjectNode object, String fieldName, String normalized,
                                  String rawValue, Set<String> fullMaskKeys) {
        if (rawValue == null) {
            return;
        }
        if (fullMaskKeys.contains(normalized)) {
            object.set(fieldName, TextNode.valueOf(FULL_MASK));
        } else if (PARTIAL_MASK_KEYS.contains(normalized)) {
            object.set(fieldName, TextNode.valueOf(partialMask(rawValue)));
        }
    }

    static String partialMask(String value) {
        if (value == null || value.length() <= 8) {
            return FULL_MASK;
        }
        return value.substring(0, 4) + "****" + value.substring(value.length() - 4);
    }
}

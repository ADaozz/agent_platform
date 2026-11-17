package org.example.backend.common.utils;

import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.util.StringUtils;

import java.util.regex.Pattern;

public class PasswordUtils {
    private static final BCryptPasswordEncoder encoder = new BCryptPasswordEncoder();

    /** 注册密码：长度 6-12，且需同时包含大小写字母、数字与符号 */
    public static final int REGISTER_PASSWORD_MIN = 6;
    public static final int REGISTER_PASSWORD_MAX = 12;
    public static final String REGISTER_PASSWORD_RULE_MESSAGE =
            "密码长度需为6-12位，且需同时包含大小写字母、数字与符号";

    private static final Pattern HAS_LOWER = Pattern.compile("[a-z]");
    private static final Pattern HAS_UPPER = Pattern.compile("[A-Z]");
    private static final Pattern HAS_DIGIT = Pattern.compile("\\d");
    private static final Pattern HAS_SYMBOL = Pattern.compile("[^A-Za-z0-9]");

    // 密码比对
    public static boolean matches(String rawPassword, String encodedPassword) {
        return encoder.matches(rawPassword, encodedPassword);
    }

    // 密码摘要
    public static String encrypt(String password) {
        return encoder.encode(password);
    }

    /** 校验注册密码强度；不满足时返回错误文案，通过返回 null */
    public static String validateRegisterPassword(String password) {
        if (!StringUtils.hasText(password)) {
            return "密码不能为空";
        }
        int len = password.length();
        if (len < REGISTER_PASSWORD_MIN || len > REGISTER_PASSWORD_MAX) {
            return REGISTER_PASSWORD_RULE_MESSAGE;
        }
        if (!HAS_LOWER.matcher(password).find()
                || !HAS_UPPER.matcher(password).find()
                || !HAS_DIGIT.matcher(password).find()
                || !HAS_SYMBOL.matcher(password).find()) {
            return REGISTER_PASSWORD_RULE_MESSAGE;
        }
        return null;
    }

    public static boolean isValidRegisterPassword(String password) {
        return validateRegisterPassword(password) == null;
    }
}

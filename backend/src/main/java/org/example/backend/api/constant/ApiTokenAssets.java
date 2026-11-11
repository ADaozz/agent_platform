package org.example.backend.api.constant;

import org.example.backend.common.exception.BusinessException;
import org.example.backend.common.exception.Module;
import org.springframework.http.HttpMethod;
import org.springframework.util.StringUtils;

import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * API Token 授权资源标识：{resource}:{action}。
 * 兼容旧值 vm / app，等价于 vm:list / app:list。
 */
public final class ApiTokenAssets {

    private ApiTokenAssets() {
    }

    public static final String VM = "vm";
    public static final String APP = "app";

    public static final String VM_LIST = "vm:list";
    public static final String VM_ADD = "vm:add";
    public static final String VM_EDIT = "vm:edit";
    public static final String VM_DELETE = "vm:delete";

    public static final String APP_LIST = "app:list";
    public static final String APP_ADD = "app:add";
    public static final String APP_EDIT = "app:edit";
    public static final String APP_DELETE = "app:delete";

    private static final Set<String> ALLOWED = Collections.unmodifiableSet(new HashSet<>(Arrays.asList(
            VM, APP,
            VM_LIST, VM_ADD, VM_EDIT, VM_DELETE,
            APP_LIST, APP_ADD, APP_EDIT, APP_DELETE
    )));

    public static boolean isAllowed(String asset) {
        return StringUtils.hasText(asset) && ALLOWED.contains(asset);
    }

    public static void validateAssets(List<String> assets) {
        if (assets == null || assets.isEmpty()
                || assets.stream().anyMatch(asset -> !isAllowed(asset))) {
            throw new BusinessException(Module.ModuleType.API, "asset 错误", null);
        }
    }

    /**
     * 根据 HTTP 方法与路径解析 API Token 所需授权；非开放路径返回 null。
     */
    public static String requiredGrant(String httpMethod, String servletPath) {
        if (!StringUtils.hasText(httpMethod) || !StringUtils.hasText(servletPath)) {
            return null;
        }
        String resource = resolveResource(servletPath);
        if (resource == null) {
            return null;
        }
        String action = resolveAction(httpMethod);
        if (action == null) {
            return null;
        }
        return resource + ":" + action;
    }

    /** 判断 Token 已授权列表是否满足所需 grant（含 vm/app 旧别名） */
    public static boolean isGranted(List<String> granted, String requiredGrant) {
        if (granted == null || granted.isEmpty() || !StringUtils.hasText(requiredGrant)) {
            return false;
        }
        Set<String> normalized = new HashSet<>();
        for (String item : granted) {
            normalized.add(normalizeGrant(item));
        }
        return normalized.contains(requiredGrant);
    }

    /** vm → vm:list，app → app:list；其余原样 */
    public static String normalizeGrant(String asset) {
        if (VM.equals(asset)) {
            return VM_LIST;
        }
        if (APP.equals(asset)) {
            return APP_LIST;
        }
        return asset;
    }

    private static String resolveResource(String servletPath) {
        if (servletPath.equals("/asset/vm") || servletPath.startsWith("/asset/vm/")) {
            return "vm";
        }
        if (servletPath.equals("/asset/app") || servletPath.startsWith("/asset/app/")) {
            return "app";
        }
        return null;
    }

    private static String resolveAction(String httpMethod) {
        if (HttpMethod.GET.matches(httpMethod)) {
            return "list";
        }
        if (HttpMethod.POST.matches(httpMethod)) {
            return "add";
        }
        if (HttpMethod.PUT.matches(httpMethod) || HttpMethod.PATCH.matches(httpMethod)) {
            return "edit";
        }
        if (HttpMethod.DELETE.matches(httpMethod)) {
            return "delete";
        }
        return null;
    }
}

package org.example.backend.common.aspect;

import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.aspectj.lang.JoinPoint;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.reflect.MethodSignature;
import org.example.backend.auth.session.util.ClientIpUtils;
import org.example.backend.common.annotation.Log;
import org.example.backend.common.operlog.entity.SysOperLogEntity;
import org.example.backend.common.operlog.service.SysOperLogService;
import org.example.backend.common.utils.LogDesensitizeUtils;
import org.example.backend.security.context.LoginUserUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.validation.BindingResult;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;
import org.springframework.web.multipart.MultipartFile;

import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import java.util.Arrays;
import java.util.Date;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * 操作日志切面：控制台摘要 + 异步落库 {@code sys_oper_log}。
 */
@Aspect
@Component
@Order(100)
@Slf4j
public class LogAspect {

    private static final int MAX_TEXT_LEN = 2000;

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private SysOperLogService sysOperLogService;

    @Around("@annotation(controllerLog)")
    public Object around(ProceedingJoinPoint joinPoint, Log controllerLog) throws Throwable {
        long start = System.currentTimeMillis();
        Object result = null;
        Throwable error = null;
        try {
            result = joinPoint.proceed();
            return result;
        } catch (Throwable ex) {
            error = ex;
            throw ex;
        } finally {
            long costMs = System.currentTimeMillis() - start;
            recordLog(joinPoint, controllerLog, result, error, costMs);
        }
    }

    private void recordLog(JoinPoint joinPoint, Log controllerLog, Object result,
                           Throwable error, long costMs) {
        MethodSignature signature = (MethodSignature) joinPoint.getSignature();
        Long userId = LoginUserUtils.getUserId();
        String requestParams = buildRequestParams(joinPoint, controllerLog);
        String responseBody = buildResponseBody(result, controllerLog);
        HttpServletRequest request = currentRequest();

        StringBuilder sb = new StringBuilder("[操作日志]");
        appendField(sb, "模块", controllerLog.title());
        appendField(sb, "类型", controllerLog.businessType());
        appendField(sb, "操作人", userId);
        appendField(sb, "类别", controllerLog.operatorType());
        appendField(sb, "方法", signature.getDeclaringType().getSimpleName() + "." + signature.getName());
        appendField(sb, "耗时", costMs + "ms");
        appendField(sb, "状态", error == null ? "成功" : "失败");
        if (error != null) {
            appendField(sb, "异常", error.getMessage());
        }
        appendField(sb, "请求", requestParams);
        appendField(sb, "响应", responseBody);
        log.info(sb.toString());

        SysOperLogEntity operLog = new SysOperLogEntity();
        operLog.setTitle(controllerLog.title());
        operLog.setBusinessType(controllerLog.businessType().name());
        operLog.setMethod(signature.getDeclaringTypeName() + "." + signature.getName());
        operLog.setOperatorType(controllerLog.operatorType().name());
        operLog.setOperUserId(userId);
        if (request != null) {
            operLog.setRequestMethod(request.getMethod());
            operLog.setOperUrl(request.getRequestURI());
            operLog.setOperIp(ClientIpUtils.resolveClientIp(request));
        }
        operLog.setOperParam(truncate(requestParams));
        operLog.setJsonResult(truncate(responseBody));
        operLog.setStatus(error == null ? "0" : "1");
        operLog.setErrorMsg(error == null ? null : truncate(error.getMessage()));
        operLog.setCostTime(costMs);
        operLog.setOperTime(new Date());
        sysOperLogService.saveAsync(operLog);
    }

    private HttpServletRequest currentRequest() {
        ServletRequestAttributes attrs =
                (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
        return attrs != null ? attrs.getRequest() : null;
    }

    private String truncate(String text) {
        if (text == null) {
            return null;
        }
        return text.length() <= MAX_TEXT_LEN ? text : text.substring(0, MAX_TEXT_LEN);
    }

    private void appendField(StringBuilder sb, String label, Object value) {
        if (value == null) {
            return;
        }
        String text = String.valueOf(value).trim();
        if (text.isEmpty() || "-".equals(text) || "{}".equals(text)) {
            return;
        }
        sb.append(' ').append(label).append('=').append(text);
    }

    private String buildRequestParams(JoinPoint joinPoint, Log controllerLog) {
        if (!controllerLog.isSaveRequestData()) {
            return null;
        }
        Set<String> excludes = new HashSet<>(Arrays.asList(controllerLog.excludeParamNames()));
        MethodSignature signature = (MethodSignature) joinPoint.getSignature();
        String[] paramNames = signature.getParameterNames();
        Object[] args = joinPoint.getArgs();

        Map<String, Object> params = new LinkedHashMap<>();
        for (int i = 0; i < args.length; i++) {
            Object arg = args[i];
            if (arg == null || isFilterObject(arg)) {
                continue;
            }
            String paramName = paramNames != null && i < paramNames.length ? paramNames[i] : "arg" + i;
            if (excludes.contains(paramName)) {
                continue;
            }
            Object value = toLogValue(arg, excludes);
            params.put(paramName, value);
        }
        if (params.isEmpty()) {
            return null;
        }
        return toDesensitizedJson(params, controllerLog);
    }

    private String buildResponseBody(Object result, Log controllerLog) {
        if (!controllerLog.isSaveResponseData() || result == null) {
            return null;
        }
        return toDesensitizedJson(result, controllerLog);
    }

    @SuppressWarnings("unchecked")
    private Object toLogValue(Object arg, Set<String> excludes) {
        if (arg == null) {
            return null;
        }
        if (isSimpleValue(arg)) {
            return arg;
        }
        Map<String, Object> map = objectMapper.convertValue(arg, Map.class);
        if (map != null && !excludes.isEmpty()) {
            excludes.forEach(map::remove);
        }
        return map;
    }

    private String toDesensitizedJson(Object value, Log controllerLog) {
        Set<String> excludeKeys = new HashSet<>(Arrays.asList(controllerLog.excludeParamNames()));
        Set<String> sensitiveKeys = new HashSet<>(Arrays.asList(controllerLog.sensitiveParamNames()));
        return LogDesensitizeUtils.toDesensitizedJson(objectMapper, value, excludeKeys, sensitiveKeys);
    }

    private boolean isSimpleValue(Object arg) {
        return arg instanceof CharSequence
                || arg instanceof Number
                || arg instanceof Boolean
                || arg.getClass().isEnum();
    }

    private boolean isFilterObject(Object arg) {
        return arg instanceof HttpServletRequest
                || arg instanceof HttpServletResponse
                || arg instanceof MultipartFile
                || arg instanceof BindingResult;
    }
}

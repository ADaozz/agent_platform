package org.example.backend.common.exception;

import lombok.extern.slf4j.Slf4j;
import org.apache.shiro.authz.AuthorizationException;
import org.example.backend.common.result.AjaxResult;
import org.springframework.http.HttpStatus;
import org.springframework.validation.BindException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import javax.validation.ConstraintViolation;
import javax.validation.ConstraintViolationException;
import java.util.stream.Collectors;

/**
 * 统一异常 → {@link AjaxResult}。
 * <ul>
 *   <li>业务/校验：HTTP 200 + {@code code=500}</li>
 *   <li>无权限：HTTP 403 + {@code code=500}</li>
 *   <li>未登录：由 {@code JwtFilter} 写 HTTP 401，不经此处</li>
 * </ul>
 */
@Slf4j
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(BusinessException.class)
    public AjaxResult handleBusinessException(BusinessException e) {
        return AjaxResult.error(e.getModule().getName() + "错误:" + e.getMessage(), null);
    }

    @ExceptionHandler(AuthorizationException.class)
    @ResponseStatus(HttpStatus.FORBIDDEN)
    public AjaxResult handleAuthorizationException(AuthorizationException e) {
        return AjaxResult.error("无权限访问", null);
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public AjaxResult handleMethodArgumentNotValidException(MethodArgumentNotValidException e) {
        String msg = e.getBindingResult().getFieldErrors().stream()
                .map(err -> err.getDefaultMessage())
                .collect(Collectors.joining("; "));
        return AjaxResult.error(msg, null);
    }

    @ExceptionHandler(BindException.class)
    public AjaxResult handleBindException(BindException e) {
        String msg = e.getBindingResult().getFieldErrors().stream()
                .map(err -> err.getDefaultMessage())
                .collect(Collectors.joining("; "));
        return AjaxResult.error(msg, null);
    }

    @ExceptionHandler(ConstraintViolationException.class)
    public AjaxResult handleConstraintViolationException(ConstraintViolationException e) {
        String msg = e.getConstraintViolations().stream()
                .map(ConstraintViolation::getMessage)
                .collect(Collectors.joining("; "));
        return AjaxResult.error(msg, null);
    }

    @ExceptionHandler(Exception.class)
    public AjaxResult handleException(Exception e) {
        log.error("未捕获异常", e);
        return AjaxResult.error("系统繁忙，请稍后重试", null);
    }
}

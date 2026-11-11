package org.example.backend.common.annotation;

import org.example.backend.common.enums.BusinessType;
import org.example.backend.common.enums.OperatorType;

import java.lang.annotation.Documented;
import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * 自定义操作日志记录注解
 */
@Target({ElementType.PARAMETER, ElementType.METHOD})
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface Log {

    /**
     * 模块
     */
    String title() default "";

    /**
     * 功能
     */
    BusinessType businessType() default BusinessType.OTHER;

    /**
     * 操作人类别
     */
    OperatorType operatorType() default OperatorType.MANAGE;

    /**
     * 是否保存请求的参数
     */
    boolean isSaveRequestData() default true;

    /**
     * 是否保存响应的参数
     */
    boolean isSaveResponseData() default true;

    /**
     * 排除指定的请求参数（大小写不敏感，匹配到的字段不会写入日志）
     */
    String[] excludeParamNames() default {};

    /**
     * 额外需要全掩码的字段名（大小写不敏感，与全局敏感字段规则合并）
     */
    String[] sensitiveParamNames() default {};
}

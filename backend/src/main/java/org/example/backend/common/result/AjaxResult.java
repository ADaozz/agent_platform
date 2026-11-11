package org.example.backend.common.result;

import java.util.HashMap;

/**
 * 统一 API 响应体：{@code { code, msg, data }}。
 */
public class AjaxResult extends HashMap<String, Object> {

    public static final String CODE_TAG = "code";
    public static final String MSG_TAG = "msg";
    public static final String DATA_TAG = "data";

    public AjaxResult(ResultCode.Type type, String msg, Object data) {
        super.put(CODE_TAG, type.value());
        super.put(MSG_TAG, msg);
        super.put(DATA_TAG, data);
    }

    public static AjaxResult success(String msg, Object data) {
        return new AjaxResult(
                ResultCode.Type.SUCCESS,
                msg != null ? msg : "操作成功",
                data
        );
    }

    public static AjaxResult error(String msg, Object data) {
        return new AjaxResult(
                ResultCode.Type.ERROR,
                msg != null ? msg : "发生错误",
                data
        );
    }

    public static AjaxResult of(ResultCode.Type type, String msg, Object data) {
        return new AjaxResult(type, msg, data);
    }
}

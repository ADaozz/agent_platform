package org.example.backend.common.result;

/**
 * 统一业务状态码。HTTP 401/403 由 Filter / ExceptionHandler 控制；body 内 {@code code} 见下表。
 */
public final class ResultCode {

    private ResultCode() {
    }

    public enum Type {

        /** 成功 */
        SUCCESS(0),

        /** 业务失败、参数校验失败（HTTP 200） */
        ERROR(500);

        private final int value;

        Type(int value) {
            this.value = value;
        }

        public int value() {
            return value;
        }
    }
}

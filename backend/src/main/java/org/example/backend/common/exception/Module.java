package org.example.backend.common.exception;

import lombok.Getter;

public class Module {

    @Getter
    public enum ModuleType{

        AUTH("认证授权", "auth"),
        SYSTEM("系统管理","system");

        private final String name;
        private final String code;

        ModuleType(String name, String code) {
            this.name = name;
            this.code = code;
        }

    }
}

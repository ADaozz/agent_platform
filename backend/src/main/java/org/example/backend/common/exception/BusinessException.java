package org.example.backend.common.exception;

import lombok.Getter;

@Getter
public class BusinessException extends RuntimeException{

    private final Module.ModuleType module;

    public BusinessException(Module.ModuleType module, String message, Throwable cause){
        super(message, cause);
        this.module = module;
    }
}

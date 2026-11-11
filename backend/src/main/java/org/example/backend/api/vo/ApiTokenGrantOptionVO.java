package org.example.backend.api.vo;

import lombok.Data;

@Data
public class ApiTokenGrantOptionVO {

    /** Token 写入的 asset 值，如 vm:list */
    private String value;

    private String label;
}

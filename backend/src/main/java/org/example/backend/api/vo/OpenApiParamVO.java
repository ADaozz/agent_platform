package org.example.backend.api.vo;

import lombok.Data;

@Data
public class OpenApiParamVO {

    private String name;

    private String type;

    private boolean required;

    private String description;

    /** 示例值 */
    private String example;
}

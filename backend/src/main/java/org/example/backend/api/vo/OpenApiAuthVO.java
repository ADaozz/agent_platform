package org.example.backend.api.vo;

import lombok.Data;

import java.util.List;

@Data
public class OpenApiAuthVO {

    private String type;

    private List<OpenApiAuthHeaderVO> headers;

    private String note;
}

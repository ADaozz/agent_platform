package org.example.backend.api.vo;

import lombok.Data;

import java.util.List;

@Data
public class OpenApiDocVO {

    private String baseUrl;

    private OpenApiAuthVO auth;

    private List<OpenApiOperationVO> operations;
}

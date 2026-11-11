package org.example.backend.api.vo;

import lombok.Data;

import java.util.List;

@Data
public class ApiTokenGrantGroupVO {

    private String key;

    private String name;

    private List<ApiTokenGrantOptionVO> options;
}

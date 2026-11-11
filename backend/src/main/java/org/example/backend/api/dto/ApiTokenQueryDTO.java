package org.example.backend.api.dto;

import lombok.Data;

import javax.validation.constraints.Max;
import javax.validation.constraints.Min;
import javax.validation.constraints.NotBlank;
import javax.validation.constraints.Size;

@Data
public class ApiTokenQueryDTO {

    private Long userId;

    private String accessKey;

    private String tokenName;

    @Min(1)
    private Integer pageNum = 1;

    @Max(50)
    private Integer pageSize = 10;
}

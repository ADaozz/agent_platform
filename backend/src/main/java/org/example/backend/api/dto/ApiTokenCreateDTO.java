package org.example.backend.api.dto;

import lombok.Data;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotEmpty;
import javax.validation.constraints.Size;
import java.util.List;

@Data
public class ApiTokenCreateDTO {

    @NotBlank(message = "名称不能为空")
    @Size(max = 128)
    private String tokenName;

    @NotBlank(message = "用途不能为空")
    private String detail;

    @NotEmpty(message = "必须选定一个业务资源")
    private List<String> asset;
}

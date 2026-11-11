package org.example.backend.asset.app.dto;

import lombok.Data;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.Pattern;
import javax.validation.constraints.Size;

@Data
public class VmAppUpdateDTO {

    @NotBlank(message = "应用ID不能为空")
    private String appId;

    @NotBlank(message = "应用名称不能为空")
    @Size(max = 128)
    private String appName;

    @NotBlank(message = "部署路径不能为空")
    @Size(max = 512)
    private String deployPath;

    @NotBlank(message = "应用状态不能为空")
    @Pattern(regexp = "running|stopped", message = "应用状态只能是 running 或 stopped")
    private String appStatus;
}

package org.example.backend.quartz.dto;

import lombok.Data;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.Size;

@Data
public class SysJobCreateDTO {

    @NotBlank(message = "任务名称不能为空")
    @Size(max = 128, message = "任务名称最长128字符")
    private String jobName;

    @NotBlank(message = "Bean 名称不能为空")
    @Size(max = 64, message = "Bean 名称最长64字符")
    private String beanName;

    @Size(max = 64, message = "任务分组最长64字符")
    private String jobGroup;

    @Size(max = 512, message = "任务描述最长512字符")
    private String description;
}

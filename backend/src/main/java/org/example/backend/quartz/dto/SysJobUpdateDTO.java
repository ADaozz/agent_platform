package org.example.backend.quartz.dto;

import lombok.Data;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;
import javax.validation.constraints.Pattern;
import javax.validation.constraints.Size;

@Data
public class SysJobUpdateDTO {

    @NotNull(message = "任务ID不能为空")
    private Long jobId;

    @NotBlank(message = "任务名称不能为空")
    @Size(max = 128, message = "任务名称最长128字符")
    private String jobName;

    @Size(max = 64, message = "Cron 表达式最长64字符")
    private String cronExpression;

    @Size(max = 512, message = "任务描述最长512字符")
    private String description;

    /** 0-停用，1-启用 */
    @Pattern(regexp = "[01]", message = "启用状态只能是0或1")
    private String enabled;
}

package org.example.backend.quartz.dto;

import lombok.Data;

import javax.validation.constraints.Max;
import javax.validation.constraints.Min;

@Data
public class SysJobQueryDTO {

    /** 传 jobId 时查单条详情 */
    private Long jobId;

    private String jobName;

    private String jobGroup;

    /** 0-停用，1-启用 */
    private String enabled;

    @Min(1)
    private Integer pageNum = 1;

    @Max(50)
    private Integer pageSize = 10;
}

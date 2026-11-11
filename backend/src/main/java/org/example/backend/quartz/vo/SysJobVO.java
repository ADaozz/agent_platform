package org.example.backend.quartz.vo;

import com.fasterxml.jackson.annotation.JsonFormat;
import lombok.Data;
import org.springframework.format.annotation.DateTimeFormat;

import java.util.Date;

@Data
public class SysJobVO {

    private Long jobId;

    private String jobName;

    private String beanName;

    private String jobGroup;

    private String cronExpression;

    private String description;

    /** 最近一次执行状态：0-未执行，1-正在执行，2-执行成功，3-执行失败 */
    private String status;

    /** 0-停用，1-启用 */
    private String enabled;

    @JsonFormat(timezone = "GMT+8", pattern = "yyyy-MM-dd HH:mm:ss")
    @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private Date createTime;

    @JsonFormat(timezone = "GMT+8", pattern = "yyyy-MM-dd HH:mm:ss")
    @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private Date updateTime;
}

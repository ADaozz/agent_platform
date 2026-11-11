package org.example.backend.quartz.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.fasterxml.jackson.annotation.JsonFormat;
import lombok.Data;
import lombok.EqualsAndHashCode;
import lombok.experimental.Accessors;
import org.springframework.format.annotation.DateTimeFormat;

import java.util.Date;

@Data
@TableName("sys_job_log")
@Accessors(chain = true)
@EqualsAndHashCode(callSuper = false)
public class SysJobLogEntity {

    @TableId(type = IdType.ASSIGN_ID)
    // 日志 ID
    private Long logId;

    // 任务 ID
    private Long jobId;

    // 任务名称
    private String jobName;

    // 执行状态：0-成功，1-失败
    private String status;

    // 执行信息
    private String message;

    @JsonFormat(timezone = "GMT+8", pattern = "yyyy-MM-dd HH:mm:ss")
    @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    // 开始时间
    private Date startTime;

    @JsonFormat(timezone = "GMT+8", pattern = "yyyy-MM-dd HH:mm:ss")
    @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    // 结束时间
    private Date endTime;
}

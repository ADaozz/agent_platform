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
@TableName("sys_job")
@Accessors(chain = true)
@EqualsAndHashCode(callSuper = false)
public class SysJobEntity {

    @TableId(type = IdType.ASSIGN_ID)
    // 任务 ID
    private Long jobId;

    // 任务名称
    private String jobName;

    // Bean名称
    private String beanName;

    // 任务分组，默认 DEFAULT
    private String jobGroup;

    // Cron 表达式
    private String cronExpression;

    // 任务状态：0-未执行，1-正在执行，2-执行成功，3-执行失败
    private String status;

    // 启用状态：0-停用，1-启用；新建任务默认停用，不可直接执行
    private String enabled;

    // 任务描述
    private String description;

    @JsonFormat(timezone = "GMT+8", pattern = "yyyy-MM-dd HH:mm:ss")
    @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    // 创建时间
    private Date createTime;

    @JsonFormat(timezone = "GMT+8", pattern = "yyyy-MM-dd HH:mm:ss")
    @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    // 更新时间
    private Date updateTime;
}

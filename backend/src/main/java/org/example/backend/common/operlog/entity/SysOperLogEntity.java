package org.example.backend.common.operlog.entity;

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
@TableName("sys_oper_log")
@Accessors(chain = true)
@EqualsAndHashCode(callSuper = false)
public class SysOperLogEntity {

    @TableId(type = IdType.ASSIGN_ID)
    private Long operId;

    private String title;

    private String businessType;

    private String method;

    private String requestMethod;

    private String operatorType;

    private Long operUserId;

    private String operUrl;

    private String operIp;

    private String operParam;

    private String jsonResult;

    /** 0=成功 1=失败 */
    private String status;

    private String errorMsg;

    private Long costTime;

    @JsonFormat(timezone = "GMT+8", pattern = "yyyy-MM-dd HH:mm:ss")
    @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private Date operTime;
}

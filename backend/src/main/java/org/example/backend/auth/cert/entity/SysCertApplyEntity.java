package org.example.backend.auth.cert.entity;

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
@TableName("sys_cert_apply")
@Accessors(chain = true)
@EqualsAndHashCode(callSuper = false)
public class SysCertApplyEntity {

    @TableId(type = IdType.AUTO)
    private Long applyId;

    private Long userId;

    private String userName;

    private String applyType;

    private String status;

    private String applyReason;

    private String rejectReason;

    private String subjectCn;

    private String subjectO;

    private String subjectOu;

    private Integer validDays;

    private Long approverId;

    @JsonFormat(timezone = "GMT+8", pattern = "yyyy-MM-dd HH:mm:ss")
    @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private Date approveTime;

    private String p12Password;

    private String bundlePath;

    @JsonFormat(timezone = "GMT+8", pattern = "yyyy-MM-dd HH:mm:ss")
    @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private Date createTime;
}

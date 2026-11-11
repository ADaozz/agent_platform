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
@TableName("sys_user_cert")
@Accessors(chain = true)
@EqualsAndHashCode(callSuper = false)
public class SysUserCertEntity {

    @TableId(type = IdType.AUTO)
    private Long certId;

    private Long userId;

    private Long applyId;

    private String certType;

    private String certFingerprint;

    private String certSerial;

    private String subjectDn;

    private String issuerDn;

    @JsonFormat(timezone = "GMT+8", pattern = "yyyy-MM-dd HH:mm:ss")
    @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private Date notBefore;

    @JsonFormat(timezone = "GMT+8", pattern = "yyyy-MM-dd HH:mm:ss")
    @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private Date notAfter;

    private String certPath;

    private String keyPath;

    private String p12Path;

    /** 0=有效 1=吊销 */
    private String status;

    @JsonFormat(timezone = "GMT+8", pattern = "yyyy-MM-dd HH:mm:ss")
    @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private Date createTime;
}

package org.example.backend.auth.session.entity;

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
@TableName("sys_login_session")
@Accessors(chain = true)
@EqualsAndHashCode(callSuper = false)
public class LoginSessionEntity {

    @TableId(type = IdType.INPUT)
    private String sessionId;

    private Long userId;

    private String deviceName;

    private String loginIp;

    private String userAgent;

    @JsonFormat(timezone = "GMT+8", pattern = "yyyy-MM-dd HH:mm:ss")
    @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private Date loginTime;

    /** 0=在线 1=下线 */
    private String status;

    /** 0=账密 1=证书 */
    private String loginType;

    @JsonFormat(timezone = "GMT+8", pattern = "yyyy-MM-dd HH:mm:ss")
    @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private Date revokeTime;
}

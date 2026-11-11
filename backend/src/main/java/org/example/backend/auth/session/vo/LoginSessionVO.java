package org.example.backend.auth.session.vo;

import com.fasterxml.jackson.annotation.JsonFormat;
import lombok.Data;
import org.springframework.format.annotation.DateTimeFormat;

import java.util.Date;

@Data
public class LoginSessionVO {

    private String sessionId;

    private Long userId;

    private String userName;

    private String deviceName;

    private String loginIp;

    @JsonFormat(timezone = "GMT+8", pattern = "yyyy-MM-dd HH:mm:ss")
    @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private Date loginTime;

    /** 0=在线 1=下线 */
    private String status;

    /** 0=账密 1=证书 */
    private String loginType;

    /** 是否当前请求设备 */
    private Boolean current;
}

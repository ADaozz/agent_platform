package org.example.backend.auth.vo;

import lombok.Data;
import org.example.backend.system.user.vo.SysUserInfoVO;

@Data
public class LoginVO {

    private String token;

    private String sessionId;

    private SysUserInfoVO user;
}

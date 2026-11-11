package org.example.backend.auth.service;

import org.example.backend.auth.dto.LoginDTO;
import org.example.backend.auth.vo.LoginVO;
import org.example.backend.system.user.vo.SysUserInfoVO;

import javax.servlet.http.HttpServletRequest;

public interface AuthService {

    LoginVO login(LoginDTO dto, HttpServletRequest request);

    LoginVO loginByCert(HttpServletRequest request);

    void logout(HttpServletRequest request);

    SysUserInfoVO getCurrentUser();
}

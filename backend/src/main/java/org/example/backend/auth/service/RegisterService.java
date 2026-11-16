package org.example.backend.auth.service;

import org.example.backend.auth.dto.RegisterDTO;

public interface RegisterService {

    /** 向邮箱发送注册验证码 */
    void sendCode(String email);

    /** 校验验证码并创建用户（密码哈希存储） */
    void register(RegisterDTO dto);
}

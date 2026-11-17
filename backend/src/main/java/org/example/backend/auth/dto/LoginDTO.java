package org.example.backend.auth.dto;

import lombok.Data;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.Size;

@Data
public class LoginDTO {

    @NotBlank(message = "用户名或邮箱不能为空")
    @Size(max = 128, message = "用户名或邮箱最长128字符")
    private String userName;

    @NotBlank(message = "密码不能为空")
    @Size(max = 128, message = "密码最长128字符")
    private String passWord;
}

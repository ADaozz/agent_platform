package org.example.backend.auth.dto;

import lombok.Data;

import javax.validation.constraints.Email;
import javax.validation.constraints.NotBlank;
import javax.validation.constraints.Pattern;
import javax.validation.constraints.Size;

@Data
public class RegisterDTO {

    @NotBlank(message = "用户名不能为空")
    @Size(min = 2, max = 64, message = "用户名长度需为2-64字符")
    @Pattern(regexp = "^[A-Za-z0-9_\\u4e00-\\u9fa5]+$", message = "用户名只能包含字母、数字、下划线或中文")
    private String userName;

    @NotBlank(message = "邮箱不能为空")
    @Email(message = "邮箱格式不正确")
    @Size(max = 128, message = "邮箱最长128字符")
    private String email;

    @NotBlank(message = "密码不能为空")
    @Size(min = 6, max = 12, message = "密码长度需为6-12位，且需同时包含大小写字母、数字与符号")
    @Pattern(
            regexp = "^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d)(?=.*[^A-Za-z0-9]).{6,12}$",
            message = "密码长度需为6-12位，且需同时包含大小写字母、数字与符号"
    )
    private String passWord;

    @NotBlank(message = "确认密码不能为空")
    private String confirmPassWord;

    @NotBlank(message = "验证码不能为空")
    @Pattern(regexp = "^\\d{6}$", message = "验证码为6位数字")
    private String code;
}

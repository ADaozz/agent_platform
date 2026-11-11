package org.example.backend.system.user.dto;

import lombok.Data;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;
import javax.validation.constraints.Pattern;
import javax.validation.constraints.Size;

@Data
public class SysUserUpdateDTO {

    @NotNull
    private Long userId;

    @NotBlank(message = "用户名不能为空")
    @Size(max = 64, message = "用户名最长64字符")
    private String userName;

    @Size(min = 6, max = 32, message = "密码长度6-32位")
    private String passWord;

    @Pattern(regexp = "[01]", message = "状态只能是0或1")
    private String status;
}

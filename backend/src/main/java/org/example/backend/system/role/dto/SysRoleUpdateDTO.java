package org.example.backend.system.role.dto;

import lombok.Data;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;
import javax.validation.constraints.Size;

@Data
public class SysRoleUpdateDTO {

    @NotNull(message = "角色ID不能为空")
    private Long roleId;

    @NotBlank(message = "角色标识不能为空")
    @Size(max = 64, message = "角色标识最长64字符")
    private String sysRole;
}

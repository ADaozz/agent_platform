package org.example.backend.system.role.dto;

import lombok.Data;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.Size;
import java.util.List;

@Data
public class SysRoleCreateDTO {

    @NotBlank(message = "角色标识不能为空")
    @Size(max = 64, message = "角色标识最长64字符")
    private String sysRole;

    /** 新角色创建时可同时绑定权限；不传表示空权限 */
    private List<Long> permissionIds;
}

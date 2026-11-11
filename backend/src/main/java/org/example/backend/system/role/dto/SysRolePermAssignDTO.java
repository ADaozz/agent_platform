package org.example.backend.system.role.dto;

import lombok.Data;

import javax.validation.constraints.NotNull;
import java.util.List;

@Data
public class SysRolePermAssignDTO {

    @NotNull(message = "角色ID不能为空")
    private Long roleId;

    /** 覆盖式分配；空列表表示清空权限 */
    private List<Long> permissionIds;
}

package org.example.backend.system.user.dto;

import lombok.Data;

import javax.validation.constraints.NotNull;
import java.util.List;

@Data
public class SysUserRoleAssignDTO {

    @NotNull(message = "用户ID不能为空")
    private Long userId;

    /** 覆盖式分配；空列表表示清空角色 */
    private List<Long> roleIds;
}

package org.example.backend.system.role.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import lombok.EqualsAndHashCode;
import lombok.experimental.Accessors;

import java.util.List;

@Data
@TableName("sys_role_permission")
@Accessors(chain = true)
@EqualsAndHashCode(callSuper = false)
public class SysRolePermissionEntity {

    // 角色 ID
    private Long roleId;

    // 权限 ID
    private Long permissionId;
}

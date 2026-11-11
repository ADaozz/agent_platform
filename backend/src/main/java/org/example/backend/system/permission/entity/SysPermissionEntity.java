package org.example.backend.system.permission.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import lombok.EqualsAndHashCode;
import lombok.experimental.Accessors;

@Data
@TableName("sys_permission")
@Accessors(chain = true)
@EqualsAndHashCode(callSuper = false)
public class SysPermissionEntity {

    @TableId(type = IdType.AUTO)
    // 权限 ID
    private Long permissionId;

    // 权限标识，例如：system:user:list
    private String sysPermission;

    // 归属菜单 ID，为空表示未挂载到任何菜单
    private Long menuId;

    // 权限展示名称，例如：用户查询
    private String permName;

}

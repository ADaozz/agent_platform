package org.example.backend.system.role.service;

import com.baomidou.mybatisplus.extension.service.IService;
import org.example.backend.system.role.entity.SysRolePermissionEntity;

import java.util.List;

public interface SysRolePermissionService extends IService<SysRolePermissionEntity> {

    List<SysRolePermissionEntity> getByRoleId(Long roleId);

    void assignPermissionsByRoleId(Long roleId, List<Long> permissionIds);
}

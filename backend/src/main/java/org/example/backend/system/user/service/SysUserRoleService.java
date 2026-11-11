package org.example.backend.system.user.service;

import com.baomidou.mybatisplus.extension.service.IService;
import org.example.backend.system.user.entity.SysUserRoleEntity;

import java.util.List;

public interface SysUserRoleService extends IService<SysUserRoleEntity> {
    //获取用户的角色
    List<SysUserRoleEntity> getByUserId(Long userId);

    void assignRolesByUserId(Long userId, List<Long> roleIds);

    List<Long> listUserIdsByRoleId(Long roleId);
}

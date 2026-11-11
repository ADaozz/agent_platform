package org.example.backend.system.role.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import lombok.extern.slf4j.Slf4j;
import org.example.backend.system.role.entity.SysRolePermissionEntity;
import org.example.backend.system.role.mapper.SysRolePermissionMapper;
import org.example.backend.system.role.service.SysRolePermissionService;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import javax.annotation.Resource;
import java.util.Collections;
import java.util.List;

@Service
@Slf4j
public class SysRolePermissionServiceImpl extends ServiceImpl<SysRolePermissionMapper, SysRolePermissionEntity> implements SysRolePermissionService {

    @Resource
    private SysRolePermissionMapper sysRolePermissionMapper;

    @Override
    // 查询角色的权限关联列表
    public List<SysRolePermissionEntity> getByRoleId(Long roleId) {
        LambdaQueryWrapper<SysRolePermissionEntity> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(
                SysRolePermissionEntity::getRoleId,
                roleId
                );
        return sysRolePermissionMapper.selectList(wrapper);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    // 为角色重新分配权限
    public void assignPermissionsByRoleId(Long roleId, List<Long> permissionIds) {
        LambdaQueryWrapper<SysRolePermissionEntity> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(SysRolePermissionEntity::getRoleId, roleId);
        remove(wrapper);

        if (permissionIds == null || permissionIds.isEmpty()) {
            return;
        }
        List<SysRolePermissionEntity> relations = permissionIds.stream()
                .distinct()
                .map(permissionId -> new SysRolePermissionEntity()
                        .setRoleId(roleId)
                        .setPermissionId(permissionId))
                .collect(java.util.stream.Collectors.toList());
        saveBatch(relations);
    }
}

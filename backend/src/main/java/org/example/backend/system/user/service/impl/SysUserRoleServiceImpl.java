package org.example.backend.system.user.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import lombok.extern.slf4j.Slf4j;
import org.example.backend.system.user.entity.SysUserRoleEntity;
import org.example.backend.system.user.mapper.SysUserRoleMapper;
import org.example.backend.system.user.service.SysUserRoleService;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;
import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

@Service
@Slf4j
public class SysUserRoleServiceImpl extends ServiceImpl<SysUserRoleMapper, SysUserRoleEntity> implements SysUserRoleService {

    @Resource
    private SysUserRoleMapper sysUserRoleMapper;

    @Override
    // 查询用户的角色关联列表
    public List<SysUserRoleEntity> getByUserId(Long userId) {
        LambdaQueryWrapper<SysUserRoleEntity> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(
                SysUserRoleEntity::getUserId,
                userId
        );
        return sysUserRoleMapper.selectList(wrapper);
    }

    @Override
    // 为用户重新分配角色
    public void assignRolesByUserId(Long userId, List<Long> roleIds) {
        LambdaQueryWrapper<SysUserRoleEntity> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(
                SysUserRoleEntity::getUserId,
                userId
        );
        remove(wrapper);
        if (roleIds == null || roleIds.isEmpty()) {
            return;
        }
        List<SysUserRoleEntity> sysUserRoleEntityList = new ArrayList<>();
        for (Long roleId : roleIds) {
            SysUserRoleEntity entity = new SysUserRoleEntity();
            entity.setUserId(userId);
            entity.setRoleId(roleId);
            sysUserRoleEntityList.add(entity);
        }
        saveBatch(sysUserRoleEntityList);
    }

    @Override
    // 查询拥有指定角色的用户ID列表
    public List<Long> listUserIdsByRoleId(Long roleId) {
        if (roleId == null) {
            return new ArrayList<>();
        }
        LambdaQueryWrapper<SysUserRoleEntity> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(SysUserRoleEntity::getRoleId, roleId);
        return sysUserRoleMapper.selectList(wrapper).stream()
                .map(SysUserRoleEntity::getUserId)
                .collect(Collectors.toList());
    }
}

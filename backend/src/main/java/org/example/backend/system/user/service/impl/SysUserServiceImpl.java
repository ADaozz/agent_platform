package org.example.backend.system.user.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import lombok.extern.slf4j.Slf4j;
import org.apache.shiro.authc.AuthenticationException;
import org.example.backend.common.exception.BusinessException;
import org.example.backend.common.exception.Module;
import org.example.backend.common.utils.PasswordUtils;
import org.example.backend.common.vo.OptionVO;
import org.example.backend.common.vo.PageResultVO;
import org.example.backend.security.context.LoginUserUtils;
import org.example.backend.system.permission.service.SysPermissionService;
import org.example.backend.system.role.entity.SysRoleEntity;
import org.example.backend.system.role.service.SysRoleService;
import org.example.backend.system.user.constant.UserConstants;
import org.example.backend.system.user.event.UserStatusChangedEvent;
import org.example.backend.system.user.dto.SysUserCreateDTO;
import org.example.backend.system.user.dto.SysUserQueryDTO;
import org.example.backend.system.user.dto.SysUserRoleAssignDTO;
import org.example.backend.system.user.dto.SysUserUpdateDTO;
import org.example.backend.system.user.entity.SysUserEntity;
import org.example.backend.system.user.entity.SysUserRoleEntity;
import org.example.backend.system.user.mapper.SysUserMapper;
import org.example.backend.system.user.service.SysUserRoleService;
import org.example.backend.system.user.service.SysUserService;
import org.example.backend.system.user.vo.SysUserInfoVO;
import org.example.backend.system.user.vo.SysUserVO;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.CollectionUtils;
import org.springframework.util.StringUtils;

import javax.annotation.Resource;
import java.util.Collections;
import java.util.Date;
import java.util.List;
import java.util.stream.Collectors;

@Service
@Slf4j
public class SysUserServiceImpl extends ServiceImpl<SysUserMapper, SysUserEntity> implements SysUserService {

    private static final String ADMIN_ROLE_NAME = "admin";

    @Resource
    private SysUserMapper sysUserMapper;

    @Autowired
    private SysUserRoleService sysUserRoleService;

    @Autowired
    private SysRoleService sysRoleService;

    @Autowired
    private SysPermissionService sysPermissionService;

    @Resource
    private org.example.backend.security.cache.AuthorizationCacheEvictor authorizationCacheEvictor;

    @Resource
    private ApplicationEventPublisher eventPublisher;

    @Override
    // 校验用户处于启用状态
    public void assertUserActive(Long userId) {
        if (userId == null) {
            throw new AuthenticationException("账号已停用");
        }
        SysUserEntity user = getById(userId);
        if (user == null || !UserConstants.STATUS_NORMAL.equals(user.getStatus())) {
            throw new AuthenticationException("账号已停用");
        }
    }

    @Override
    // 按用户名查询用户
    public SysUserEntity getByUserName(String userName) {
        LambdaQueryWrapper<SysUserEntity> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(SysUserEntity::getUserName, userName);
        return sysUserMapper.selectOne(wrapper);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    // 创建用户并分配角色
    public void createUser(SysUserCreateDTO dto) {
        if (getByUserName(dto.getUserName()) != null) {
            throw new BusinessException(Module.ModuleType.SYSTEM, "用户名已存在", null);
        }

        Date now = new Date();
        SysUserEntity user = new SysUserEntity();
        user.setUserName(dto.getUserName());
        user.setPassWord(PasswordUtils.encrypt(dto.getPassWord()));
        user.setStatus(StringUtils.hasText(dto.getStatus()) ? dto.getStatus() : UserConstants.STATUS_NORMAL);
        user.setCreateTime(now);
        user.setUpdateTime(now);
        save(user);

        sysUserRoleService.assignRolesByUserId(user.getUserId(), dto.getRoleIds());
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    // 更新用户信息
    public void updateUser(SysUserUpdateDTO dto) {
        SysUserEntity user = getById(dto.getUserId());
        if (user == null) {
            throw new BusinessException(Module.ModuleType.SYSTEM, "用户不存在", null);
        }

        SysUserEntity exists = getByUserName(dto.getUserName());
        if (exists != null && !exists.getUserId().equals(dto.getUserId())) {
            throw new BusinessException(Module.ModuleType.SYSTEM, "用户名已存在", null);
        }

        String oldStatus = user.getStatus();
        user.setUserName(dto.getUserName());
        if (StringUtils.hasText(dto.getStatus())) {
            user.setStatus(dto.getStatus());
        }
        if (StringUtils.hasText(dto.getPassWord())) {
            user.setPassWord(PasswordUtils.encrypt(dto.getPassWord()));
        }
        user.setUpdateTime(new Date());
        boolean disabling = UserConstants.STATUS_NORMAL.equals(oldStatus)
                && UserConstants.STATUS_DISABLED.equals(user.getStatus());
        updateById(user);
        if (disabling) {
            publishUserStatusChanged(user.getUserId(), UserStatusChangedEvent.ChangeType.DISABLED);
        }
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    // 删除用户并清理关联数据
    public void deleteUser(Long userId) {
        SysUserEntity user = getById(userId);
        if (user == null) {
            throw new BusinessException(Module.ModuleType.SYSTEM, "用户不存在", null);
        }

        Long currentUserId = LoginUserUtils.getUserId();
        if (userId.equals(currentUserId)) {
            throw new BusinessException(Module.ModuleType.SYSTEM, "不能删除当前登录用户", null);
        }

        assertNotLastAdmin(userId);

        LambdaQueryWrapper<SysUserRoleEntity> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(SysUserRoleEntity::getUserId, userId);
        sysUserRoleService.remove(wrapper);
        removeById(userId);
        publishUserStatusChanged(userId, UserStatusChangedEvent.ChangeType.DELETED);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    // 为用户分配角色
    public void assignUserRoles(SysUserRoleAssignDTO dto) {
        SysUserEntity user = getById(dto.getUserId());
        if (user == null) {
            throw new BusinessException(Module.ModuleType.SYSTEM, "用户不存在", null);
        }
        assertNotRemoveLastAdminRole(dto.getUserId(), dto.getRoleIds());
        sysUserRoleService.assignRolesByUserId(dto.getUserId(), dto.getRoleIds());
        authorizationCacheEvictor.evictByUserId(dto.getUserId());
    }

    @Override
    // 按ID查询用户详情
    public SysUserVO getUserById(Long userId) {
        SysUserEntity user = getById(userId);
        if (user == null) {
            throw new BusinessException(Module.ModuleType.SYSTEM, "用户不存在", null);
        }
        return toSysUserVO(user);
    }

    @Override
    // 获取当前用户的角色与权限信息
    public SysUserInfoVO getCurrentUserInfo(Long userId) {
        SysUserEntity user = getById(userId);
        if (user == null) {
            throw new BusinessException(Module.ModuleType.SYSTEM, "用户不存在", null);
        }
        SysUserInfoVO vo = new SysUserInfoVO();
        vo.setUserId(userId);
        vo.setUsername(user.getUserName());
        vo.setRoles(sysRoleService.selectRoleOptionsByUserId(userId));
        vo.setPermissions(sysPermissionService.selectPermissionOptionsByUserId(userId));
        return vo;
    }

    @Override
    // 更新用户最后登录时间
    public void updateLastLoginTime(Long userId) {
        Date now = new Date();
        LambdaUpdateWrapper<SysUserEntity> wrapper = new LambdaUpdateWrapper<>();
        wrapper.eq(SysUserEntity::getUserId, userId)
                .set(SysUserEntity::getLastLoginTime, now)
                .set(SysUserEntity::getUpdateTime, now);
        update(wrapper);
    }

    @Override
    // 分页查询用户列表
    public PageResultVO<SysUserVO> listUserInfo(SysUserQueryDTO dto) {
        if (dto.getUserId() != null) {
            SysUserVO vo = getUserById(dto.getUserId());
            return new PageResultVO<>(1, Collections.singletonList(vo));
        }

        LambdaQueryWrapper<SysUserEntity> wrapper = buildUserQueryWrapper(dto);

        int pageNum = dto.getPageNum() != null ? dto.getPageNum() : 1;
        int pageSize = dto.getPageSize() != null ? dto.getPageSize() : 10;
        Page<SysUserEntity> page = page(new Page<>(pageNum, pageSize), wrapper);

        List<SysUserVO> rows = page.getRecords().stream()
                .map(this::toSysUserVO)
                .collect(Collectors.toList());
        return new PageResultVO<>(page.getTotal(), rows);
    }

    // 构建用户分页查询条件
    private LambdaQueryWrapper<SysUserEntity> buildUserQueryWrapper(SysUserQueryDTO dto) {
        LambdaQueryWrapper<SysUserEntity> wrapper = new LambdaQueryWrapper<>();

        if (dto.getRoleId() != null) {
            LambdaQueryWrapper<SysUserRoleEntity> urWrapper = new LambdaQueryWrapper<>();
            urWrapper.eq(SysUserRoleEntity::getRoleId, dto.getRoleId());
            List<Long> userIds = sysUserRoleService.list(urWrapper).stream()
                    .map(SysUserRoleEntity::getUserId)
                    .distinct()
                    .collect(Collectors.toList());
            if (userIds.isEmpty()) {
                wrapper.eq(SysUserEntity::getUserId, -1L);
            } else {
                wrapper.in(SysUserEntity::getUserId, userIds);
            }
        }

        if (StringUtils.hasText(dto.getUserName())) {
            wrapper.like(SysUserEntity::getUserName, dto.getUserName());
        }
        if (StringUtils.hasText(dto.getStatus())) {
            wrapper.eq(SysUserEntity::getStatus, dto.getStatus());
        }
        wrapper.orderByDesc(SysUserEntity::getCreateTime);
        return wrapper;
    }

    // 将用户实体转换为VO
    private SysUserVO toSysUserVO(SysUserEntity user) {
        SysUserVO vo = new SysUserVO();
        vo.setUserId(user.getUserId());
        vo.setUserName(user.getUserName());
        vo.setStatus(user.getStatus());
        vo.setCreateTime(user.getCreateTime());
        vo.setUpdateTime(user.getUpdateTime());
        vo.setLastLoginTime(user.getLastLoginTime());

        List<OptionVO> roles = sysRoleService.selectRoleOptionsByUserId(user.getUserId());
        vo.setRoles(CollectionUtils.isEmpty(roles) ? Collections.emptyList() : roles);
        return vo;
    }

    // 校验不能删除最后一个管理员
    private void assertNotLastAdmin(Long userId) {
        SysRoleEntity adminRole = getAdminRole();
        if (adminRole == null) {
            return;
        }
        if (!hasRole(userId, adminRole.getRoleId())) {
            return;
        }
        if (countUsersWithRole(adminRole.getRoleId()) <= 1) {
            throw new BusinessException(Module.ModuleType.SYSTEM, "不能删除最后一个管理员", null);
        }
    }

    // 校验不能移除最后一个管理员的admin角色
    private void assertNotRemoveLastAdminRole(Long userId, List<Long> newRoleIds) {
        SysRoleEntity adminRole = getAdminRole();
        if (adminRole == null) {
            return;
        }
        if (!hasRole(userId, adminRole.getRoleId())) {
            return;
        }
        boolean stillAdmin = newRoleIds != null && newRoleIds.contains(adminRole.getRoleId());
        if (!stillAdmin && countUsersWithRole(adminRole.getRoleId()) <= 1) {
            throw new BusinessException(Module.ModuleType.SYSTEM, "不能移除最后一个管理员的 admin 角色", null);
        }
    }

    // 发布用户状态变更事件
    private void publishUserStatusChanged(Long userId, UserStatusChangedEvent.ChangeType changeType) {
        eventPublisher.publishEvent(new UserStatusChangedEvent(userId, changeType));
    }

    // 获取admin角色实体
    private SysRoleEntity getAdminRole() {
        LambdaQueryWrapper<SysRoleEntity> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(SysRoleEntity::getSysRole, ADMIN_ROLE_NAME);
        return sysRoleService.getOne(wrapper);
    }

    // 判断用户是否拥有指定角色
    private boolean hasRole(Long userId, Long roleId) {
        LambdaQueryWrapper<SysUserRoleEntity> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(SysUserRoleEntity::getUserId, userId)
                .eq(SysUserRoleEntity::getRoleId, roleId);
        return sysUserRoleService.count(wrapper) > 0;
    }

    // 统计拥有指定角色的用户数
    private long countUsersWithRole(Long roleId) {
        LambdaQueryWrapper<SysUserRoleEntity> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(SysUserRoleEntity::getRoleId, roleId);
        return sysUserRoleService.list(wrapper).stream()
                .map(SysUserRoleEntity::getUserId)
                .distinct()
                .count();
    }
}

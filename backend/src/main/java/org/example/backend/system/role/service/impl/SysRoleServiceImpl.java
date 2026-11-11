package org.example.backend.system.role.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import org.apache.shiro.SecurityUtils;
import org.example.backend.common.exception.BusinessException;
import org.example.backend.common.exception.Module;
import lombok.extern.slf4j.Slf4j;
import org.example.backend.common.vo.OptionVO;
import org.example.backend.common.vo.PageResultVO;
import org.example.backend.system.role.dto.SysRoleCreateDTO;
import org.example.backend.system.role.dto.SysRolePermAssignDTO;
import org.example.backend.system.role.dto.SysRoleQueryDTO;
import org.example.backend.system.role.dto.SysRoleUpdateDTO;
import org.example.backend.system.role.entity.SysRoleEntity;
import org.example.backend.system.role.entity.SysRolePermissionEntity;
import org.example.backend.system.role.mapper.SysRoleMapper;
import org.example.backend.system.role.service.SysRolePermissionService;
import org.example.backend.system.role.service.SysRoleService;
import org.example.backend.system.role.vo.SysRoleVO;
import org.example.backend.system.permission.entity.SysPermissionEntity;
import org.example.backend.system.user.entity.SysUserRoleEntity;
import org.example.backend.system.user.service.SysUserRoleService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import javax.annotation.Resource;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

@Service
@Slf4j
public class SysRoleServiceImpl extends ServiceImpl<SysRoleMapper, SysRoleEntity> implements SysRoleService {

    private static final String LIST_SUFFIX = ":list";
    private static final String[] MUTATING_SUFFIXES = {":add", ":edit", ":delete"};

    @Resource
    private SysRoleMapper sysRoleMapper;

    @Autowired
    private SysRolePermissionService sysRolePermissionService;

    @Autowired
    private SysUserRoleService sysUserRoleService;

    @Autowired
    private org.example.backend.system.permission.service.SysPermissionService sysPermissionService;

    @Resource
    private org.example.backend.security.cache.AuthorizationCacheEvictor authorizationCacheEvictor;

    @Override
    // 按角色ID查询角色
    public SysRoleEntity getByRoleId(Long roleId) {
        LambdaQueryWrapper<SysRoleEntity> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(SysRoleEntity::getRoleId, roleId);
        return sysRoleMapper.selectOne(wrapper);
    }

    @Override
    // 查询用户拥有的角色标识列表
    public List<String> selectSysRoleByUserId(Long userId) {
        return sysRoleMapper.selectSysRoleByUserId(userId);
    }

    @Override
    // 查询用户的角色选项列表
    public List<OptionVO> selectRoleOptionsByUserId(Long userId) {
        return sysRoleMapper.selectRoleOptionsByUserId(userId);
    }

    @Override
    // 列出全部角色选项（管理员）
    public List<OptionVO> listAllRoleOptions() {
        assertAdmin();
        return sysRoleMapper.selectAllRoleOptions();
    }

    @Override
    // 分页查询角色及权限信息
    public PageResultVO<SysRoleVO> listRoleInfo(SysRoleQueryDTO dto) {
        assertAdmin();
        Map<Long, SysPermissionEntity> permIndex = loadPermissionIndex();
        if (dto.getRoleId() != null) {
            SysRoleEntity entity = getByRoleId(dto.getRoleId());
            if (entity == null) {
                throw roleNotFound();
            }
            return new PageResultVO<>(1, Collections.singletonList(toRoleVO(entity, permIndex)));
        }

        LambdaQueryWrapper<SysRoleEntity> wrapper = new LambdaQueryWrapper<>();
        wrapper.like(org.springframework.util.StringUtils.hasText(dto.getSysRole()),
                        SysRoleEntity::getSysRole, dto.getSysRole())
                .orderByAsc(SysRoleEntity::getRoleId);
        int pageNum = dto.getPageNum() == null ? 1 : dto.getPageNum();
        int pageSize = dto.getPageSize() == null ? 10 : dto.getPageSize();
        Page<SysRoleEntity> page = sysRoleMapper.selectPage(new Page<>(pageNum, pageSize), wrapper);
        List<SysRoleVO> rows = page.getRecords().stream()
                .map(entity -> toRoleVO(entity, permIndex))
                .collect(Collectors.toList());
        return new PageResultVO<>(page.getTotal(), rows);
    }

    @Transactional(rollbackFor = Exception.class)
    @Override
    // 创建角色并分配权限
    public void createRole(SysRoleCreateDTO dto) {
        assertAdmin();
        if (getByRoleName(dto.getSysRole()) != null) {
            throw new BusinessException(Module.ModuleType.SYSTEM, "角色标识已存在", null);
        }
        SysRoleEntity role = new SysRoleEntity();
        role.setSysRole(dto.getSysRole());
        save(role);
        assignPermissionsForRole(role, dto.getPermissionIds());
    }

    @Transactional(rollbackFor = Exception.class)
    @Override
    // 更新角色信息
    public void updateRole(SysRoleUpdateDTO dto) {
        assertAdmin();
        SysRoleEntity role = getByRoleId(dto.getRoleId());
        if (role == null) {
            throw roleNotFound();
        }
        if ("admin".equals(role.getSysRole()) && !"admin".equals(dto.getSysRole())) {
            throw new BusinessException(Module.ModuleType.SYSTEM, "不能修改管理员角色标识", null);
        }
        SysRoleEntity duplicate = getByRoleName(dto.getSysRole());
        if (duplicate != null && !duplicate.getRoleId().equals(dto.getRoleId())) {
            throw new BusinessException(Module.ModuleType.SYSTEM, "角色标识已存在", null);
        }
        role.setSysRole(dto.getSysRole());
        updateById(role);
    }

    @Override
    // 删除角色
    public void deleteRole(Long roleId) {
        assertAdmin();
        SysRoleEntity role = getByRoleId(roleId);
        if (role == null) {
            throw roleNotFound();
        }
        if ("admin".equals(role.getSysRole())) {
            throw new BusinessException(Module.ModuleType.SYSTEM, "不能删除管理员角色", null);
        }
        LambdaQueryWrapper<SysUserRoleEntity> userRoleWrapper = new LambdaQueryWrapper<>();
        userRoleWrapper.eq(SysUserRoleEntity::getRoleId, roleId);
        if (sysUserRoleService.count(userRoleWrapper) > 0) {
            throw new BusinessException(Module.ModuleType.SYSTEM, "角色已绑定用户，不能删除", null);
        }
        sysRolePermissionService.remove(
                new LambdaQueryWrapper<org.example.backend.system.role.entity.SysRolePermissionEntity>()
                        .eq(org.example.backend.system.role.entity.SysRolePermissionEntity::getRoleId, roleId));
        authorizationCacheEvictor.evictByRoleId(roleId);
        removeById(roleId);
    }

    @Override
    // 为角色分配权限
    public void assignRolePermissions(SysRolePermAssignDTO dto) {
        assertAdmin();
        SysRoleEntity role = getByRoleId(dto.getRoleId());
        if (role == null) {
            throw roleNotFound();
        }
        assignPermissionsForRole(role, dto.getPermissionIds());
    }

    // 为角色写入权限关联并刷新缓存
    private void assignPermissionsForRole(SysRoleEntity role, List<Long> permissionIds) {
        List<Long> ids;
        if ("admin".equals(role.getSysRole())) {
            ids = sysPermissionService.list().stream()
                    .map(SysPermissionEntity::getPermissionId)
                    .collect(Collectors.toList());
        } else {
            ids = expandWithRequiredListPermissions(permissionIds);
            long validCount = ids.stream().distinct()
                    .filter(id -> sysPermissionService.getByPermissionId(id) != null)
                    .count();
            if (validCount != ids.stream().distinct().count()) {
                throw new BusinessException(Module.ModuleType.SYSTEM, "存在不存在的权限 ID", null);
            }
        }
        sysRolePermissionService.assignPermissionsByRoleId(role.getRoleId(), ids);
        authorizationCacheEvictor.evictByRoleId(role.getRoleId());
    }

    /**
     * 勾选了 add/edit/delete 时自动补全同模块的 list 权限，保证能进入页面并加载列表。
     */
    // 自动补全同模块的list权限
    private List<Long> expandWithRequiredListPermissions(List<Long> permissionIds) {
        if (permissionIds == null || permissionIds.isEmpty()) {
            return Collections.emptyList();
        }
        Map<String, Long> permKeyToId = sysPermissionService.list().stream()
                .collect(Collectors.toMap(
                        SysPermissionEntity::getSysPermission,
                        SysPermissionEntity::getPermissionId,
                        (left, right) -> left,
                        LinkedHashMap::new));
        LinkedHashSet<Long> expanded = new LinkedHashSet<>(permissionIds);
        for (Long id : permissionIds) {
            SysPermissionEntity perm = sysPermissionService.getByPermissionId(id);
            if (perm == null || !org.springframework.util.StringUtils.hasText(perm.getSysPermission())) {
                continue;
            }
            String listKey = toListPermissionKey(perm.getSysPermission());
            if (listKey != null) {
                Long listId = permKeyToId.get(listKey);
                if (listId != null) {
                    expanded.add(listId);
                }
            }
        }
        return new ArrayList<>(expanded);
    }

    /** add/edit/delete 权限映射到同前缀的 list；其它操作不补全 */
    // 将变更类权限映射为对应的list权限键
    private String toListPermissionKey(String sysPermission) {
        for (String suffix : MUTATING_SUFFIXES) {
            if (sysPermission.endsWith(suffix)) {
                return sysPermission.substring(0, sysPermission.length() - suffix.length()) + LIST_SUFFIX;
            }
        }
        return null;
    }

    /** 按 permission_id 升序建索引，保证角色列表里权限展示顺序稳定 */
    // 加载权限ID索引
    private Map<Long, SysPermissionEntity> loadPermissionIndex() {
        return sysPermissionService.list(new LambdaQueryWrapper<SysPermissionEntity>()
                        .orderByAsc(SysPermissionEntity::getPermissionId)).stream()
                .collect(Collectors.toMap(
                        SysPermissionEntity::getPermissionId,
                        perm -> perm,
                        (left, right) -> left,
                        LinkedHashMap::new));
    }

    // 将角色实体转换为VO
    private SysRoleVO toRoleVO(SysRoleEntity entity, Map<Long, SysPermissionEntity> permIndex) {
        SysRoleVO vo = new SysRoleVO();
        vo.setRoleId(entity.getRoleId());
        vo.setSysRole(entity.getSysRole());
        Set<Long> boundIds = "admin".equals(entity.getSysRole())
                ? permIndex.keySet()
                : sysRolePermissionService.getByRoleId(entity.getRoleId()).stream()
                        .map(SysRolePermissionEntity::getPermissionId)
                        .collect(Collectors.toSet());
        vo.setPermissions(permIndex.values().stream()
                .filter(perm -> boundIds.contains(perm.getPermissionId()))
                .map(perm -> new OptionVO(perm.getPermissionId(), permDisplayName(perm)))
                .collect(Collectors.toList()));
        return vo;
    }

    /** 未维护中文名的权限回退展示权限标识，避免出现空白标签 */
    // 获取权限展示名称
    private String permDisplayName(SysPermissionEntity perm) {
        return org.springframework.util.StringUtils.hasText(perm.getPermName())
                ? perm.getPermName()
                : perm.getSysPermission();
    }

    // 按角色名查询角色
    private SysRoleEntity getByRoleName(String roleName) {
        return sysRoleMapper.selectOne(new LambdaQueryWrapper<SysRoleEntity>()
                .eq(SysRoleEntity::getSysRole, roleName));
    }

    // 校验当前用户为管理员
    private void assertAdmin() {
        if (!SecurityUtils.getSubject().hasRole("admin")) {
            throw new BusinessException(Module.ModuleType.SYSTEM, "仅管理员可以操作角色和权限", null);
        }
    }

    // 构建角色不存在异常
    private BusinessException roleNotFound() {
        return new BusinessException(Module.ModuleType.SYSTEM, "角色不存在", null);
    }
}

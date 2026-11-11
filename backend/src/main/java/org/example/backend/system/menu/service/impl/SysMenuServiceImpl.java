package org.example.backend.system.menu.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import lombok.extern.slf4j.Slf4j;
import org.apache.shiro.SecurityUtils;
import org.example.backend.common.exception.BusinessException;
import org.example.backend.common.exception.Module;
import org.example.backend.system.menu.entity.SysMenuEntity;
import org.example.backend.system.menu.mapper.SysMenuMapper;
import org.example.backend.system.menu.service.SysMenuService;
import org.example.backend.system.menu.vo.PermTreeNodeVO;
import org.example.backend.system.permission.entity.SysPermissionEntity;
import org.example.backend.system.permission.service.SysPermissionService;
import org.example.backend.system.role.entity.SysRoleEntity;
import org.example.backend.system.role.entity.SysRolePermissionEntity;
import org.example.backend.system.role.service.SysRolePermissionService;
import org.example.backend.system.role.service.SysRoleService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

@Service
@Slf4j
public class SysMenuServiceImpl extends ServiceImpl<SysMenuMapper, SysMenuEntity> implements SysMenuService {

    /** 未挂载菜单的权限归入该虚拟节点，menu_id 从 1 开始，0 不会与真实菜单冲突 */
    private static final long UNGROUPED_MENU_ID = 0L;

    private static final long ROOT_PARENT_ID = 0L;

    @Autowired
    private SysPermissionService sysPermissionService;

    @Autowired
    private SysRoleService sysRoleService;

    @Autowired
    private SysRolePermissionService sysRolePermissionService;

    @Override
    // 构建角色权限分配树
    public List<PermTreeNodeVO> buildPermTree(Long roleId) {
        assertAdmin();
        Set<Long> checkedIds = resolveCheckedPermissionIds(roleId);

        List<SysMenuEntity> menus = list(new LambdaQueryWrapper<SysMenuEntity>()
                .orderByAsc(SysMenuEntity::getParentId)
                .orderByAsc(SysMenuEntity::getOrderNum)
                .orderByAsc(SysMenuEntity::getMenuId));
        Set<Long> menuIds = menus.stream()
                .map(SysMenuEntity::getMenuId)
                .collect(Collectors.toSet());

        Map<Long, List<SysPermissionEntity>> permsByMenu = sysPermissionService.list().stream()
                .sorted(Comparator.comparing(SysPermissionEntity::getPermissionId))
                .collect(Collectors.groupingBy(
                        perm -> effectiveMenuId(perm, menuIds),
                        LinkedHashMap::new,
                        Collectors.toList()));

        Map<Long, List<SysMenuEntity>> menusByParent = menus.stream()
                .collect(Collectors.groupingBy(
                        menu -> parentIdOf(menu, menuIds),
                        LinkedHashMap::new,
                        Collectors.toList()));

        List<PermTreeNodeVO> tree = buildMenuNodes(ROOT_PARENT_ID, menusByParent, permsByMenu, checkedIds);

        List<SysPermissionEntity> ungrouped = permsByMenu.get(UNGROUPED_MENU_ID);
        if (ungrouped != null && !ungrouped.isEmpty()) {
            PermTreeNodeVO node = PermTreeNodeVO.menu(UNGROUPED_MENU_ID, "未分类");
            node.getChildren().addAll(toPermissionNodes(ungrouped, checkedIds));
            tree.add(node);
        }
        return tree;
    }

    // 递归构建菜单节点树
    private List<PermTreeNodeVO> buildMenuNodes(Long parentId,
                                                Map<Long, List<SysMenuEntity>> menusByParent,
                                                Map<Long, List<SysPermissionEntity>> permsByMenu,
                                                Set<Long> checkedIds) {
        List<PermTreeNodeVO> nodes = new ArrayList<>();
        for (SysMenuEntity menu : menusByParent.getOrDefault(parentId, Collections.emptyList())) {
            PermTreeNodeVO node = PermTreeNodeVO.menu(menu.getMenuId(), menu.getMenuName());
            node.getChildren().addAll(
                    buildMenuNodes(menu.getMenuId(), menusByParent, permsByMenu, checkedIds));
            node.getChildren().addAll(toPermissionNodes(
                    permsByMenu.getOrDefault(menu.getMenuId(), Collections.emptyList()), checkedIds));
            nodes.add(node);
        }
        return nodes;
    }

    // 将权限列表转换为树节点
    private List<PermTreeNodeVO> toPermissionNodes(List<SysPermissionEntity> perms, Set<Long> checkedIds) {
        return perms.stream()
                .map(perm -> PermTreeNodeVO.permission(
                        perm.getPermissionId(),
                        displayName(perm),
                        perm.getSysPermission(),
                        checkedIds.contains(perm.getPermissionId())))
                .collect(Collectors.toList());
    }

    // 解析角色已勾选的权限ID集合
    private Set<Long> resolveCheckedPermissionIds(Long roleId) {
        if (roleId == null) {
            return Collections.emptySet();
        }
        SysRoleEntity role = sysRoleService.getByRoleId(roleId);
        if (role == null) {
            throw new BusinessException(Module.ModuleType.SYSTEM, "角色不存在", null);
        }
        // 与 SysRoleServiceImpl.assignPermissionsForRole 一致：admin 恒为全量授权
        if ("admin".equals(role.getSysRole())) {
            return sysPermissionService.list().stream()
                    .map(SysPermissionEntity::getPermissionId)
                    .collect(Collectors.toSet());
        }
        return sysRolePermissionService.getByRoleId(roleId).stream()
                .map(SysRolePermissionEntity::getPermissionId)
                .collect(Collectors.toSet());
    }

    // 获取权限展示名称
    private String displayName(SysPermissionEntity perm) {
        return StringUtils.hasText(perm.getPermName()) ? perm.getPermName() : perm.getSysPermission();
    }

    // 计算权限所属的有效菜单ID
    private Long effectiveMenuId(SysPermissionEntity perm, Set<Long> menuIds) {
        Long menuId = perm.getMenuId();
        return menuId != null && menuIds.contains(menuId) ? menuId : UNGROUPED_MENU_ID;
    }

    /** 父菜单不存在时按顶级处理，避免整棵子树因脏数据不可见 */
    // 解析菜单的有效父ID
    private Long parentIdOf(SysMenuEntity menu, Set<Long> menuIds) {
        Long parentId = menu.getParentId();
        return parentId != null && menuIds.contains(parentId) ? parentId : ROOT_PARENT_ID;
    }

    // 校验当前用户为管理员
    private void assertAdmin() {
        if (!SecurityUtils.getSubject().hasRole("admin")) {
            throw new BusinessException(Module.ModuleType.SYSTEM, "仅管理员可以操作角色和权限", null);
        }
    }
}

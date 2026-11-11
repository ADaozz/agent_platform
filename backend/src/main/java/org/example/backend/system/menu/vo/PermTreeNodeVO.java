package org.example.backend.system.menu.vo;

import com.fasterxml.jackson.annotation.JsonInclude;
import lombok.Data;

import java.util.List;

/**
 * 角色授权树节点：菜单节点承载分组，权限节点承载勾选项。
 * 菜单节点不输出 permission/checked，权限节点不输出 children。
 */
@Data
@JsonInclude(JsonInclude.Include.NON_NULL)
public class PermTreeNodeVO {

    public static final String TYPE_MENU = "MENU";
    public static final String TYPE_PERMISSION = "PERMISSION";

    // 菜单节点为 menuId，权限节点为 permissionId（授权提交用的就是它）
    private Long id;

    // 全局唯一键，menuId 与 permissionId 会撞号，树组件用它作 node-key
    private String nodeKey;

    private String name;

    // MENU 或 PERMISSION
    private String type;

    // 仅权限节点：权限标识，例如 system:user:list
    private String permission;

    // 仅权限节点：当前角色是否已勾选
    private Boolean checked;

    // 仅菜单节点：子节点，无内容时为空数组
    private List<PermTreeNodeVO> children;

    public static PermTreeNodeVO menu(Long menuId, String name) {
        PermTreeNodeVO node = new PermTreeNodeVO();
        node.setId(menuId);
        node.setNodeKey("M-" + menuId);
        node.setName(name);
        node.setType(TYPE_MENU);
        node.setChildren(new java.util.ArrayList<>());
        return node;
    }

    public static PermTreeNodeVO permission(Long permissionId, String name, String permission, boolean checked) {
        PermTreeNodeVO node = new PermTreeNodeVO();
        node.setId(permissionId);
        node.setNodeKey("P-" + permissionId);
        node.setName(name);
        node.setType(TYPE_PERMISSION);
        node.setPermission(permission);
        node.setChecked(checked);
        return node;
    }
}

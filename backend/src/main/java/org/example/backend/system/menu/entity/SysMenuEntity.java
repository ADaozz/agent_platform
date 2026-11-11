package org.example.backend.system.menu.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import lombok.EqualsAndHashCode;
import lombok.experimental.Accessors;

@Data
@TableName("sys_menu")
@Accessors(chain = true)
@EqualsAndHashCode(callSuper = false)
public class SysMenuEntity {

    @TableId(type = IdType.AUTO)
    // 菜单 ID
    private Long menuId;

    // 菜单名称，例如：用户管理
    private String menuName;

    // 父菜单 ID，顶级为 0
    private Long parentId;

    // 前端路由路径，例如：/system/user
    private String path;

    // 图标名，对应前端 AppIcon
    private String icon;

    // 同级排序号，升序
    private Integer orderNum;

    // 是否显示：0-显示，1-隐藏
    private String visible;

}

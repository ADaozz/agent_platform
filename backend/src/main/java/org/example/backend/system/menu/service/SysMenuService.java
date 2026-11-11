package org.example.backend.system.menu.service;

import com.baomidou.mybatisplus.extension.service.IService;
import org.example.backend.system.menu.entity.SysMenuEntity;
import org.example.backend.system.menu.vo.PermTreeNodeVO;

import java.util.List;

public interface SysMenuService extends IService<SysMenuEntity> {

    /**
     * 组装菜单 + 权限的授权树。
     *
     * @param roleId 角色 ID，为 null 时所有权限节点 checked 均为 false
     */
    List<PermTreeNodeVO> buildPermTree(Long roleId);
}

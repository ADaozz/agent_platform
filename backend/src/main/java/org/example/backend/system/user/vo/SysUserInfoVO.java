package org.example.backend.system.user.vo;

import lombok.Data;
import org.example.backend.common.vo.OptionVO;

import java.util.List;

@Data
public class SysUserInfoVO {

    private Long userId;

    private String username;

    /** 角色：id=roleId，label=sysRole（Shiro 仍用 label 作为角色标识） */
    private List<OptionVO> roles;

    /** 权限：id=permissionId，label=sysPermission */
    private List<OptionVO> permissions;
}

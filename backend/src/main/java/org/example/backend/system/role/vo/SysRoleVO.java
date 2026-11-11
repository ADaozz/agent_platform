package org.example.backend.system.role.vo;

import lombok.Data;
import org.example.backend.common.vo.OptionVO;

import java.util.List;

@Data
public class SysRoleVO {

    private Long roleId;

    private String sysRole;

    /** 已绑定的权限：id=permissionId，label=权限中文名（perm_name，未维护时回退为权限标识） */
    private List<OptionVO> permissions;
}

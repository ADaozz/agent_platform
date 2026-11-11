package org.example.backend.system.user.vo;

import lombok.Data;
import org.example.backend.common.vo.OptionVO;

import java.util.Date;
import java.util.List;

@Data
public class SysUserVO {

    /** 业务主键，可作为列表展示项 */
    private Long userId;

    private String userName;

    private String status;

    private Date createTime;

    private Date updateTime;

    private Date lastLoginTime;

    /** 角色：id=roleId，label=sysRole */
    private List<OptionVO> roles;
}

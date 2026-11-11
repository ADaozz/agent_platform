package org.example.backend.system.role.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import lombok.EqualsAndHashCode;
import lombok.experimental.Accessors;

import java.util.List;

@Data
@TableName("sys_role")
@Accessors(chain = true)
@EqualsAndHashCode(callSuper = false)
public class SysRoleEntity {

    @TableId(type = IdType.AUTO)
    // 角色 ID
    private Long roleId;

    // 角色标识，例如：admin、user
    private String sysRole;

}

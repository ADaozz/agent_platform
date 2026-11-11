package org.example.backend.system.user.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import lombok.EqualsAndHashCode;
import lombok.experimental.Accessors;

@Data
@TableName("sys_user_role")
@Accessors(chain = true)
@EqualsAndHashCode(callSuper = false)
public class SysUserRoleEntity {

    // 用户 ID
    private Long userId;

    // 角色 ID
    private Long roleId;
}

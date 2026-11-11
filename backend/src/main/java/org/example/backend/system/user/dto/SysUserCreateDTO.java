package org.example.backend.system.user.dto;

import lombok.Data;
import org.example.backend.system.user.constant.UserConstants;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.Pattern;
import javax.validation.constraints.Size;
import java.util.List;

@Data
public class SysUserCreateDTO {

    @NotBlank(message = "用户名不能为空")
    @Size(max = 64, message = "用户名最长64字符")
    private String userName;

    @NotBlank(message = "密码不能为空")
    @Size(min = 6, max = 32, message = "密码长度6-32位")
    private String passWord;

    @Pattern(regexp = "[01]", message = "状态只能是0或1")
    private String status = UserConstants.STATUS_NORMAL;

    /** 分配角色时传 roleId 列表即可 */
    private List<Long> roleIds;
}

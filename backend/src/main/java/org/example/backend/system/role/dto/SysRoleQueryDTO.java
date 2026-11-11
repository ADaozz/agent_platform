package org.example.backend.system.role.dto;

import lombok.Data;

import javax.validation.constraints.Max;
import javax.validation.constraints.Min;

@Data
public class SysRoleQueryDTO {

    /** 传 roleId 时查单条详情 */
    private Long roleId;

    private String sysRole;

    @Min(1)
    private Integer pageNum = 1;

    @Max(50)
    private Integer pageSize = 10;
}

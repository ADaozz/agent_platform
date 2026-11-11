package org.example.backend.system.permission.dto;

import lombok.Data;

import javax.validation.constraints.Max;
import javax.validation.constraints.Min;

@Data
public class SysPermissionQueryDTO {

    private Long permissionId;

    private String sysPermission;

    @Min(1)
    private Integer pageNum = 1;

    @Max(50)
    private Integer pageSize = 10;
}

package org.example.backend.system.user.dto;

import lombok.Data;

import javax.validation.constraints.Max;
import javax.validation.constraints.Min;

@Data
public class SysUserQueryDTO {

    /** 传 userId 时查单条详情，不传则查列表 */
    private Long userId;

    private String userName;
    private String status;
    private Long roleId;
    @Min(1)
    private Integer pageNum = 1;
    @Max(50)
    private Integer pageSize = 10;
}

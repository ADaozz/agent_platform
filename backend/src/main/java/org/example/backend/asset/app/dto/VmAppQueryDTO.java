package org.example.backend.asset.app.dto;

import lombok.Data;

import javax.validation.constraints.Max;
import javax.validation.constraints.Min;

@Data
public class VmAppQueryDTO {

    private String appId;

    private String appName;

    private String hostId;

    private String vmIp;

    private String appStatus;

    @Min(1)
    private Integer pageNum = 1;

    @Max(50)
    private Integer pageSize = 10;
}

package org.example.backend.asset.host.dto;

import lombok.Data;

import javax.validation.constraints.Max;
import javax.validation.constraints.Min;

@Data
public class VmHostQueryDTO {

    /** 传 hostId 时查单条详情 */
    private String hostId;

    private String hostName;

    private String vmIp;

    private String lifecycleStatus;

    private Long ownerUserId;

    private String networkZone;

    private String env;

    @Min(1)
    private Integer pageNum = 1;

    @Max(50)
    private Integer pageSize = 10;
}

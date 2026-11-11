package org.example.backend.asset.host.domain.model;

import lombok.Builder;
import lombok.Getter;

@Getter
@Builder
public class VmHostUpdateCommand {

    private final String hostName;
    private final String osType;
    private final String osVersion;
    private final String vmIp;
    private final Integer cpuCores;
    private final Integer memoryGb;
    private final Integer diskGb;
    private final String physicalHostIp;
    private final String lifecycleStatus;
    private final String networkZone;
    private final String env;
    private final String remark;
}

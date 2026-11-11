package org.example.backend.asset.host.vo;

import com.fasterxml.jackson.annotation.JsonFormat;
import lombok.Data;
import org.example.backend.common.vo.OptionVO;
import org.springframework.format.annotation.DateTimeFormat;

import java.util.Date;

@Data
public class VmHostVO {

    private String hostId;

    private String hostName;

    private String osType;

    private String osVersion;

    private String vmIp;

    private Integer cpuCores;

    private Integer memoryGb;

    private Integer diskGb;

    private String physicalHostIp;

    private String lifecycleStatus;

    /** owner：id=userId，label=userName */
    private OptionVO owner;

    private String networkZone;

    private String env;

    private String remark;

    @JsonFormat(timezone = "GMT+8", pattern = "yyyy-MM-dd HH:mm:ss")
    @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private Date createTime;

    @JsonFormat(timezone = "GMT+8", pattern = "yyyy-MM-dd HH:mm:ss")
    @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private Date updateTime;
}

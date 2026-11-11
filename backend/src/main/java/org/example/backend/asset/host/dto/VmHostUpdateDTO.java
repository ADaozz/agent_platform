package org.example.backend.asset.host.dto;

import lombok.Data;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;
import javax.validation.constraints.Pattern;
import javax.validation.constraints.Size;

@Data
public class VmHostUpdateDTO {

    @NotBlank(message = "虚机ID不能为空")
    private String hostId;

    @NotBlank(message = "虚机名称不能为空")
    @Size(max = 128)
    private String hostName;

    @NotBlank(message = "操作系统不能为空")
    @Size(max = 64)
    private String osType;

    @Size(max = 64)
    private String osVersion;

    @Size(max = 64)
    private String vmIp;

    private Integer cpuCores;

    private Integer memoryGb;

    private Integer diskGb;

    @Size(max = 64)
    private String physicalHostIp;

    /** 仅允许按生命周期顺序推进到下一状态；不传则保持当前状态 */
    @Pattern(regexp = "creating|running|stopped|pending_delete|destroyed", message = "生命周期状态不合法")
    private String lifecycleStatus;

    @NotBlank(message = "网段不能为空")
    @Pattern(regexp = "idc|cfdc", message = "网段只能是 idc 或 cfdc")
    private String networkZone;

    @NotBlank(message = "环境不能为空")
    @Pattern(regexp = "prod|dev|test", message = "环境只能是 prod、dev 或 test")
    private String env;

    @Size(max = 512)
    private String remark;
}
